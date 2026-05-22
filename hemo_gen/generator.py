from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field
from pathlib import Path

from hemo_gen.assessment import (
    ASSESSMENT_ITEM_COLUMNS,
    PRE_VITAL_COLUMNS,
    build_assessment_items,
    build_post_vital,
    build_pre_vital,
    load_assessment_map,
)
from hemo_gen.config import (
    B01_FILE,
    B02_FILE,
    B03_FILE,
    B04_FILE,
    B05_FILE,
    B06_FILE,
    B07_FILE,
    CREATED_BY,
    GenConfig,
    START_DATE,
    first_business_on_or_after,
)
from hemo_gen.dialysis_records import B04_COLUMNS, build_dialysis_records
from hemo_gen.execution import B06_COLUMNS, build_medicine_execution
from hemo_gen.medicine_prescription import B07_COLUMNS, build_espogen_prescription, load_medicine_catalog
from hemo_gen.patient_loader import load_patients, load_slot_assignments
from hemo_gen.prescription import B02_COLUMNS, DialysisPrescriptionManager
from hemo_gen.profiles import build_profile
from hemo_gen.schedule import build_session_slots
from hemo_gen.session_builder import B01_COLUMNS, B03_COLUMNS, build_b01_row, build_session
from hemo_gen.sql_io import (
    append_b05_bundle,
    append_rows,
    find_patient_uuid_in_file,
    max_treatment_no_for_patient,
    patient_exists_in_file,
)
from hemo_gen.state import GenState


@dataclass
class GenResult:
    patient_id: str
    sessions: int = 0
    b02_rows: int = 0
    b03_rows: int = 0
    b04_rows: int = 0
    b05_pre: int = 0
    b05_post: int = 0
    b05_items: int = 0
    b06_rows: int = 0
    b07_rows: int = 0
    b01_written: bool = False


def run_generator(cfg: GenConfig) -> GenResult:
    rng = random.Random(cfg.seed)
    base = cfg.base_dir
    state = GenState.load(base / ".hemo_gen_state.json")
    ps = state.for_patient(cfg.patient_id)

    patients = {p.patient_id: p for p in load_patients(base / "05-Patients.sql")}
    if cfg.patient_id not in patients:
        raise SystemExit(f"ไม่พบ PatientId {cfg.patient_id} ใน 05-Patients.sql")
    patient = patients[cfg.patient_id]
    slots = load_slot_assignments(base / "11-SectionSlotPatient.sql", cfg.patient_id)
    profile = build_profile(patient, slots, rng)

    result = GenResult(patient_id=cfg.patient_id)
    b01_path = base / B01_FILE
    b02_path = base / B02_FILE
    b03_path = base / B03_FILE
    b04_path = base / B04_FILE
    b05_path = base / B05_FILE
    b06_path = base / B06_FILE
    b07_path = base / B07_FILE

    treatment_no = max(
        ps.last_treatment_no,
        max_treatment_no_for_patient(b03_path, cfg.patient_id),
    )
    last_post: float | None = None

    rx_mgr = DialysisPrescriptionManager(profile, rng)
    if ps.sessions_on_current_rx > 0:
        rx_mgr.sessions_on_rx = ps.sessions_on_current_rx
        rx_mgr.max_sessions = ps.max_sessions_on_rx

    session_slots = build_session_slots(profile, cfg.start_date, cfg.end_date, rng)
    catalog = load_medicine_catalog()
    amap = load_assessment_map()
    b01_rows: list[list[str]] = []
    b02_rows: list[list[str]] = []
    b03_rows: list[list[str]] = []
    b04_rows: list[list[str]] = []
    b05_pre_rows: list[list[str]] = []
    b05_post_rows: list[list[str]] = []
    b05_item_rows: list[list[str]] = []
    b06_rows: list[list[str]] = []
    b07_rows: list[list[str]] = []

    first_session_date = session_slots[0].session_date if session_slots else cfg.start_date

    if not patient_exists_in_file(b01_path, "AvShunts", "PatientId", cfg.patient_id) or cfg.force_b01:
        established = dt.datetime.combine(
            first_business_on_or_after(START_DATE),
            dt.time(2, 0),
            tzinfo=dt.timezone.utc,
        )
        b01_rows.append(build_b01_row(profile, established))
        result.b01_written = True

    med_rx_id = find_patient_uuid_in_file(b07_path, "MedicinePrescriptions", "PatientId", cfg.patient_id)
    if not med_rx_id:
        stale_rx_id = ps.medicine_prescription_ids.get("espogen")
        med_row = build_espogen_prescription(
            cfg.patient_id,
            dt.datetime.combine(first_session_date, dt.time(5, 0), tzinfo=dt.timezone.utc),
            cfg.end_date,
            catalog,
            prescription_id=stale_rx_id,
        )
        med_rx_id = med_row.id
        b07_rows.append(med_row.fields)
    ps.medicine_prescription_ids["espogen"] = med_rx_id

    is_first_rx = True
    for slot in session_slots:
        new_rx = rx_mgr.new_prescription_rows_for_session(slot.cycle_start, is_first_rx)
        if new_rx:
            b02_rows.extend(new_rx)
            result.b02_rows += len(new_rx)
            is_first_rx = False
        elif is_first_rx:
            b02_rows.append(rx_mgr.active().fields)
            result.b02_rows += 1
            is_first_rx = False

        treatment_no += 1
        built = build_session(slot, profile, rx_mgr.active(), treatment_no, last_post, rng)
        last_post = built.post_weight
        b03_rows.append(built.b03_fields)
        b04_rows.extend(build_dialysis_records(built, profile.bed_number, rng))
        pre = build_pre_vital(built, rng)
        pre_bps = int(pre[3])
        b05_pre_rows.append(pre)
        b05_post_rows.append(build_post_vital(built, pre_bps, rng))
        b05_item_rows.extend(build_assessment_items(built.hemo_id, amap))

        exec_row = build_medicine_execution(
            built,
            med_rx_id,
            catalog["espogen"]["override_route"],
            rng,
        )
        if exec_row:
            b06_rows.append(exec_row)

        rx_mgr.on_session_completed()
        result.sessions += 1

    result.b03_rows = len(b03_rows)
    result.b04_rows = len(b04_rows)
    result.b05_pre = len(b05_pre_rows)
    result.b05_post = len(b05_post_rows)
    result.b05_items = len(b05_item_rows)
    result.b06_rows = len(b06_rows)
    result.b07_rows = len(b07_rows)

    if cfg.dry_run:
        print(f"[dry-run] patient={cfg.patient_id} sessions={result.sessions}")
        print(f"  B01={len(b01_rows)} B02={result.b02_rows} B07={result.b07_rows} B03={result.b03_rows}")
        print(f"  B04={result.b04_rows} B05 pre/post/items={result.b05_pre}/{result.b05_post}/{result.b05_items} B06={result.b06_rows}")
        return result

    if b01_rows:
        append_rows(b01_path, "AvShunts", B01_COLUMNS, b01_rows, "hemo_gen AvShunts")
    if b02_rows:
        append_rows(b02_path, "DialysisPrescriptions", B02_COLUMNS, b02_rows, "hemo_gen DialysisPrescriptions")
    if b07_rows:
        append_rows(b07_path, "MedicinePrescriptions", B07_COLUMNS, b07_rows, "hemo_gen MedicinePrescriptions")
    if b03_rows:
        append_rows(b03_path, "HemodialysisRecords", B03_COLUMNS, b03_rows, "hemo_gen HemodialysisRecords")
    if b04_rows:
        append_rows(b04_path, "DialysisRecords", B04_COLUMNS, b04_rows, "hemo_gen DialysisRecords")
    if b05_pre_rows or b05_post_rows or b05_item_rows:
        append_b05_bundle(
            b05_path,
            b05_pre_rows,
            b05_post_rows,
            b05_item_rows,
            PRE_VITAL_COLUMNS,
            PRE_VITAL_COLUMNS,
            ASSESSMENT_ITEM_COLUMNS,
        )
    if b06_rows:
        append_rows(b06_path, "ExecutionRecords", B06_COLUMNS, b06_rows, "hemo_gen ExecutionRecords")

    ps.last_treatment_no = treatment_no
    ps.last_session_date = session_slots[-1].session_date.isoformat() if session_slots else None
    ps.sessions_on_current_rx = rx_mgr.sessions_on_rx
    ps.max_sessions_on_rx = rx_mgr.max_sessions
    ps.dialysis_prescription_count += result.b02_rows
    state.save(base / ".hemo_gen_state.json")

    return result

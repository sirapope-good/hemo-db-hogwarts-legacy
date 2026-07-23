from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass

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
    GenConfig,
    PATIENTS_FILE,
    SLOT_FILE,
    START_DATE,
    a_file,
    b_file,
    first_business_on_or_after,
    state_path,
)
from hemo_gen.dialysis_records import B04_COLUMNS, build_dialysis_records
from hemo_gen.execution import B06_COLUMNS, build_session_executions
from hemo_gen.medicine_prescription import (
    B07_COLUMNS,
    MedicinePrescriptionRow,
    build_medicine_prescription,
    load_medicine_catalog,
    load_templates,
    plan_patient_medication_keys,
)
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


def _resolve_session_window(cfg: GenConfig, last_session_date: str | None) -> tuple[dt.date, dt.date]:
    """Continue from day after last generated session when state has progress."""
    end = cfg.end_date
    start = cfg.start_date
    if last_session_date:
        after = dt.date.fromisoformat(last_session_date) + dt.timedelta(days=1)
        if after > start:
            start = after
    return first_business_on_or_after(start), end


def _ensure_medicine_prescriptions(
    *,
    profile,
    patient_id: str,
    administer_at: dt.datetime,
    b07_path,
    ps,
    rng: random.Random,
    catalog: dict,
    force_meds: bool = False,
) -> tuple[list[MedicinePrescriptionRow], list[list[str]]]:
    """
    Ensure patient has a natural multi-med B07 set.
    Returns (active prescription objects for B06, new SQL rows to append).
    """
    templates = load_templates(catalog)
    existing_in_file = find_patient_uuid_in_file(b07_path, "MedicinePrescriptions", "PatientId", patient_id)
    active: list[MedicinePrescriptionRow] = []
    new_rows: list[list[str]] = []

    if force_meds:
        ps.medicine_prescription_ids = {}

    planned_keys = [k for k in ps.medicine_prescription_ids.keys() if k in templates]
    if not planned_keys:
        planned_keys = plan_patient_medication_keys(profile, rng, catalog)

    # Legacy single-row seed without state keys: keep Espogen id for B06 unless force_meds.
    if existing_in_file and not ps.medicine_prescription_ids and not force_meds:
        tmpl = templates["espogen"]
        legacy = MedicinePrescriptionRow(
            id=existing_in_file,
            key="espogen",
            role="esa",
            medicine_id=tmpl.medicine_id,
            non_dialysis=False,
            execute_chance=tmpl.execute_chance,
            route=tmpl.route,
            fields=[],
        )
        ps.medicine_prescription_ids["espogen"] = existing_in_file
        return [legacy], []

    for key in planned_keys:
        tmpl = templates[key]
        existing_id = None if force_meds else ps.medicine_prescription_ids.get(key)
        if existing_id:
            active.append(
                MedicinePrescriptionRow(
                    id=existing_id,
                    key=key,
                    role=tmpl.role,
                    medicine_id=tmpl.medicine_id,
                    non_dialysis=tmpl.non_dialysis,
                    execute_chance=tmpl.execute_chance,
                    route=tmpl.route,
                    fields=[],
                )
            )
            continue

        note = f"Hogwarts gen {tmpl.name} (with dialysis start {administer_at.date().isoformat()})"
        row = build_medicine_prescription(
            tmpl,
            patient_id,
            administer_at,
            note=note,
        )
        active.append(row)
        new_rows.append(row.fields)
        ps.medicine_prescription_ids[key] = row.id

    return active, new_rows


def run_generator(cfg: GenConfig) -> GenResult:
    rng = random.Random(cfg.seed)
    root = cfg.base_dir
    state = GenState.load(state_path(root))
    ps = state.for_patient(cfg.patient_id)

    patients = {p.patient_id: p for p in load_patients(a_file(PATIENTS_FILE, root))}
    if cfg.patient_id not in patients:
        raise SystemExit(f"ไม่พบ PatientId {cfg.patient_id} ใน {PATIENTS_FILE}")
    patient = patients[cfg.patient_id]
    slots = load_slot_assignments(a_file(SLOT_FILE, root), cfg.patient_id)
    profile = build_profile(patient, slots, rng)

    result = GenResult(patient_id=cfg.patient_id)
    b01_path = b_file(B01_FILE, root)
    b02_path = b_file(B02_FILE, root)
    b03_path = b_file(B03_FILE, root)
    b04_path = b_file(B04_FILE, root)
    b05_path = b_file(B05_FILE, root)
    b06_path = b_file(B06_FILE, root)
    b07_path = b_file(B07_FILE, root)

    treatment_no = max(
        ps.last_treatment_no,
        max_treatment_no_for_patient(b03_path, cfg.patient_id),
    )
    last_post: float | None = None

    rx_mgr = DialysisPrescriptionManager(profile, rng)
    if ps.sessions_on_current_rx > 0:
        rx_mgr.sessions_on_rx = ps.sessions_on_current_rx
        rx_mgr.max_sessions = ps.max_sessions_on_rx

    window_start, window_end = _resolve_session_window(cfg, ps.last_session_date)
    if window_start > window_end:
        print(
            f"[skip] patient={cfg.patient_id} already through {ps.last_session_date} "
            f"(target end={window_end})"
        )
        return result

    session_slots = build_session_slots(profile, window_start, window_end, rng)
    if not session_slots:
        print(f"[skip] patient={cfg.patient_id} no session days in {window_start}..{window_end}")
        return result

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

    first_slot = session_slots[0]
    # Medicine AdministerDate aligns with first dialysis prescription / session of this generation window.
    med_admin = first_slot.cycle_start

    if not patient_exists_in_file(b01_path, "AvShunts", "PatientId", cfg.patient_id) or cfg.force_b01:
        established = dt.datetime.combine(
            first_business_on_or_after(START_DATE),
            dt.time(2, 0),
            tzinfo=dt.timezone.utc,
        )
        b01_rows.append(build_b01_row(profile, established))
        result.b01_written = True

    active_meds, new_med_rows = _ensure_medicine_prescriptions(
        profile=profile,
        patient_id=cfg.patient_id,
        administer_at=med_admin,
        b07_path=b07_path,
        ps=ps,
        rng=rng,
        catalog=catalog,
        force_meds=cfg.force_meds,
    )
    b07_rows.extend(new_med_rows)

    is_first_rx = True
    for slot in session_slots:
        new_rx = rx_mgr.new_prescription_rows_for_session(slot.cycle_start, is_first_rx)
        if new_rx:
            b02_rows.extend(new_rx)
            result.b02_rows += len(new_rx)
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

        b06_rows.extend(build_session_executions(built, active_meds, rng))

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
        med_keys = list(ps.medicine_prescription_ids.keys())
        print(f"[dry-run] patient={cfg.patient_id} sessions={result.sessions} window={window_start}..{window_end}")
        print(f"  meds={med_keys}")
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
    state.save(state_path(root))

    return result

"""เขียน B07 จาก state / B06 เมื่อไฟล์ B07 หายแต่ยังมี PrescriptionId ใน state หรือ B06."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from hemo_gen.config import B03_FILE, B06_FILE, B07_FILE, START_DATE, first_business_on_or_after
from hemo_gen.medicine_prescription import B07_COLUMNS, build_espogen_prescription, load_medicine_catalog
from hemo_gen.sql_io import append_rows, find_patient_uuid_in_file, iter_insert_blocks, split_fields, split_tuples
from hemo_gen.state import GenState


def _prescription_id_from_b06(b06_path: Path, patient_id: str) -> str | None:
    if not b06_path.exists():
        return None
    b03_path = b06_path.parent / B03_FILE
    if not b03_path.exists():
        return None
    hemo_to_patient: dict[str, str] = {}
    text_b03 = b03_path.read_text(encoding="utf-8")
    for columns, values in iter_insert_blocks(text_b03, "HemodialysisRecords"):
        if "Id" not in columns or "PatientId" not in columns:
            continue
        id_idx = columns.index("Id")
        p_idx = columns.index("PatientId")
        for body in split_tuples(values):
            fields = split_fields(body)
            if len(fields) > max(id_idx, p_idx):
                hemo_to_patient[fields[id_idx].strip("'")] = fields[p_idx].strip("'")

    text_b06 = b06_path.read_text(encoding="utf-8")
    for columns, values in iter_insert_blocks(text_b06, "ExecutionRecords"):
        if "HemodialysisId" not in columns or "PrescriptionId" not in columns:
            continue
        h_idx = columns.index("HemodialysisId")
        rx_idx = columns.index("PrescriptionId")
        for body in split_tuples(values):
            fields = split_fields(body)
            if len(fields) <= max(h_idx, rx_idx):
                continue
            hemo_id = fields[h_idx].strip("'")
            if hemo_to_patient.get(hemo_id) == patient_id:
                return fields[rx_idx].strip("'")
    return None


def _last_cycle_end_date(b03_path: Path, patient_id: str) -> dt.date | None:
    if not b03_path.exists():
        return None
    best: dt.date | None = None
    text = b03_path.read_text(encoding="utf-8")
    for columns, values in iter_insert_blocks(text, "HemodialysisRecords"):
        if "PatientId" not in columns or "CycleEndTime" not in columns:
            continue
        p_idx = columns.index("PatientId")
        c_idx = columns.index("CycleEndTime")
        for body in split_tuples(values):
            fields = split_fields(body)
            if fields[p_idx].strip("'") != patient_id:
                continue
            raw = fields[c_idx].strip("'")
            m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
            if m:
                d = dt.date.fromisoformat(m.group(1))
                if best is None or d > best:
                    best = d
    return best


def restore_b07(base: Path, patient_id: str | None = None) -> list[tuple[str, str, bool]]:
    """คืน [(patient_id, prescription_id, written)]"""
    state = GenState.load(base / ".hemo_gen_state.json")
    b07_path = base / B07_FILE
    b03_path = base / B03_FILE
    b06_path = base / B06_FILE
    catalog = load_medicine_catalog()
    results: list[tuple[str, str, bool]] = []

    patient_ids = [patient_id] if patient_id else list(state.patients.keys())
    for pid in patient_ids:
        existing = find_patient_uuid_in_file(b07_path, "MedicinePrescriptions", "PatientId", pid)
        if existing:
            ps = state.for_patient(pid)
            ps.medicine_prescription_ids["espogen"] = existing
            results.append((pid, existing, False))
            continue

        ps = state.for_patient(pid)
        rx_id = ps.medicine_prescription_ids.get("espogen") or _prescription_id_from_b06(b06_path, pid)
        administer = dt.datetime.combine(
            first_business_on_or_after(START_DATE),
            dt.time(5, 0),
            tzinfo=dt.timezone.utc,
        )
        expire = _last_cycle_end_date(b03_path, pid) or dt.date.today()
        med_row = build_espogen_prescription(
            pid,
            administer,
            expire,
            catalog,
            prescription_id=rx_id,
        )
        append_rows(b07_path, "MedicinePrescriptions", B07_COLUMNS, [med_row.fields], "hemo_gen restore B07")
        ps.medicine_prescription_ids["espogen"] = med_row.id
        results.append((pid, med_row.id, True))

    state.save(base / ".hemo_gen_state.json")
    return results

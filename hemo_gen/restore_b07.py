"""เขียน B07 จาก state เมื่อไฟล์หาย — ใช้ multi-med templates (ExpireDate NULL)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from hemo_gen.config import B03_FILE, B06_FILE, B07_FILE, START_DATE, b_file, first_business_on_or_after, state_path
from hemo_gen.medicine_prescription import (
    B07_COLUMNS,
    build_medicine_prescription,
    load_medicine_catalog,
    load_templates,
)
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


def _last_cycle_start(b03_path: Path, patient_id: str) -> dt.datetime | None:
    if not b03_path.exists():
        return None
    best: dt.datetime | None = None
    text = b03_path.read_text(encoding="utf-8")
    for columns, values in iter_insert_blocks(text, "HemodialysisRecords"):
        if "PatientId" not in columns or "CycleStartTime" not in columns:
            continue
        p_idx = columns.index("PatientId")
        c_idx = columns.index("CycleStartTime")
        for body in split_tuples(values):
            fields = split_fields(body)
            if fields[p_idx].strip("'") != patient_id:
                continue
            raw = fields[c_idx].strip("'")
            try:
                ts = dt.datetime.fromisoformat(raw.replace("+00", "+00:00"))
            except ValueError:
                continue
            if best is None or ts < best:
                best = ts
    return best


def restore_b07(base: Path, patient_id: str | None = None) -> list[tuple[str, str, bool]]:
    """คืน [(patient_id, prescription_id, written)] — ใช้ template จาก state keys."""
    state = GenState.load(state_path(base))
    b07_path = b_file(B07_FILE, base)
    b03_path = b_file(B03_FILE, base)
    b06_path = b_file(B06_FILE, base)
    catalog = load_medicine_catalog()
    templates = load_templates(catalog)
    results: list[tuple[str, str, bool]] = []

    patient_ids = [patient_id] if patient_id else list(state.patients.keys())
    for pid in patient_ids:
        existing = find_patient_uuid_in_file(b07_path, "MedicinePrescriptions", "PatientId", pid)
        if existing:
            ps = state.for_patient(pid)
            if not ps.medicine_prescription_ids:
                ps.medicine_prescription_ids["espogen"] = existing
            results.append((pid, existing, False))
            continue

        ps = state.for_patient(pid)
        admin = _last_cycle_start(b03_path, pid) or dt.datetime.combine(
            first_business_on_or_after(START_DATE),
            dt.time(5, 0),
            tzinfo=dt.timezone.utc,
        )
        keys = list(ps.medicine_prescription_ids.keys()) or ["espogen"]
        for key in keys:
            tmpl = templates.get(key) or templates["espogen"]
            rx_id = ps.medicine_prescription_ids.get(key)
            if key == "espogen" and not rx_id:
                rx_id = _prescription_id_from_b06(b06_path, pid)
            row = build_medicine_prescription(
                tmpl,
                pid,
                admin,
                prescription_id=rx_id,
                note=f"Hogwarts restore {tmpl.name}",
            )
            append_rows(b07_path, "MedicinePrescriptions", B07_COLUMNS, [row.fields], "hemo_gen restore B07")
            ps.medicine_prescription_ids[key] = row.id
            results.append((pid, row.id, True))

    state.save(state_path(base))
    return results

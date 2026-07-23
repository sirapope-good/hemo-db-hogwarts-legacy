"""Rebuild B07 MedicinePrescriptions for all (or one) patients — multi-med, ExpireDate NULL."""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

from hemo_gen.config import B03_FILE, B07_FILE, PATIENTS_FILE, SLOT_FILE, a_file, b_file, state_path
from hemo_gen.medicine_prescription import (
    B07_COLUMNS,
    build_medicine_prescription,
    load_medicine_catalog,
    load_templates,
    plan_patient_medication_keys,
)
from hemo_gen.patient_loader import load_patients, load_slot_assignments
from hemo_gen.profiles import build_profile
from hemo_gen.sql_io import append_rows, iter_insert_blocks, split_fields, split_tuples
from hemo_gen.state import GenState


def _first_session_admin(b03_path: Path, patient_id: str) -> dt.datetime:
    """Prefer earliest CycleStartTime from B03; fallback 2025-08-01 05:00 UTC."""
    fallback = dt.datetime(2025, 8, 1, 5, 0, tzinfo=dt.timezone.utc)
    if not b03_path.exists():
        return fallback
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
                # '2025-08-04 05:00:00+00'
                ts = dt.datetime.fromisoformat(raw.replace("+00", "+00:00"))
            except ValueError:
                continue
            if best is None or ts < best:
                best = ts
    return best or fallback


def rebuild_b07(base: Path, patient_id: str | None = None, *, dry_run: bool = False) -> tuple[int, int]:
    """
    Rewrite B07 for selected patients (or all).
    Returns (patients, prescription_rows).
    """
    catalog = load_medicine_catalog()
    templates = load_templates(catalog)
    patients = load_patients(a_file(PATIENTS_FILE, base))
    if patient_id:
        patients = [p for p in patients if p.patient_id == patient_id]
        if not patients:
            raise SystemExit(f"ไม่พบ patient {patient_id}")

    state = GenState.load(state_path(base))
    b03_path = b_file(B03_FILE, base)
    b07_path = b_file(B07_FILE, base)

    all_rows: list[list[str]] = []
    patient_count = 0
    for patient in patients:
        rng = random.Random(abs(hash(patient.patient_id)) % (2**31))
        slots = load_slot_assignments(a_file(SLOT_FILE, base), patient.patient_id)
        profile = build_profile(patient, slots, rng)
        keys = plan_patient_medication_keys(profile, rng, catalog)
        admin = _first_session_admin(b03_path, patient.patient_id)
        ps = state.for_patient(patient.patient_id)
        ps.medicine_prescription_ids = {}
        for key in keys:
            tmpl = templates[key]
            row = build_medicine_prescription(
                tmpl,
                patient.patient_id,
                admin,
                note=f"Hogwarts gen {tmpl.name} (with dialysis start {admin.date().isoformat()})",
            )
            all_rows.append(row.fields)
            ps.medicine_prescription_ids[key] = row.id
        patient_count += 1

    if dry_run:
        return patient_count, len(all_rows)

    # Full rewrite of B07 (clean ExpireDate / multi-med)
    b07_path.write_text("", encoding="utf-8")
    if all_rows:
        append_rows(b07_path, "MedicinePrescriptions", B07_COLUMNS, all_rows, "hemo_gen MedicinePrescriptions")
    else:
        b07_path.write_text("-- hemo_gen MedicinePrescriptions (empty)\n", encoding="utf-8")

    state.save(state_path(base))
    return patient_count, len(all_rows)

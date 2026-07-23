"""MedicinePrescription (B07) builders aligned with backend medicines.csv."""

from __future__ import annotations

import csv
import datetime as dt
import json
import random
import uuid
from dataclasses import dataclass
from pathlib import Path

from hemo_gen.config import CREATED_BY, DATA_DIR
from hemo_gen.profiles import PatientProfile
from hemo_gen.sql_io import sql_bool, sql_quote, to_sql_timestamp


B07_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "PatientId",
    "MedicineId", "Route", "DosePerTarget", "TargetLoopAmount", "Frequency",
    "AdministerDate", "InitSessionCount", "NonDialysis", "LimitDose",
    "HospitalName", "OverrideDoseAmount", "OverrideUnit", "Note", "ExpireDate",
    # Backend: RegimenLineId NOT NULL — new course defaults to Id (same as migration backfill).
    "RegimenLineId",
]


@dataclass(frozen=True)
class MedicineInfo:
    id: int
    name: str
    dose_amount: float | None
    med_type: int
    piece_unit: str


@dataclass
class MedicineTemplate:
    key: str
    medicine_id: int
    role: str
    name: str
    override_dose_amount: float | None
    override_unit: str | None
    route: int
    frequency: int
    dose_per_target: int
    target_loop_amount: int
    limit_dose: int
    init_session_count: int
    non_dialysis: bool
    execute_chance: float


@dataclass
class MedicinePrescriptionRow:
    id: str
    key: str
    role: str
    medicine_id: int
    non_dialysis: bool
    execute_chance: float
    route: int
    fields: list[str]


def load_medicines_csv(path: Path | None = None) -> dict[int, MedicineInfo]:
    csv_path = path or (DATA_DIR / "medicines.csv")
    out: dict[int, MedicineInfo] = {}
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            mid = int(row["Id"])
            dose_raw = (row.get("DoseAmount") or "").strip()
            dose = float(dose_raw) if dose_raw else None
            out[mid] = MedicineInfo(
                id=mid,
                name=(row.get("Name") or "").strip(),
                dose_amount=dose,
                med_type=int(row.get("MedType") or 0),
                piece_unit=(row.get("PieceUnit") or "").strip(),
            )
    return out


def load_medicine_catalog() -> dict:
    """Backward-compatible: returns raw JSON (templates + roles). Prefer load_templates()."""
    return json.loads((DATA_DIR / "medicine_catalog.json").read_text(encoding="utf-8"))


def load_templates(catalog: dict | None = None) -> dict[str, MedicineTemplate]:
    raw = catalog or load_medicine_catalog()
    medicines = load_medicines_csv()
    templates: dict[str, MedicineTemplate] = {}
    for key, t in raw.get("templates", {}).items():
        mid = int(t["medicine_id"])
        info = medicines.get(mid)
        if info is None:
            raise SystemExit(f"medicine_catalog key={key} medicine_id={mid} not in medicines.csv")
        unit = t.get("override_unit")
        if unit is None and info.piece_unit:
            unit = info.piece_unit
        dose = t.get("override_dose_amount")
        if dose is None and info.dose_amount is not None:
            dose = info.dose_amount
        templates[key] = MedicineTemplate(
            key=key,
            medicine_id=mid,
            role=str(t["role"]),
            name=info.name,
            override_dose_amount=float(dose) if dose is not None else None,
            override_unit=unit,
            route=int(t["route"]),
            frequency=int(t["frequency"]),
            dose_per_target=int(t["dose_per_target"]),
            target_loop_amount=int(t["target_loop_amount"]),
            limit_dose=int(t["limit_dose"]),
            init_session_count=int(t["init_session_count"]),
            non_dialysis=bool(t["non_dialysis"]),
            execute_chance=float(t.get("execute_chance", 0.0)),
        )
    return templates


def plan_patient_medication_keys(profile: PatientProfile, rng: random.Random, catalog: dict | None = None) -> list[str]:
    """
    Natural HD med set per patient:
    - 1 ESA (always)
    - optional IV iron (~60%)
    - heparin when dialysis anticoagulant looks heparin-like (~70%)
    - 1–2 oral CKD home meds (NonDialysis)
    """
    raw = catalog or load_medicine_catalog()
    roles = raw["roles"]
    keys: list[str] = []
    keys.append(rng.choice(roles["esa"]))
    if rng.random() < 0.6:
        keys.append(rng.choice(roles["iv_iron"]))
    ac = (profile.anticoagulant or "").lower()
    if "heparin" in ac or ac in ("heparin", "lmwh", ""):
        if rng.random() < 0.7:
            keys.append(rng.choice(roles["anticoagulant"]))
    oral_pool = list(roles["oral_ckd"])
    rng.shuffle(oral_pool)
    for key in oral_pool[: rng.choice([1, 2])]:
        keys.append(key)
    # stable unique order: esa, iron, anticoagulant, orals
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def build_medicine_prescription(
    template: MedicineTemplate,
    patient_id: str,
    administer_date: dt.datetime,
    *,
    prescription_id: str | None = None,
    note: str | None = None,
) -> MedicinePrescriptionRow:
    """Create B07 row. ExpireDate is always NULL (unlimited / active course)."""
    rx_id = prescription_id or str(uuid.uuid4())
    now = dt.datetime.now(dt.timezone.utc)
    ts = to_sql_timestamp(now)
    dose_sql = "NULL" if template.override_dose_amount is None else str(template.override_dose_amount)
    unit_sql = "NULL" if not template.override_unit else sql_quote(template.override_unit)
    note_text = note or f"Hogwarts gen {template.name}"
    fields = [
        sql_quote(rx_id),
        ts,
        sql_quote(CREATED_BY),
        ts,
        sql_quote(CREATED_BY),
        sql_bool(True),
        sql_quote(patient_id),
        str(template.medicine_id),
        str(template.route),
        str(template.dose_per_target),
        str(template.target_loop_amount),
        str(template.frequency),
        to_sql_timestamp(administer_date),
        str(template.init_session_count),
        sql_bool(template.non_dialysis),
        str(template.limit_dose),
        "NULL",
        dose_sql,
        unit_sql,
        sql_quote(note_text),
        "NULL",  # ExpireDate — only set when superseding a regimen line
        sql_quote(rx_id),  # RegimenLineId = Id for first course
    ]
    return MedicinePrescriptionRow(
        id=rx_id,
        key=template.key,
        role=template.role,
        medicine_id=template.medicine_id,
        non_dialysis=template.non_dialysis,
        execute_chance=template.execute_chance,
        route=template.route,
        fields=fields,
    )


def build_espogen_prescription(
    patient_id: str,
    administer_date: dt.datetime,
    expire_date: dt.date | None = None,  # ignored — kept for call-site compatibility
    catalog: dict | None = None,
    prescription_id: str | None = None,
) -> MedicinePrescriptionRow:
    """Legacy helper — Espogen only, ExpireDate always NULL."""
    _ = expire_date
    templates = load_templates(catalog)
    return build_medicine_prescription(
        templates["espogen"],
        patient_id,
        administer_date,
        prescription_id=prescription_id,
    )


def ensure_medicines_exist(templates: dict[str, MedicineTemplate], keys: list[str]) -> None:
    missing = [k for k in keys if k not in templates]
    if missing:
        raise SystemExit(f"unknown medicine template keys: {missing}")

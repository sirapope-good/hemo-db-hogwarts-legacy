from __future__ import annotations

import datetime as dt
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from hemo_gen.config import CREATED_BY, DATA_DIR
from hemo_gen.sql_io import sql_bool, sql_nullable_str, sql_quote, to_sql_timestamp


B07_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "PatientId",
    "MedicineId", "Route", "DosePerTarget", "TargetLoopAmount", "Frequency",
    "AdministerDate", "InitSessionCount", "NonDialysis", "LimitDose",
    "HospitalName", "OverrideDoseAmount", "OverrideUnit", "Note", "ExpireDate",
]


@dataclass
class MedicinePrescriptionRow:
    id: str
    fields: list[str]


def load_medicine_catalog() -> dict:
    return json.loads((DATA_DIR / "medicine_catalog.json").read_text(encoding="utf-8"))


def build_espogen_prescription(
    patient_id: str,
    administer_date: dt.datetime,
    expire_date: dt.date | None,
    catalog: dict | None = None,
) -> MedicinePrescriptionRow:
    cat = (catalog or load_medicine_catalog())["espogen"]
    rx_id = str(uuid.uuid4())
    now = dt.datetime.now(dt.timezone.utc)
    ts = to_sql_timestamp(now)
    exp = "NULL" if expire_date is None else to_sql_timestamp(
        dt.datetime.combine(expire_date, dt.time(23, 59), tzinfo=dt.timezone.utc)
    )
    fields = [
        sql_quote(rx_id),
        ts,
        sql_quote(CREATED_BY),
        ts,
        sql_quote(CREATED_BY),
        sql_bool(True),
        sql_quote(patient_id),
        str(cat["medicine_id"]),
        str(cat["route"]),
        str(cat["dose_per_target"]),
        str(cat["target_loop_amount"]),
        str(cat["frequency_bs"]),
        to_sql_timestamp(administer_date),
        str(cat["init_session_count"]),
        sql_bool(cat["non_dialysis"]),
        str(cat["limit_dose"]),
        "NULL",
        str(cat["override_dose_amount"]),
        sql_quote(cat["override_unit"]),
        sql_quote("Hogwarts gen Espogen"),
        exp,
    ]
    return MedicinePrescriptionRow(id=rx_id, fields=fields)

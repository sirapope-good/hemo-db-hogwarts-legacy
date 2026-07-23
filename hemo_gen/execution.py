from __future__ import annotations

import datetime as dt
import random
import uuid

from hemo_gen.config import CREATED_BY
from hemo_gen.medicine_prescription import MedicinePrescriptionRow
from hemo_gen.session_builder import BuiltSession
from hemo_gen.sql_io import sql_bool, sql_quote, to_sql_timestamp


B06_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "HemodialysisId",
    "Timestamp", "Type", "IsExecuted", "CoSign", "PrescriptionId", "OverrideRoute", "Quantity", "LotNo",
]


def build_medicine_execution(
    session: BuiltSession,
    medicine_prescription_id: str,
    override_route: int,
    rng: random.Random,
    *,
    execute_chance: float = 0.55,
) -> list[str] | None:
    if execute_chance <= 0 or rng.random() > execute_chance:
        return None
    exec_time = session.cycle_start + dt.timedelta(
        hours=rng.randint(2, 3), minutes=rng.randint(0, 45)
    )
    now = dt.datetime.now(dt.timezone.utc)
    return [
        sql_quote(str(uuid.uuid4())),
        to_sql_timestamp(now),
        sql_quote(CREATED_BY),
        to_sql_timestamp(now),
        sql_quote(CREATED_BY),
        sql_bool(True),
        sql_quote(session.hemo_id),
        to_sql_timestamp(exec_time),
        "0",
        sql_bool(True),
        "NULL",
        sql_quote(medicine_prescription_id),
        str(override_route),
        "1",
        "NULL",
    ]


def build_session_executions(
    session: BuiltSession,
    prescriptions: list[MedicinePrescriptionRow],
    rng: random.Random,
) -> list[list[str]]:
    """Create 0–n execution rows for in-center (NonDialysis=false) meds only."""
    rows: list[list[str]] = []
    for rx in prescriptions:
        if rx.non_dialysis:
            continue
        row = build_medicine_execution(
            session,
            rx.id,
            rx.route,
            rng,
            execute_chance=rx.execute_chance,
        )
        if row:
            rows.append(row)
    return rows

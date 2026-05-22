from __future__ import annotations

import datetime as dt
import random
import uuid

from hemo_gen.config import CREATED_BY
from hemo_gen.session_builder import BuiltSession
from hemo_gen.sql_io import sql_bool, sql_nullable_str, sql_quote, to_sql_timestamp


B06_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "HemodialysisId",
    "Timestamp", "Type", "IsExecuted", "CoSign", "PrescriptionId", "OverrideRoute", "Quantity", "LotNo",
]


def build_medicine_execution(
    session: BuiltSession,
    medicine_prescription_id: str,
    override_route: int,
    rng: random.Random,
) -> list[str] | None:
    if rng.random() > 0.55:
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

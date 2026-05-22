from __future__ import annotations

import datetime as dt
import json
import random
import uuid

from hemo_gen.config import CREATED_BY, DATA_DIR
from hemo_gen.session_builder import BuiltSession
from hemo_gen.sql_io import (
    sql_bigint_array,
    sql_bool,
    sql_nullable_str,
    sql_quote,
    to_sql_timestamp,
)


def load_assessment_map() -> dict:
    return json.loads((DATA_DIR / "assessment_map.json").read_text(encoding="utf-8"))


PRE_VITAL_COLUMNS = [
    "Id", "HemodialysisRecordId", "Timestamp", "BPS", "BPD", "HR", "RR", "Temp", "SpO2", "Posture",
]

ASSESSMENT_ITEM_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "HemosheetId",
    "AssessmentId", "Selected", "Checked", "Text", "Value", "IsReassessment",
]


def _vital_id(hemo_id: str, kind: str) -> str:
    return str(abs(hash((hemo_id, kind))) % (10**14) + 1)


def build_pre_vital(session: BuiltSession, rng: random.Random) -> list[str]:
    pre_time = session.cycle_start + dt.timedelta(minutes=rng.randint(20, 40))
    bps = session.pre_bps or (155 + rng.randint(5, 25))
    bpd = session.pre_bpd or (75 + rng.randint(0, 10))
    hr = session.pre_hr or (75 + rng.randint(0, 10))
    return [
        _vital_id(session.hemo_id, "pre"),
        sql_quote(session.hemo_id),
        to_sql_timestamp(pre_time),
        str(bps),
        str(bpd),
        str(hr),
        str(18 + rng.randint(0, 4)),
        str(round(36.0 + rng.uniform(-0.2, 0.2), 1)),
        str(98 + rng.randint(0, 2)),
        "1",
    ]


def build_post_vital(session: BuiltSession, pre_bps: int, rng: random.Random) -> list[str]:
    post_bps = max(110, pre_bps - rng.randint(5, 20))
    post_bpd = max(60, (session.pre_bpd or 80) - rng.randint(0, 8))
    post_hr = session.pre_hr or (75 + rng.randint(0, 10))
    return [
        _vital_id(session.hemo_id, "post"),
        sql_quote(session.hemo_id),
        to_sql_timestamp(session.completed),
        str(post_bps),
        str(post_bpd),
        str(post_hr),
        str(18 + rng.randint(0, 4)),
        str(round(36.0 + rng.uniform(-0.2, 0.2), 1)),
        str(98 + rng.randint(0, 2)),
        "1",
    ]


def _assessment_item(hemo_id: str, assessment_id: int, option_ids: list[int]) -> list[str]:
    now = dt.datetime.now(dt.timezone.utc)
    return [
        sql_quote(str(uuid.uuid4())),
        to_sql_timestamp(now),
        sql_quote(CREATED_BY),
        to_sql_timestamp(now),
        sql_quote(CREATED_BY),
        sql_bool(True),
        sql_quote(hemo_id),
        str(assessment_id),
        sql_bigint_array(option_ids),
        sql_bool(True),
        "NULL",
        "NULL",
        sql_bool(False),
    ]


def build_assessment_items(hemo_id: str, amap: dict | None = None) -> list[list[str]]:
    m = amap or load_assessment_map()
    pa = m["post_assessment"]
    rows = [
        _assessment_item(hemo_id, pa["complication"]["assessment_id"], [pa["complication"]["no_complication_option_id"]]),
        _assessment_item(hemo_id, pa["technical"]["assessment_id"], [pa["technical"]["no_complication_option_id"]]),
        _assessment_item(hemo_id, pa["nursing"]["assessment_id"], [pa["nursing"]["monitor_vital_signs_option_id"]]),
        _assessment_item(
            hemo_id,
            pa["health_education"]["assessment_id"],
            [
                pa["health_education"]["nutrition_option_id"],
                pa["health_education"]["vascular_access_option_id"],
                pa["health_education"]["exercise_option_id"],
            ],
        ),
    ]
    return rows

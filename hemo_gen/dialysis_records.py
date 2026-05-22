from __future__ import annotations

import datetime as dt
import random
import uuid

from hemo_gen.config import CREATED_BY, MACHINE_MODEL
from hemo_gen.session_builder import BuiltSession
from hemo_gen.sql_io import sql_bool, sql_quote, to_sql_timestamp


B04_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "HemodialysisId", "Timestamp",
    "Remaining", "Model", "Number", "BPS", "BPD", "MAP", "HR", "RR", "Temp", "BFR",
    "VP", "AP", "DP", "TMP", "UFRate", "UFTotal", "UFTarget", "HAV", "DFR", "DFRTarget",
    "DT", "DTTarget", "DC", "DCTarget", "BC", "NSS", "Glucose50", "HCO3", "NaTarget",
    "NaProfile", "UFProfile", "Mode", "BFAV", "IsFromMachine",
]


def _interval_str(hours: int, minutes: int) -> str:
    return sql_quote(f"{hours:02d}:{minutes:02d}:00")


def _map_value(bps: int, bpd: int) -> str:
    return str(int(bpd + (bps - bpd) / 3))


def build_dialysis_records(session: BuiltSession, profile_bed: int, rng: random.Random) -> list[list[str]]:
    count = rng.choice([8, 9])
    start = session.cycle_start
    end = session.cycle_end
    total_min = int((end - start).total_seconds() / 60)
    step = total_min // max(count - 1, 1)

    bps = session.pre_bps or (165 + rng.randint(0, 15))
    bpd = session.pre_bpd or (75 + rng.randint(0, 10))
    hr = session.pre_hr or (72 + rng.randint(0, 12))
    bfr_target = 250
    uf_target = session.uf_goal

    rows: list[list[str]] = []
    for i in range(count):
        ts = start + dt.timedelta(minutes=min(i * step, total_min))
        rem_h = max(0, (total_min - i * step) // 60)
        rem_m = max(0, (total_min - i * step) % 60)
        uf_total = round(uf_target * (i + 1) / count * rng.uniform(0.92, 1.0), 2)
        uf_rate = round(uf_total / max((i + 1) * step / 60, 0.5), 2) if step else 0.6
        bps_i = max(110, bps - i * rng.randint(0, 3))
        bpd_i = max(55, bpd - i * rng.randint(0, 2))
        hr_i = max(65, hr + rng.randint(-3, 3))
        rr_i = 18 + rng.randint(0, 4)
        temp_i = round(36.0 + rng.uniform(-0.3, 0.3), 1)

        give_nss = i >= count // 2 or rng.random() < 0.35
        nss = str(rng.randint(50, 200)) if give_nss else "NULL"
        glucose = str(rng.randint(50, 100)) if (give_nss and rng.random() < 0.5) else "NULL"

        now = dt.datetime.now(dt.timezone.utc)
        row_id = str(uuid.uuid4())
        rows.append(
            [
                sql_quote(row_id),
                to_sql_timestamp(now),
                sql_quote(CREATED_BY),
                to_sql_timestamp(now),
                sql_quote(CREATED_BY),
                sql_bool(True),
                sql_quote(session.hemo_id),
                to_sql_timestamp(ts),
                _interval_str(rem_h, rem_m),
                sql_quote(MACHINE_MODEL),
                str(profile_bed),
                str(bps_i),
                str(bpd_i),
                _map_value(bps_i, bpd_i),
                str(hr_i),
                str(rr_i),
                str(temp_i),
                str(min(bfr_target, 180 + i * 8)),
                str(50 + rng.randint(0, 30)),
                str(rng.randint(-5, 15)),
                str(-40 + rng.randint(0, 10)),
                str(70 + rng.randint(0, 20)),
                str(uf_rate),
                str(uf_total),
                str(uf_target),
                str(round(uf_rate * 0.3, 1)),
                str(480 + rng.randint(-20, 20)),
                "NULL",
                str(round(35.4 + rng.uniform(-0.2, 0.2), 1)),
                str(round(35.5, 1)),
                str(13 + rng.randint(0, 2)),
                "NULL",
                str(round(2.9 + rng.uniform(-0.1, 0.1), 2)),
                nss,
                glucose,
                "NULL",
                "NULL",
                "NULL",
                "NULL",
                sql_quote("OHDF"),
                "NULL",
                sql_bool(False),
            ]
        )
    return rows

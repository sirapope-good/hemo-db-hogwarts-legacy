"""เติม B04-DialysisRecords สำหรับ HemodialysisRecords ใน B03 ที่ยังไม่มีแถว DialysisRecord"""
from __future__ import annotations

import datetime as dt
import random
import re
from dataclasses import dataclass
from pathlib import Path

from hemo_gen.config import B03_FILE, B04_FILE
from hemo_gen.dialysis_records import B04_COLUMNS, build_dialysis_records
from hemo_gen.session_builder import B03_COLUMNS, BuiltSession
from hemo_gen.sql_io import append_rows, iter_insert_blocks, split_fields, split_tuples


@dataclass
class _SessionRef:
    hemo_id: str
    patient_id: str
    cycle_start: dt.datetime
    cycle_end: dt.datetime
    completed: dt.datetime
    uf_goal: float
    pre_weight: float
    post_weight: float
    bed_number: int


def _parse_ts(raw: str) -> dt.datetime:
    raw = raw.strip().strip("'")
    if raw.upper() == "NULL":
        raise ValueError("timestamp is NULL")
    if raw.endswith("+00"):
        return dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S+00").replace(tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _bed_from_field(bed_raw: str) -> int:
    if bed_raw.upper() == "NULL":
        return 11
    m = re.search(r"(\d+)", bed_raw.strip("'"))
    return int(m.group(1)) if m else 11


def _load_b03_sessions(b03_path: Path, patient_id: str | None) -> list[_SessionRef]:
    text = b03_path.read_text(encoding="utf-8")
    idx = {c: i for i, c in enumerate(B03_COLUMNS)}
    sessions: list[_SessionRef] = []

    for _cols, values_block in iter_insert_blocks(text, "HemodialysisRecords"):
        for body in split_tuples(values_block):
            fields = split_fields(body)
            if len(fields) < len(B03_COLUMNS):
                continue
            pid = fields[idx["PatientId"]].strip("'")
            if patient_id and pid != patient_id:
                continue
            def _float(name: str, default: float) -> float:
                v = fields[idx[name]]
                if v.upper() == "NULL":
                    return default
                return float(v)

            pre = _float("Dehydration_PreTotalWeight", 70.0)
            post = _float("Dehydration_PostTotalWeight", pre - 2.0)
            uf = _float("Dehydration_UFGoal", 0.0)
            if uf <= 0:
                uf = round(max(1.0, pre - post), 1)

            sessions.append(
                _SessionRef(
                    hemo_id=fields[idx["Id"]].strip("'"),
                    patient_id=pid,
                    cycle_start=_parse_ts(fields[idx["CycleStartTime"]]),
                    cycle_end=_parse_ts(fields[idx["CycleEndTime"]]),
                    completed=_parse_ts(fields[idx["CompletedTime"]]),
                    uf_goal=uf,
                    pre_weight=pre,
                    post_weight=post,
                    bed_number=_bed_from_field(fields[idx["Bed"]]),
                )
            )
    return sessions


def _existing_hemo_ids(b04_path: Path) -> set[str]:
    if not b04_path.exists():
        return set()
    text = b04_path.read_text(encoding="utf-8")
    return set(re.findall(r",TRUE,'([0-9a-f-]{36})','20\d{2}-", text, flags=re.IGNORECASE))


def _to_built(ref: _SessionRef, rng: random.Random) -> BuiltSession:
    return BuiltSession(
        hemo_id=ref.hemo_id,
        b03_fields=[],
        cycle_start=ref.cycle_start,
        cycle_end=ref.cycle_end,
        completed=ref.completed,
        uf_goal=ref.uf_goal,
        pre_weight=ref.pre_weight,
        post_weight=ref.post_weight,
        dry_weight=65.0,
        pre_bps=155 + rng.randint(5, 25),
        pre_bpd=75 + rng.randint(0, 10),
        pre_hr=75 + rng.randint(0, 10),
    )


def rebuild_b04(
    base_dir: Path,
    patient_id: str | None = None,
    replace_all: bool = False,
) -> tuple[int, int, int]:
    """
    Returns (sessions_scanned, sessions_backfilled, b04_rows_added).
    replace_all=True ลบ B04 แล้วสร้างใหม่ทุกรอบ (ได้ NSS/Glucose ตาม generator ล่าสุด).
    """
    b03_path = base_dir / B03_FILE
    b04_path = base_dir / B04_FILE
    if replace_all and b04_path.exists():
        b04_path.unlink()
    have = _existing_hemo_ids(b04_path)
    sessions = _load_b03_sessions(b03_path, patient_id)

    b04_rows: list[list[str]] = []
    filled = 0
    for ref in sessions:
        if not replace_all and ref.hemo_id in have:
            continue
        rng = random.Random(abs(hash(ref.hemo_id)) % (2**31))
        built = _to_built(ref, rng)
        b04_rows.extend(build_dialysis_records(built, ref.bed_number, rng))
        have.add(ref.hemo_id)
        filled += 1

    if b04_rows:
        append_rows(b04_path, "DialysisRecords", B04_COLUMNS, b04_rows, "hemo_gen backfill DialysisRecords")

    return len(sessions), filled, len(b04_rows)

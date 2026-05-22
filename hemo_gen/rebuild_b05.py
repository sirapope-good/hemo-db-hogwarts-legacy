"""สร้าง B05-Assessment.sql ใหม่จากทุก HemodialysisRecords ใน B03"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from pathlib import Path

from hemo_gen.assessment import (
    ASSESSMENT_ITEM_COLUMNS,
    PRE_VITAL_COLUMNS,
    build_assessment_items,
    build_post_vital,
    build_pre_vital,
    load_assessment_map,
)
from hemo_gen.config import B03_FILE, B05_FILE
from hemo_gen.session_builder import B03_COLUMNS, BuiltSession
from hemo_gen.sql_io import append_b05_bundle, iter_insert_blocks, split_fields, split_tuples


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
    dry_weight: float


def _parse_ts(raw: str) -> dt.datetime:
    raw = raw.strip().strip("'")
    if raw.endswith("+00"):
        return dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S+00").replace(tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _load_sessions(b03_path: Path, patient_id: str | None) -> list[_SessionRef]:
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

            def _f(name: str) -> str:
                return fields[idx[name]]

            def _float(name: str, default: float) -> float:
                v = _f(name)
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
                    hemo_id=_f("Id").strip("'"),
                    patient_id=pid,
                    cycle_start=_parse_ts(_f("CycleStartTime")),
                    cycle_end=_parse_ts(_f("CycleEndTime")),
                    completed=_parse_ts(_f("CompletedTime")),
                    uf_goal=uf,
                    pre_weight=pre,
                    post_weight=post,
                    dry_weight=max(50.0, pre - uf),
                )
            )
    return sessions


def _to_built(ref: _SessionRef, rng: random.Random) -> BuiltSession:
    pre_bps = 155 + rng.randint(5, 25)
    pre_bpd = 75 + rng.randint(0, 10)
    pre_hr = 75 + rng.randint(0, 10)
    return BuiltSession(
        hemo_id=ref.hemo_id,
        b03_fields=[],
        cycle_start=ref.cycle_start,
        cycle_end=ref.cycle_end,
        completed=ref.completed,
        uf_goal=ref.uf_goal,
        pre_weight=ref.pre_weight,
        post_weight=ref.post_weight,
        dry_weight=ref.dry_weight,
        pre_bps=pre_bps,
        pre_bpd=pre_bpd,
        pre_hr=pre_hr,
    )


def rebuild_b05(base_dir: Path, patient_id: str | None = None) -> tuple[int, int, int]:
    b03_path = base_dir / B03_FILE
    b05_path = base_dir / B05_FILE
    amap = load_assessment_map()
    pre_rows: list[list[str]] = []
    post_rows: list[list[str]] = []
    item_rows: list[list[str]] = []

    for ref in _load_sessions(b03_path, patient_id):
        rng = random.Random(abs(hash(ref.hemo_id)) % (2**31))
        built = _to_built(ref, rng)
        pre = build_pre_vital(built, rng)
        pre_rows.append(pre)
        post_rows.append(build_post_vital(built, int(pre[3]), rng))
        item_rows.extend(build_assessment_items(built.hemo_id, amap))

    if b05_path.exists():
        b05_path.unlink()
    if pre_rows or post_rows or item_rows:
        append_b05_bundle(
            b05_path,
            pre_rows,
            post_rows,
            item_rows,
            PRE_VITAL_COLUMNS,
            PRE_VITAL_COLUMNS,
            ASSESSMENT_ITEM_COLUMNS,
        )
    return len(pre_rows), len(post_rows), len(item_rows)

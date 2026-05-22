"""ตรวจค่า Dehydration ใน B03-HemodialysisRecords.sql"""

from __future__ import annotations

from pathlib import Path

from hemo_gen.config import B03_FILE
from hemo_gen.session_builder import B03_COLUMNS
from hemo_gen.sql_io import iter_insert_blocks, split_fields, split_tuples


def validate_b03(base_dir: Path, patient_id: str | None = None) -> tuple[int, int, list[str]]:
    path = base_dir / B03_FILE
    if not path.exists():
        return 0, 0, [f"ไม่พบ {B03_FILE}"]

    idx = {c: i for i, c in enumerate(B03_COLUMNS)}
    issues: list[str] = []
    total = 0
    bad = 0

    text = path.read_text(encoding="utf-8")
    for columns, values in iter_insert_blocks(text, "HemodialysisRecords"):
        for body in split_tuples(values):
            total += 1
            fields = split_fields(body)
            if len(fields) < len(B03_COLUMNS):
                bad += 1
                issues.append(f"tuple #{total}: ฟิลด์ไม่ครบ ({len(fields)}/{len(B03_COLUMNS)})")
                continue
            pid = fields[idx["PatientId"]].strip("'")
            if patient_id and pid != patient_id:
                continue
            pre = fields[idx["Dehydration_PreTotalWeight"]]
            post = fields[idx["Dehydration_PostTotalWeight"]]
            last = fields[idx["Dehydration_LastPostWeight"]]
            uf = fields[idx["Dehydration_UFGoal"]]
            cycle = fields[idx["CycleStartTime"]].strip("'")[:10]
            problems = []
            for name, val in (
                ("PreTotalWeight", pre),
                ("PostTotalWeight", post),
                ("LastPostWeight", last),
                ("UFGoal", uf),
            ):
                if val.upper() == "NULL" or val == "0":
                    problems.append(name)
            if problems:
                bad += 1
                issues.append(f"{pid} {cycle}: {', '.join(problems)} = {val}")

    return bad, total, issues

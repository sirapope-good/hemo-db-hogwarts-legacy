"""แก้ Dehydration ใน B03 seed ที่ UFGoal=0 หรือ PostTotalWeight ว่าง"""
from __future__ import annotations

import re
from pathlib import Path

from hemo_gen.config import B03_FILE
from hemo_gen.session_builder import B03_COLUMNS
from hemo_gen.sql_io import iter_insert_blocks, split_fields, split_tuples


def _patch_tuple_body(body: str) -> str:
    idx = {c: i for i, c in enumerate(B03_COLUMNS)}
    fields = split_fields(body)
    if len(fields) < len(B03_COLUMNS):
        return body

    def _float(name: str) -> float | None:
        v = fields[idx[name]]
        if v.upper() == "NULL":
            return None
        return float(v)

    pre = _float("Dehydration_PreTotalWeight")
    post = _float("Dehydration_PostTotalWeight")
    uf = _float("Dehydration_UFGoal")

    if pre is None or pre <= 0:
        return body

    changed = False
    if uf is None or uf <= 0:
        if post is not None and post > 0:
            uf = round(max(1.0, pre - post), 1)
        else:
            uf = round(max(1.5, pre * 0.03), 1)
        fields[idx["Dehydration_UFGoal"]] = str(uf)
        changed = True

    if post is None or post <= 0:
        post = round(pre - (uf or 2.0), 1)
        fields[idx["Dehydration_PostTotalWeight"]] = str(post)
        changed = True

    if not changed:
        return body
    return ",".join(fields)


def patch_b03_weights(base_dir: Path) -> tuple[int, int]:
    path = base_dir / B03_FILE
    text = path.read_text(encoding="utf-8")
    patched = 0
    total = 0

    def _repl_block(values_block: str) -> str:
        nonlocal patched, total
        bodies = split_tuples(values_block)
        new_bodies = []
        for body in bodies:
            total += 1
            new_body = _patch_tuple_body(body)
            if new_body != body:
                patched += 1
            new_bodies.append(new_body)
        return ",\n".join(f"({b})" for b in new_bodies)

    pattern = (
        r'(INSERT\s+INTO\s+local\."HemodialysisRecords"\s*\(.*?\)\s*VALUES\s*)'
        r"(.*?)(;\s*)"
    )

    def _sub(m: re.Match) -> str:
        return m.group(1) + _repl_block(m.group(2)) + m.group(3)

    new_text = re.sub(pattern, _sub, text, flags=re.IGNORECASE | re.DOTALL)
    path.write_text(new_text, encoding="utf-8")
    return patched, total

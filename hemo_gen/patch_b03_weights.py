"""แก้ Dehydration / StaffAllocation ใน B03 ให้ตรงระบบจริง"""
from __future__ import annotations

import re
from pathlib import Path

from hemo_gen.config import B03_FILE
from hemo_gen.session_builder import B03_COLUMNS
from hemo_gen.sql_io import iter_insert_blocks, split_fields, split_tuples

_ZERO_INSTEAD_OF_NULL = (
    "Dehydration_WheelchairWeight",
    "Dehydration_ClothWeight",
    "Dehydration_FoodDrinkWeight",
)
_EMPTY_UUID_ARRAY = "'{}'::uuid[]"
_STAFF_COL = "StaffAllocation"
_NURSES_COL = "NursesInShift"


def _normalize_zero_weights(fields: list[str], idx: dict[str, int]) -> bool:
    changed = False
    for col in _ZERO_INSTEAD_OF_NULL:
        if fields[idx[col]].upper() == "NULL":
            fields[idx[col]] = "0"
            changed = True
    if fields[idx["Dehydration_PostWheelchairWeight"]] == "0":
        fields[idx["Dehydration_PostWheelchairWeight"]] = "NULL"
        changed = True
    return changed


def _ensure_staff_allocation(fields: list[str], idx: dict[str, int]) -> bool:
    if _STAFF_COL not in idx:
        nurses_i = idx[_NURSES_COL]
        fields.insert(nurses_i + 1, _EMPTY_UUID_ARRAY)
        return True
    if fields[idx[_STAFF_COL]].upper() == "NULL":
        fields[idx[_STAFF_COL]] = _EMPTY_UUID_ARRAY
        return True
    return False


def _insert_header_staff_allocation(text: str) -> str:
    if f'"{_STAFF_COL}"' in text:
        return text
    return text.replace(
        f'"{_NURSES_COL}", "TreatmentNo"',
        f'"{_NURSES_COL}", "{_STAFF_COL}", "TreatmentNo"',
    )


def _patch_tuple_body(body: str) -> str:
    fields = split_fields(body)
    expected = len(B03_COLUMNS)
    if len(fields) not in (expected, expected - 1):
        return body

    idx = {c: i for i, c in enumerate(B03_COLUMNS)}
    changed = False
    if len(fields) == expected - 1:
        fields.insert(idx[_NURSES_COL] + 1, _EMPTY_UUID_ARRAY)
        changed = True

    changed = _normalize_zero_weights(fields, idx) or changed
    changed = _ensure_staff_allocation(fields, idx) or changed

    def _float(name: str) -> float | None:
        v = fields[idx[name]]
        if v.upper() == "NULL":
            return None
        return float(v)

    pre = _float("Dehydration_PreTotalWeight")
    if pre is not None and pre > 0:
        post = _float("Dehydration_PostTotalWeight")
        uf = _float("Dehydration_UFGoal")
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
    text = _insert_header_staff_allocation(path.read_text(encoding="utf-8"))
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

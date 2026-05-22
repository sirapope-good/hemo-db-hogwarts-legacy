from __future__ import annotations

import re
from pathlib import Path


def sql_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def sql_nullable_str(value: str | None) -> str:
    if value is None:
        return "NULL"
    return sql_quote(value)


def sql_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def sql_uuid(value: str) -> str:
    return sql_quote(value)


def sql_uuid_array(uuids: list[str]) -> str:
    if not uuids:
        return "'{}'::uuid[]"
    inner = ",".join(sql_quote(u) for u in uuids)
    return f"ARRAY[{inner}]::uuid[]"


def sql_bigint_array(ids: list[int]) -> str:
    if not ids:
        return "ARRAY[]::bigint[]"
    inner = ",".join(str(i) for i in ids)
    return f"ARRAY[{inner}]::bigint[]"


def to_sql_timestamp(ts) -> str:
    import datetime as dt

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    ts_utc = ts.astimezone(dt.timezone.utc)
    return sql_quote(ts_utc.strftime("%Y-%m-%d %H:%M:%S+00"))


def iter_insert_blocks(text: str, table: str):
    pattern = (
        rf'INSERT\s+INTO\s+local\."{re.escape(table)}"\s*\((.*?)\)\s*VALUES\s*'
        rf"(.*?);\s*"
    )
    for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
        columns = [c.strip().strip('"') for c in m.group(1).split(",")]
        values = m.group(2).strip()
        yield columns, values


def extract_insert_block(text: str, table: str) -> tuple[str, list[str], str] | None:
    for columns, values in iter_insert_blocks(text, table):
        col_sql = ", ".join(f'"{c}"' for c in columns)
        prefix = f'INSERT INTO local."{table}"(\n\t{col_sql}\n)\nVALUES\n'
        return prefix, columns, values
    return None


def split_tuples(values_block: str) -> list[str]:
    tuples: list[str] = []
    in_quote = False
    depth = 0
    start = -1
    i = 0
    while i < len(values_block):
        ch = values_block[i]
        if ch == "'":
            if i + 1 < len(values_block) and values_block[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and start != -1:
                    tuples.append(values_block[start + 1 : i])
                    start = -1
        i += 1
    return tuples


def _format_insert(table: str, columns: list[str], rows: list[list[str]], header_comment: str) -> str:
    values_sql = ",\n".join("(" + ",".join(r) + ")" for r in rows)
    return (
        f"-- {header_comment}\n"
        f'INSERT INTO local."{table}"(\n\t'
        + ", ".join(f'"{c}"' for c in columns)
        + "\n)\nVALUES\n"
        + values_sql
        + ";\n"
    )


def append_b05_bundle(
    path: Path,
    pre_rows: list[list[str]],
    post_rows: list[list[str]],
    item_rows: list[list[str]],
    pre_columns: list[str],
    post_columns: list[str],
    item_columns: list[str],
) -> None:
    chunks: list[str] = []
    if pre_rows:
        chunks.append(_format_insert("HemodialysisRecords_PreVitalsign", pre_columns, pre_rows, "hemo_gen PreVitalsign"))
    if post_rows:
        chunks.append(_format_insert("HemodialysisRecords_PostVitalsign", post_columns, post_rows, "hemo_gen PostVitalsign"))
    if item_rows:
        chunks.append(_format_insert("AssessmentItems", item_columns, item_rows, "hemo_gen AssessmentItems"))
    if not chunks:
        return
    block = "\n".join(chunks)
    if path.exists() and path.stat().st_size > 0:
        path.write_text(path.read_text(encoding="utf-8").rstrip() + "\n\n" + block, encoding="utf-8")
    else:
        path.write_text(block, encoding="utf-8")


def append_rows(path: Path, table: str, columns: list[str], rows: list[list[str]], header_comment: str) -> None:
    """Append rows as a new INSERT block — never merge into existing seed VALUES (avoids corrupting multi-line seeds)."""
    if not rows:
        return
    block = _format_insert(table, columns, rows, header_comment)
    if path.exists() and path.stat().st_size > 0:
        path.write_text(path.read_text(encoding="utf-8").rstrip() + "\n\n" + block, encoding="utf-8")
    else:
        path.write_text(block, encoding="utf-8")


def patient_exists_in_file(path: Path, table: str, patient_col: str, patient_id: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    for columns, values_block in iter_insert_blocks(text, table):
        if patient_col not in columns:
            continue
        idx = columns.index(patient_col)
        for body in split_tuples(values_block):
            fields = split_fields(body)
            if len(fields) > idx and fields[idx].strip("'") == patient_id:
                return True
    return False


def split_fields(tuple_body: str) -> list[str]:
    fields: list[str] = []
    in_quote = False
    start = 0
    i = 0
    n = len(tuple_body)
    while i < n:
        if not in_quote and tuple_body[i : i + 6].upper() == "ARRAY[":
            m = re.match(r"ARRAY\[.*?\]::\w+\[\]", tuple_body[i:], flags=re.IGNORECASE | re.DOTALL)
            if m:
                end = i + m.end()
                fields.append(tuple_body[start:end].strip())
                start = end
                if start < n and tuple_body[start] == ",":
                    start += 1
                i = start
                continue
        ch = tuple_body[i]
        if ch == "'":
            if i + 1 < n and tuple_body[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            fields.append(tuple_body[start:i].strip())
            start = i + 1
        i += 1
    fields.append(tuple_body[start:].strip())
    return fields


def find_patient_uuid_in_file(path: Path, table: str, patient_col: str, patient_id: str, id_col: str = "Id") -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    for columns, values_block in iter_insert_blocks(text, table):
        if patient_col not in columns or id_col not in columns:
            continue
        p_idx = columns.index(patient_col)
        id_idx = columns.index(id_col)
        for body in split_tuples(values_block):
            fields = split_fields(body)
            if len(fields) > p_idx and fields[p_idx].strip("'") == patient_id:
                return fields[id_idx].strip("'")
    return None


def max_treatment_no_for_patient(path: Path, patient_id: str) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    best = 0
    for columns, values in iter_insert_blocks(text, "HemodialysisRecords"):
        if "PatientId" not in columns or "TreatmentNo" not in columns:
            continue
        p_idx = columns.index("PatientId")
        t_idx = columns.index("TreatmentNo")
        for body in split_tuples(values):
            fields = split_fields(body)
            if fields[p_idx].strip("'") != patient_id:
                continue
            try:
                best = max(best, int(fields[t_idx]))
            except ValueError:
                pass
    return best

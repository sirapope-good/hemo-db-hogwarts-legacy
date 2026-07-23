#!/usr/bin/env python3
from __future__ import annotations

"""
ซ่อม/เติม B03-HemodialysisRecords (UTC, ข้ามเสาร์–อาทิตย์)

โหมดหลัก (gap-fill — default) แบบซ่อมไฟล์:
1) โหลดคู่ (PatientId, SectionId) จาก 11-SectionSlotPatient + เวลาเริ่ม section จาก 08-Sections
2) ต่อคู่ (patient, section): ดูวันที่มีแถวใน B03 จริง (จากไฟล์)
3) เติมวันทำการที่หายระหว่างสองวันที่ติดกัน ถ้าห่างไม่เกิน --max-internal-gap-days (กันย้อนหลังมหาศาล)
4) เติมหางจากวันล่าสุดของคู่นั้น +1 ถึง --to-date (วันทำการ, UTC)
5) template แถวใหม่: แถวล่าสุดของคนนั้น+section เดียวกัน ถ้าไม่มีใช้แถวล่าสุดของคนนั้น
6) merge เข้า B03 เดิมได้ตามเดิม

โหมด tail (เก่า): เติมเฉพาะหลังวันล่าสุด โดย clone ทุกแถวของวันล่าสุด
"""

import argparse
import datetime as dt
import re
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

# scripts/legacy/ -> scripts/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _extract_insert_columns_and_values(sql_text: str) -> tuple[list[str], str]:
    """ดึงชื่อคอลัมน์และ values block ของ INSERT HemodialysisRecords."""
    insert_match = re.search(
        r'INSERT\s+INTO\s+local\."HemodialysisRecords"\s*\((.*?)\)\s*VALUES\s*(.*);\s*$',
        sql_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not insert_match:
        raise ValueError('ไม่พบ INSERT INTO local."HemodialysisRecords" ที่ parse ได้')

    raw_columns = insert_match.group(1)
    values_block = insert_match.group(2)
    columns = [c.strip().strip('"') for c in raw_columns.split(",")]
    return columns, values_block


def _split_tuples(values_block: str) -> list[str]:
    """แยก values block ออกเป็น tuple body ทีละแถว โดยรองรับ quote/comma ภายในค่า."""
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


def _split_fields(tuple_body: str) -> list[str]:
    """แยกฟิลด์ของ tuple เดียว โดยไม่แตก comma ที่อยู่ใน string literal."""
    fields: list[str] = []
    in_quote = False
    start = 0
    i = 0

    while i < len(tuple_body):
        ch = tuple_body[i]
        if ch == "'":
            if i + 1 < len(tuple_body) and tuple_body[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            fields.append(tuple_body[start:i].strip())
            start = i + 1
        i += 1

    fields.append(tuple_body[start:].strip())
    return fields


def _parse_sql_timestamp(token: str) -> dt.datetime:
    """แปลง timestamp SQL literal เป็น datetime."""
    if not (token.startswith("'") and token.endswith("'")):
        raise ValueError(f"คาดว่าเป็น timestamp แบบ quoted แต่เจอ: {token}")
    raw = token[1:-1].replace(" ", "T")
    return dt.datetime.fromisoformat(raw)


def _sql_quote(text: str) -> str:
    """escape string สำหรับ SQL literal."""
    return "'" + text.replace("'", "''") + "'"


def _to_sql_timestamp(ts: dt.datetime) -> str:
    """serialize datetime เป็น SQL timestamp (UTC)."""
    ts_utc = ts.astimezone(dt.timezone.utc)
    return _sql_quote(ts_utc.strftime("%Y-%m-%d %H:%M:%S+00"))


def _resolve_today_date(today_tz: str) -> dt.date:
    """คำนวณ today จาก timezone ที่กำหนด แล้วคืนค่าเป็น date."""
    # บางเครื่อง (โดยเฉพาะ Windows ที่ไม่มี tzdata) หา IANA timezone ไม่เจอ
    # จึง fallback สำหรับ Bangkok ให้เป็น UTC+7 แบบไม่พึ่ง timezone DB
    try:
        tz = ZoneInfo(today_tz)
    except ZoneInfoNotFoundError:
        if today_tz == "Asia/Bangkok":
            tz = dt.timezone(dt.timedelta(hours=7))
        else:
            raise
    return dt.datetime.now(tz).date()


def _business_days(start_date: dt.date, end_date: dt.date) -> list[dt.date]:
    """คืนรายการวันทำการ (จันทร์-ศุกร์) ในช่วงวันที่ที่กำหนด."""
    days: list[dt.date] = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            days.append(current)
        current += dt.timedelta(days=1)
    return days


def _load_sections_time_map(path: Path) -> dict[str, int]:
    """โหลด mapping เวลาเริ่ม HH:MM:SS -> SectionId จาก 08-Sections.sql."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*(\d+)\s*,.*?,\s*(-?\d+)\s*,\s*'(\d{2}:\d{2}:\d{2})'\s*\)",
        re.DOTALL,
    )
    result: dict[str, int] = {}
    for match in pattern.finditer(text):
        section_id = int(match.group(1))
        start_time = match.group(3)
        result[start_time] = section_id
    return result


def _load_section_start_time_by_id(path: Path) -> dict[int, str]:
    """SectionId -> เวลาเริ่ม HH:MM:SS (จาก 08-Sections.sql)"""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*(\d+)\s*,.*?,\s*(-?\d+)\s*,\s*'(\d{2}:\d{2}:\d{2})'\s*\)",
        re.DOTALL,
    )
    out: dict[int, str] = {}
    for match in pattern.finditer(text):
        section_id = int(match.group(1))
        start_time = match.group(3)
        out[section_id] = start_time
    return out


def _load_section_slot_pairs(path: Path) -> set[tuple[str, int]]:
    """โหลดคู่ (PatientId, SectionId) ที่ควรมีรายการต่อวันจาก 11-SectionSlotPatient.sql (unique ต่อคู่)"""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*'[^']+'\s*,\s*'[^']+'\s*,\s*'[^']+'\s*,\s*'[^']+'\s*,\s*true\s*,\s*(\d+)\s*,\s*'(\d+)'\s*,\s*\d+\s*\)",
        re.IGNORECASE,
    )
    pairs: set[tuple[str, int]] = set()
    for match in pattern.finditer(text):
        section_id = int(match.group(1))
        patient_id = match.group(2)
        pairs.add((patient_id, section_id))
    return pairs


def _load_schedule_meta(path: Path) -> dict[str, set[str]]:
    """โหลดเวลาที่ unit เปิดให้บริการจาก 09-ScheduleMeta.sql."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*\d+\s*,.*?,\s*true\s*,\s*-?\d+\s*,\s*'([^']+)'\s*,\s*(NULL|'[^']+')\s*,\s*(NULL|'[^']+')\s*,\s*(NULL|'[^']+')\s*,\s*(NULL|'[^']+')\s*,\s*(NULL|'[^']+')\s*,\s*(NULL|'[^']+')\s*\)",
        re.IGNORECASE | re.DOTALL,
    )
    unit_times: dict[str, set[str]] = {}
    for match in pattern.finditer(text):
        unit_name = match.group(1)
        raw_times = match.groups()[1:]
        times: set[str] = set()
        for token in raw_times:
            if token != "NULL":
                times.add(token.strip("'"))
        if times:
            unit_times[unit_name] = times
    return unit_times


def _load_shift_meta_months(path: Path) -> set[dt.date]:
    """โหลดเดือนที่อยู่ใน ShiftMeta (ใช้แค่เตือนความสอดคล้องข้อมูล)."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r",\s*'(\d{4}-\d{2}-\d{2})'\s*,\s*\d+\s*\)")
    months: set[dt.date] = set()
    for match in pattern.finditer(text):
        month_date = dt.date.fromisoformat(match.group(1))
        months.add(month_date.replace(day=1))
    return months


def _pick_template_row(
    patient: str,
    section_id: int,
    by_patient_section: dict[tuple[str, int], list[list[str]]],
    by_patient: dict[str, list[list[str]]],
    cycle_idx: int,
) -> list[str] | None:
    """เลือกแถว template: ล่าสุดตามวันที่ของ (patient, section) ก่อน แล้วจึงล่าสุดของ patient"""
    key = (patient, section_id)
    candidates = by_patient_section.get(key) or []
    if candidates:
        return max(candidates, key=lambda r: _parse_sql_timestamp(r[cycle_idx]))
    any_rows = by_patient.get(patient) or []
    if any_rows:
        return max(any_rows, key=lambda r: _parse_sql_timestamp(r[cycle_idx]))
    return None


def _build_template_indexes(
    rows: list[list[str]],
    patient_idx: int,
    shift_idx: int,
    cycle_idx: int,
) -> tuple[dict[tuple[str, int], list[list[str]]], dict[str, list[list[str]]]]:
    """จัดกลุ่มแถวตาม (patient, ShiftSectionId) และตาม patient สำหรับหา template"""
    by_ps: dict[tuple[str, int], list[list[str]]] = defaultdict(list)
    by_p: dict[str, list[list[str]]] = defaultdict(list)
    for row in rows:
        p = row[patient_idx].strip("'")
        s = int(row[shift_idx])
        by_ps[(p, s)].append(row)
        by_p[p].append(row)
    return by_ps, by_p


def _build_gap_fill_rows(
    rows: list[list[str]],
    col_idx: dict[str, int],
    to_date: dt.date,
    sections_by_time: dict[str, int],
    slot_pairs: set[tuple[str, int]],
    unit_schedule_times: dict[str, set[str]],
    section_start_by_id: dict[int, str],
    max_internal_gap_days: int,
) -> tuple[list[list[str]], dict[str, int]]:
    """
    เติมช่องว่างแบบซ่อมไฟล์ (สอดคล้อง seed แบบเว้นวัน):

    ต่อคู่ (patient, SectionId) จาก slot:
    - รวบวันที่ที่มีข้อมูลจริงในไฟล์ของคู่นั้น
    - เติมวันทำการที่ "หาย" ระหว่างสองวันที่ติดกันในปฏิทิน ถ้าห่างไม่เกิน max_internal_gap_days
      (ช่องว่างยาวเกินนี้ถือว่าไม่มารักษาไม่เติมกลาง — กันการสร้างย้อนหลังมหาศาล)
    - เติมหาง: จากวันล่าสุดของคู่นั้น +1 ถึง to_date (วันทำการ)
    """
    cycle_idx = col_idx["CycleStartTime"]
    end_idx = col_idx["CycleEndTime"]
    completed_idx = col_idx["CompletedTime"]
    created_idx = col_idx["Created"]
    updated_idx = col_idx["Updated"]
    id_idx = col_idx["Id"]
    treatment_idx = col_idx["TreatmentNo"]
    patient_idx = col_idx["PatientId"]
    shift_idx = col_idx["ShiftSectionId"]
    ward_idx = col_idx["Ward"]

    if not rows:
        return [], {"pairs_tail_lag": 0, "calendar_internal_missing": 0, "calendar_tail_missing": 0}

    patients_in_file = {r[patient_idx].strip("'") for r in rows}
    slot_pairs_use = {(p, s) for (p, s) in slot_pairs if p in patients_in_file}
    if not slot_pairs_use:
        return [], {"pairs_tail_lag": 0, "calendar_internal_missing": 0, "calendar_tail_missing": 0}

    by_ps, by_p = _build_template_indexes(rows, patient_idx, shift_idx, cycle_idx)

    existing: set[tuple[str, dt.date, int]] = set()
    for row in rows:
        p = row[patient_idx].strip("'")
        d = _parse_sql_timestamp(row[cycle_idx]).date()
        s = int(row[shift_idx])
        existing.add((p, d, s))

    orig_existing = frozenset(existing)

    max_treatment_by_patient: dict[str, int] = {}
    for row in rows:
        patient = row[patient_idx].strip("'")
        treatment_no = int(row[treatment_idx])
        max_treatment_by_patient[patient] = max(max_treatment_by_patient.get(patient, 0), treatment_no)

    pending: list[tuple[dt.date, str, int, list[str]]] = []

    def _try_add_day(day: dt.date, patient: str, section_id: int) -> None:
        if (patient, day, section_id) in existing:
            return
        start_hms = section_start_by_id.get(section_id)
        if not start_hms:
            return
        tpart = dt.time.fromisoformat(start_hms)
        new_cycle = dt.datetime.combine(day, tpart, tzinfo=dt.timezone.utc)
        start_key = new_cycle.strftime("%H:%M:%S")
        if sections_by_time.get(start_key) != section_id:
            return
        src = _pick_template_row(patient, section_id, by_ps, by_p, cycle_idx)
        if src is None:
            return
        new_row = [x for x in src]
        src_cycle = _parse_sql_timestamp(src[cycle_idx])
        src_end = _parse_sql_timestamp(src[end_idx])
        src_completed = _parse_sql_timestamp(src[completed_idx])
        src_created = _parse_sql_timestamp(src[created_idx])
        src_updated = _parse_sql_timestamp(src[updated_idx])
        delta_end = src_end - src_cycle
        delta_completed = src_completed - src_cycle
        delta_created = src_created - src_cycle
        delta_updated = src_updated - src_cycle
        new_row[cycle_idx] = _to_sql_timestamp(new_cycle)
        new_row[end_idx] = _to_sql_timestamp(new_cycle + delta_end)
        new_row[completed_idx] = _to_sql_timestamp(new_cycle + delta_completed)
        new_row[created_idx] = _to_sql_timestamp(new_cycle + delta_created)
        new_row[updated_idx] = _to_sql_timestamp(new_cycle + delta_updated)
        new_row[id_idx] = _sql_quote(str(uuid.uuid4()))
        new_row[shift_idx] = str(section_id)
        ward_name = new_row[ward_idx].strip("'")
        allowed_times = unit_schedule_times.get(ward_name)
        if allowed_times is not None and start_key not in allowed_times:
            return
        pending.append((day, patient, section_id, new_row))
        existing.add((patient, day, section_id))

    pairs_tail_lag = 0
    calendar_internal_missing = 0
    calendar_tail_missing = 0

    for patient, section_id in sorted(slot_pairs_use):
        ds = sorted({d for (p, d, s) in orig_existing if p == patient and s == section_id})
        if not ds:
            continue
        if ds[-1] < to_date:
            pairs_tail_lag += 1
        for a, b in zip(ds, ds[1:]):
            if max_internal_gap_days > 0 and (b - a).days > max_internal_gap_days:
                continue
            for day in _business_days(a + dt.timedelta(days=1), b - dt.timedelta(days=1)):
                if (patient, day, section_id) not in orig_existing:
                    calendar_internal_missing += 1
                _try_add_day(day, patient, section_id)
        last = ds[-1]
        for day in _business_days(last + dt.timedelta(days=1), to_date):
            if (patient, day, section_id) not in orig_existing:
                calendar_tail_missing += 1
            _try_add_day(day, patient, section_id)

    pending.sort(key=lambda x: (x[1], x[0], x[2]))
    generated: list[list[str]] = []
    for _day, patient, _section_id, new_row in pending:
        max_treatment_by_patient[patient] = max_treatment_by_patient.get(patient, 0) + 1
        new_row[treatment_idx] = str(max_treatment_by_patient[patient])
        generated.append(new_row)

    stats = {
        "pairs_tail_lag": pairs_tail_lag,
        "calendar_internal_missing": calendar_internal_missing,
        "calendar_tail_missing": calendar_tail_missing,
    }
    return generated, stats


def _build_tail_rows(
    rows: list[list[str]],
    col_idx: dict[str, int],
    to_date: dt.date,
    sections_by_time: dict[str, int],
    valid_patient_section_pairs: set[tuple[str, int]],
    unit_schedule_times: dict[str, set[str]],
) -> list[list[str]]:
    """
    โหมดเดิม: เติมเฉพาะหลังวันล่าสุด โดย clone ทุกแถวของวันล่าสุด
    """
    cycle_idx = col_idx["CycleStartTime"]
    end_idx = col_idx["CycleEndTime"]
    completed_idx = col_idx["CompletedTime"]
    created_idx = col_idx["Created"]
    updated_idx = col_idx["Updated"]
    id_idx = col_idx["Id"]
    treatment_idx = col_idx["TreatmentNo"]
    patient_idx = col_idx["PatientId"]
    shift_idx = col_idx["ShiftSectionId"]
    ward_idx = col_idx["Ward"]

    max_cycle_date = max(_parse_sql_timestamp(r[cycle_idx]).date() for r in rows)
    latest_rows = [r for r in rows if _parse_sql_timestamp(r[cycle_idx]).date() == max_cycle_date]
    if not latest_rows:
        return []

    max_treatment_by_patient: dict[str, int] = {}
    for row in rows:
        patient = row[patient_idx].strip("'")
        treatment_no = int(row[treatment_idx])
        max_treatment_by_patient[patient] = max(max_treatment_by_patient.get(patient, 0), treatment_no)

    target_days = _business_days(max_cycle_date + dt.timedelta(days=1), to_date)
    generated: list[list[str]] = []

    for target_day in target_days:
        for src in latest_rows:
            new_row = src.copy()
            patient = src[patient_idx].strip("'")

            src_cycle = _parse_sql_timestamp(src[cycle_idx])
            src_end = _parse_sql_timestamp(src[end_idx])
            src_completed = _parse_sql_timestamp(src[completed_idx])
            src_created = _parse_sql_timestamp(src[created_idx])
            src_updated = _parse_sql_timestamp(src[updated_idx])

            new_cycle = dt.datetime.combine(
                target_day,
                src_cycle.timetz(),
                tzinfo=src_cycle.tzinfo or dt.timezone.utc,
            )
            delta_end = src_end - src_cycle
            delta_completed = src_completed - src_cycle
            delta_created = src_created - src_cycle
            delta_updated = src_updated - src_cycle

            new_row[cycle_idx] = _to_sql_timestamp(new_cycle)
            new_row[end_idx] = _to_sql_timestamp(new_cycle + delta_end)
            new_row[completed_idx] = _to_sql_timestamp(new_cycle + delta_completed)
            new_row[created_idx] = _to_sql_timestamp(new_cycle + delta_created)
            new_row[updated_idx] = _to_sql_timestamp(new_cycle + delta_updated)
            new_row[id_idx] = _sql_quote(str(uuid.uuid4()))

            max_treatment_by_patient[patient] = max_treatment_by_patient.get(patient, 0) + 1
            new_row[treatment_idx] = str(max_treatment_by_patient[patient])

            start_key = new_cycle.astimezone(dt.timezone.utc).strftime("%H:%M:%S")
            expected_section = sections_by_time.get(start_key)
            if expected_section is not None:
                new_row[shift_idx] = str(expected_section)

            ward_name = new_row[ward_idx].strip("'")
            allowed_times = unit_schedule_times.get(ward_name)
            if allowed_times is not None and start_key not in allowed_times:
                continue

            section_id = int(new_row[shift_idx])
            if valid_patient_section_pairs and (patient, section_id) not in valid_patient_section_pairs:
                continue

            generated.append(new_row)

    return generated


def _write_sql(output_path: Path, columns: list[str], rows: list[list[str]]) -> None:
    """เขียน rows เป็นไฟล์ SQL INSERT เดี่ยว."""
    if not rows:
        output_path.write_text("-- No incremental rows generated.\n", encoding="utf-8")
        return

    header = (
        'INSERT INTO local."HemodialysisRecords"(\n'
        + "\t"
        + ", ".join(f'"{c}"' for c in columns)
        + "\n)\nVALUES\n"
    )
    values = ",\n".join("(" + ",".join(r) + ")" for r in rows) + ";\n"
    output_path.write_text(header + values, encoding="utf-8")


def _tuples_to_values_sql(rows: list[list[str]]) -> str:
    """แปลง list rows เป็นข้อความ tuples สำหรับแทรกต่อท้าย VALUES."""
    return ",\n".join("(" + ",".join(r) + ")" for r in rows)


def _merge_rows_into_base_file(input_path: Path, rows: list[list[str]]) -> None:
    """
    merge rows ใหม่เข้าไฟล์ B03 เดิม
    - ไม่ทับ comment/header
    - แทรก tuple ใหม่ท้าย VALUES ก่อน ';'
    """
    if not rows:
        return

    original = input_path.read_text(encoding="utf-8")
    insert_match = re.search(
        r'(INSERT\s+INTO\s+local\."HemodialysisRecords"\s*\(.*?\)\s*VALUES\s*)(.*?)(;\s*)$',
        original,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not insert_match:
        raise ValueError("ไม่พบบล็อก INSERT ของ HemodialysisRecords สำหรับ merge")

    prefix = insert_match.group(1)
    old_values = insert_match.group(2).strip()
    suffix = insert_match.group(3)
    merged_values = old_values + ",\n" + _tuples_to_values_sql(rows)
    new_insert = prefix + merged_values + suffix

    start, end = insert_match.span()
    merged_text = original[:start] + new_insert + original[end:]
    input_path.write_text(merged_text, encoding="utf-8")


def main() -> None:
    """entrypoint: parse args -> generate -> export -> merge/cleanup."""
    parser = argparse.ArgumentParser(
        description="Generate incremental B03-HemodialysisRecords rows (UTC, skip weekends)."
    )
    parser.add_argument(
        "--input",
        default="seeds/b_sessions/B03-HemodialysisRecords.sql",
        help="ไฟล์ seed หลักของ B03",
    )
    parser.add_argument(
        "--sections",
        default="seeds/a_core/08-Sections.sql",
        help="ไฟล์ sections สำหรับ map เวลา -> ShiftSectionId",
    )
    parser.add_argument(
        "--slot",
        default="seeds/a_core/11-SectionSlotPatient.sql",
        help="ไฟล์ section slot patient สำหรับ validate pattern",
    )
    parser.add_argument(
        "--schedule",
        default="seeds/a_core/09-ScheduleMeta.sql",
        help="ไฟล์ ScheduleMeta สำหรับตรวจ time slot ของ unit",
    )
    parser.add_argument(
        "--shift-meta",
        default="seeds/a_core/10-ShiftMeta.sql",
        help="ไฟล์ ShiftMeta สำหรับตรวจเดือนที่เปิดตาราง",
    )
    parser.add_argument(
        "--output",
        default="seeds/b_sessions/B03-HemodialysisRecords.incremental.sql",
        help="ไฟล์ incremental ชั่วคราว",
    )
    parser.add_argument("--to-date", default="today", help="วันที่ปลายทางแบบ YYYY-MM-DD หรือ today")
    parser.add_argument(
        "--today-tz",
        default="Asia/Bangkok",
        help=(
            "timezone ที่ใช้คำนวณเมื่อ --to-date=today "
            "(เช่น Asia/Bangkok, UTC; default: Asia/Bangkok)"
        ),
    )
    parser.add_argument(
        "--merge-into-base",
        action="store_true",
        default=True,
        help="merge แถวใหม่กลับเข้าไฟล์ --input (default: true)",
    )
    parser.add_argument(
        "--no-merge-into-base",
        dest="merge_into_base",
        action="store_false",
        help="ไม่ merge เข้าไฟล์ --input (generate incremental อย่างเดียว)",
    )
    parser.add_argument(
        "--keep-incremental-file",
        action="store_true",
        help="เก็บไฟล์ incremental ไว้ (default: ลบเมื่อ merge สำเร็จ)",
    )
    parser.add_argument(
        "--mode",
        choices=("gap-fill", "tail"),
        default="gap-fill",
        help="gap-fill=เติมช่องว่างตาม slot (default); tail=เติมแค่หลังวันล่าสุดแบบเดิม",
    )
    parser.add_argument(
        "--max-internal-gap-days",
        type=int,
        default=90,
        help=(
            "gap-fill: เติมช่องว่างระหว่างสองวันที่มีข้อมูลของคู่ (patient,section) "
            "ได้เฉพาะเมื่อห่างกันไม่เกิน N วันปฏิทิน; 0 = ไม่จำกัด (อันตรายถ้า seed เว้นช่วงยาว)"
        ),
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    # เตรียม path ที่ใช้อ่าน/เขียน (relative กับ repo root)
    def _resolve(p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else (_REPO_ROOT / path)

    input_path = _resolve(args.input)
    sections_path = _resolve(args.sections)
    slot_path = _resolve(args.slot)
    schedule_path = _resolve(args.schedule)
    shift_meta_path = _resolve(args.shift_meta)
    output_path = _resolve(args.output)

    # Parse ข้อมูลจาก B03 เดิม
    sql_text = input_path.read_text(encoding="utf-8")
    columns, values_block = _extract_insert_columns_and_values(sql_text)
    tuple_bodies = _split_tuples(values_block)
    rows = [_split_fields(t) for t in tuple_bodies]

    # index คอลัมน์ที่ใช้กับ logic generate
    required_columns = [
        "Id",
        "PatientId",
        "Ward",
        "Created",
        "Updated",
        "CompletedTime",
        "CycleStartTime",
        "CycleEndTime",
        "ShiftSectionId",
        "TreatmentNo",
    ]
    col_idx = {name: columns.index(name) for name in required_columns}

    # ปลายทางวันสุดท้ายของการ generate (UTC)
    if args.to_date == "today":
        try:
            to_date = _resolve_today_date(args.today_tz)
        except Exception as exc:
            parser.error(f"--today-tz ไม่ถูกต้อง: {args.today_tz!r} ({exc})")
    else:
        to_date = dt.date.fromisoformat(args.to_date)

    sections_by_time = _load_sections_time_map(sections_path)
    section_start_by_id = _load_section_start_time_by_id(sections_path)
    valid_pairs = _load_section_slot_pairs(slot_path)
    unit_schedule_times = _load_schedule_meta(schedule_path)
    shift_meta_months = _load_shift_meta_months(shift_meta_path)

    check_month = to_date.replace(day=1)
    if shift_meta_months and check_month not in shift_meta_months:
        print(
            f"Warning: month {check_month.isoformat()} not found in ShiftMeta; "
            "script will still generate rows."
        )

    gap_stats: dict[str, int] | None = None
    if args.mode == "gap-fill":
        generated_rows, gap_stats = _build_gap_fill_rows(
            rows=rows,
            col_idx=col_idx,
            to_date=to_date,
            sections_by_time=sections_by_time,
            slot_pairs=valid_pairs,
            unit_schedule_times=unit_schedule_times,
            section_start_by_id=section_start_by_id,
            max_internal_gap_days=args.max_internal_gap_days,
        )
        lim = "ไม่จำกัด" if args.max_internal_gap_days <= 0 else f"<={args.max_internal_gap_days} วัน"
        print(f"Gap-fill (UTC): ช่องว่างระหว่าง anchor {lim}, หางถึง {to_date.isoformat()}")
    else:
        generated_rows = _build_tail_rows(
            rows=rows,
            col_idx=col_idx,
            to_date=to_date,
            sections_by_time=sections_by_time,
            valid_patient_section_pairs=valid_pairs,
            unit_schedule_times=unit_schedule_times,
        )

    print(f"Generated rows: {len(generated_rows)}")
    if gap_stats is not None and generated_rows:
        print(
            "สรุป (gap-fill นับต่อคู่ PatientId+ShiftSectionId ตาม slot ไม่ใช่แค่วันล่าสุดของทั้งไฟล์): "
            f"คู่ที่วันล่าสุดของคู่นั้นยังก่อน to-date = {gap_stats['pairs_tail_lag']}, "
            f"วันทำการหายระหว่าง anchor (ปฏิทิน) = {gap_stats['calendar_internal_missing']}, "
            f"วันทำการหายในหางถึง to-date (ปฏิทิน) = {gap_stats['calendar_tail_missing']} "
            "(จำนวนแถวจริงอาจน้อยกว่าถ้า ScheduleMeta/Sections กรองไม่ผ่าน)"
        )
    if not generated_rows:
        print("No new business-day gaps to fill.")
        return

    # export incremental เพื่อใช้ตรวจสอบย้อนหลัง/ดีบัก
    _write_sql(output_path, columns, generated_rows)
    print(f"Incremental output: {output_path}")

    # default workflow: merge กลับเข้า B03 เดิม เพื่อให้ bat เดิมใช้ได้ทันที
    if args.merge_into_base:
        _merge_rows_into_base_file(input_path=input_path, rows=generated_rows)
        print(f"Merged into base: {input_path}")

        # ถ้าไม่ต้องการเก็บไฟล์ incremental ก็ลบทิ้งเพื่อให้เหลือ B03 ไฟล์เดียว
        if not args.keep_incremental_file and output_path.exists():
            output_path.unlink()
            print(f"Removed incremental file: {output_path}")


if __name__ == "__main__":
    main()

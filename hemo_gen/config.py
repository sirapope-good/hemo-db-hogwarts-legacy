from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

CREATED_BY = "866dabc4-6501-44d2-a0e5-65da9c45a46e"
START_DATE = dt.date(2025, 8, 1)
TODAY_TZ = "Asia/Bangkok"
WARD = "Hogwarts"
MACHINE_MODEL = "Nikkiso DBB-05/07"

# SectionId -> UTC hour:minute (from 08-Sections Hogwarts unit -1)
SECTION_UTC_TIMES: dict[int, tuple[int, int]] = {
    1: (5, 0),
    2: (9, 0),
    3: (13, 0),
    4: (17, 0),
}

DURATION_HOURS = 4
CYCLE_END_OFFSET_MIN = 30
COMPLETED_OFFSET_MIN = 37

B01_FILE = "B01-AvShunts.sql"
B02_FILE = "B02-DialysisPrescriptions.sql"
B03_FILE = "B03-HemodialysisRecords.sql"
B04_FILE = "B04-DialysisRecords.sql"
B05_FILE = "B05-Assessment.sql"
B06_FILE = "B06-ExecutionRecords.sql"
B07_FILE = "B07-MedicinePrescriptions.sql"

STATE_FILE = ".hemo_gen_state.json"

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class GenConfig:
    base_dir: Path
    patient_id: str
    start_date: dt.date
    end_date: dt.date
    seed: int
    dry_run: bool
    force_b01: bool


def resolve_timezone(name: str) -> dt.tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Bangkok":
            return dt.timezone(dt.timedelta(hours=7))
        raise


def resolve_end_date(span: str, start: dt.date, tz_name: str) -> dt.date:
    if span == "today":
        tz = resolve_timezone(tz_name)
        return dt.datetime.now(tz).date()
    if span.endswith("m"):
        months = int(span[:-1])
        month = start.month - 1 + months
        year = start.year + month // 12
        month = month % 12 + 1
        day = min(start.day, 28)
        return dt.date(year, month, day)
    raise ValueError(f"ไม่รองรับ span: {span}")


def first_business_on_or_after(d: dt.date) -> dt.date:
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d

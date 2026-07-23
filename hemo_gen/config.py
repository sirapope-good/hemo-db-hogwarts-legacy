from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

CREATED_BY = "866dabc4-6501-44d2-a0e5-65da9c45a46e"
START_DATE = dt.date(2025, 8, 1)
TODAY_TZ = "Asia/Bangkok"
WARD = "Hogwarts Hospital Wing"
WARD_BY_UNIT: dict[int, str] = {
    -1: "Hogwarts Hospital Wing",
    1: "Azkaban Ward",
}
MACHINE_MODEL = "Nikkiso DBB-05/07"

# SectionId -> UTC hour:minute (08-Sections: 1-4 Hogwarts, 5-7 Azkaban)
SECTION_UTC_TIMES: dict[int, tuple[int, int]] = {
    1: (5, 0),
    2: (9, 0),
    3: (13, 0),
    4: (17, 0),
    5: (12, 0),
    6: (16, 0),
    7: (20, 0),
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

PATIENTS_FILE = "05-Patients.sql"
SLOT_FILE = "11-SectionSlotPatient.sql"

STATE_FILE = ".hemo_gen_state.json"

DATA_DIR = Path(__file__).resolve().parent / "data"


def repo_root() -> Path:
    """Repo root (parent of hemo_gen/)."""
    return Path(__file__).resolve().parent.parent


def a_core_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "seeds" / "a_core"


def b_sessions_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "seeds" / "b_sessions"


def c_stock_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "seeds" / "c_stock"


def state_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / STATE_FILE


def a_file(name: str, root: Path | None = None) -> Path:
    return a_core_dir(root) / name


def b_file(name: str, root: Path | None = None) -> Path:
    return b_sessions_dir(root) / name


@dataclass(frozen=True)
class GenConfig:
    base_dir: Path  # repo root
    patient_id: str
    start_date: dt.date
    end_date: dt.date
    seed: int
    dry_run: bool
    force_b01: bool
    force_meds: bool = False


def resolve_timezone(name: str) -> dt.tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name == "Asia/Bangkok":
            return dt.timezone(dt.timedelta(hours=7))
        raise


def clinic_today(tz_name: str = TODAY_TZ) -> dt.date:
    """Calendar 'today' in clinic timezone (default Asia/Bangkok)."""
    return dt.datetime.now(resolve_timezone(tz_name)).date()


def playable_end_date(tz_name: str = TODAY_TZ) -> dt.date:
    """
    Last date we may generate session data for.

    Stops at yesterday so *today* stays empty for manual / UI play.
    """
    return clinic_today(tz_name) - dt.timedelta(days=1)


def resolve_end_date(span: str, start: dt.date, tz_name: str) -> dt.date:
    if span == "today":
        # Through yesterday only — leave today free for the user.
        return playable_end_date(tz_name)
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

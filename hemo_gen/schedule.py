from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass

from hemo_gen.config import SECTION_UTC_TIMES, first_business_on_or_after
from hemo_gen.profiles import PatientProfile


@dataclass(frozen=True)
class SessionSlot:
    session_date: dt.date
    section_id: int
    cycle_start: dt.datetime


def iter_business_days(start: dt.date, end: dt.date):
    current = start
    while current <= end:
        if current.weekday() < 5:
            yield current
        current += dt.timedelta(days=1)


def pick_session_days(profile: PatientProfile, start: dt.date, end: dt.date, rng: random.Random) -> list[dt.date]:
    """เลือกวันฟอก ~1–2 ครั้ง/สัปดาห์ ตาม slot ของผู้ป่วย."""
    sessions_per_week = 1 if rng.random() < 0.45 else 2
    allowed_weekdays = set(profile.slot_weekdays)
    candidates = [d for d in iter_business_days(start, end) if d.weekday() in allowed_weekdays]
    if not candidates:
        candidates = list(iter_business_days(start, end))

    chosen: list[dt.date] = []
    week_start = None
    picks_this_week = 0
    for d in candidates:
        iso = d.isocalendar()
        wk = (iso.year, iso.week)
        if week_start != wk:
            week_start = wk
            picks_this_week = 0
        if picks_this_week >= sessions_per_week:
            continue
        if rng.random() < (0.55 if sessions_per_week == 2 else 0.85):
            chosen.append(d)
            picks_this_week += 1
    return sorted(set(chosen))


def session_datetime(session_date: dt.date, section_id: int) -> dt.datetime:
    h, m = SECTION_UTC_TIMES.get(section_id, (5, 0))
    return dt.datetime.combine(session_date, dt.time(h, m), tzinfo=dt.timezone.utc)


def build_session_slots(profile: PatientProfile, start: dt.date, end: dt.date, rng: random.Random) -> list[SessionSlot]:
    start = first_business_on_or_after(start)
    days = pick_session_days(profile, start, end, rng)
    return [
        SessionSlot(
            session_date=d,
            section_id=profile.section_id,
            cycle_start=session_datetime(d, profile.section_id),
        )
        for d in days
    ]

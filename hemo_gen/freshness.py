"""Freshness of generated B-group sessions vs playable end (yesterday)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from hemo_gen.config import B03_FILE, PATIENTS_FILE, TODAY_TZ, a_file, b_file, playable_end_date, state_path
from hemo_gen.patient_loader import load_patients
from hemo_gen.sql_io import iter_insert_blocks, split_fields, split_tuples
from hemo_gen.state import GenState


@dataclass(frozen=True)
class PatientFreshness:
    patient_id: str
    name: str
    last_session_date: dt.date | None
    days_behind: int | None  # None = no data yet


@dataclass(frozen=True)
class FreshnessReport:
    playable_end: dt.date
    clinic_today: dt.date
    patients: list[PatientFreshness]

    @property
    def latest_any(self) -> dt.date | None:
        dates = [p.last_session_date for p in self.patients if p.last_session_date]
        return max(dates) if dates else None

    @property
    def max_days_behind(self) -> int | None:
        lags = [p.days_behind for p in self.patients if p.days_behind is not None]
        if not lags:
            # no data at all → treat as behind from start? report None
            return None
        return max(lags)

    @property
    def lagging(self) -> list[PatientFreshness]:
        """Patients with no sessions yet, or last session before playable end."""
        return [p for p in self.patients if (p.days_behind or 0) > 0 or p.last_session_date is None]

    @property
    def needs_extend(self) -> bool:
        # True if any patient is missing data or behind — not only when the
        # global latest date is behind (new patients would otherwise be skipped).
        return bool(self.lagging)

def _b03_last_dates(b03_path: Path) -> dict[str, dt.date]:
    out: dict[str, dt.date] = {}
    if not b03_path.exists():
        return out
    text = b03_path.read_text(encoding="utf-8")
    for columns, values in iter_insert_blocks(text, "HemodialysisRecords"):
        if "PatientId" not in columns or "CycleStartTime" not in columns:
            continue
        p_idx = columns.index("PatientId")
        c_idx = columns.index("CycleStartTime")
        for body in split_tuples(values):
            fields = split_fields(body)
            if len(fields) <= max(p_idx, c_idx):
                continue
            pid = fields[p_idx].strip("'")
            raw = fields[c_idx].strip("'")
            try:
                if raw.endswith("+00"):
                    d = dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S+00").date()
                else:
                    d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
            except ValueError:
                continue
            prev = out.get(pid)
            if prev is None or d > prev:
                out[pid] = d
    return out


def collect_freshness(root: Path | None = None, tz_name: str = TODAY_TZ) -> FreshnessReport:
    from hemo_gen.config import clinic_today, repo_root

    root = root or repo_root()
    playable = playable_end_date(tz_name)
    today = clinic_today(tz_name)
    state = GenState.load(state_path(root))
    b03_dates = _b03_last_dates(b_file(B03_FILE, root))
    patients = load_patients(a_file(PATIENTS_FILE, root))

    rows: list[PatientFreshness] = []
    for p in patients:
        last: dt.date | None = None
        ps = state.patients.get(p.patient_id)
        if ps and ps.last_session_date:
            last = dt.date.fromisoformat(ps.last_session_date)
        b03_last = b03_dates.get(p.patient_id)
        if b03_last and (last is None or b03_last > last):
            last = b03_last
        if last is None:
            days = None
        else:
            days = max(0, (playable - last).days)
        rows.append(
            PatientFreshness(
                patient_id=p.patient_id,
                name=p.name,
                last_session_date=last,
                days_behind=days,
            )
        )
    return FreshnessReport(playable_end=playable, clinic_today=today, patients=rows)

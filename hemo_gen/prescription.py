from __future__ import annotations

import datetime as dt
import random
import uuid
from dataclasses import dataclass

from hemo_gen.config import CREATED_BY
from hemo_gen.profiles import PatientProfile
from hemo_gen.sql_io import sql_bool, sql_nullable_str, sql_quote, to_sql_timestamp


@dataclass
class DialysisPrescriptionRow:
    id: str
    administered_date: dt.datetime
    fields: list[str]


B02_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "PatientId", "Temporary",
    "Mode", "HdfType", "SubstituteVolume", "IvSupplementVolume", "IvSupplementPosition",
    "DryWeight", "ExcessFluidRemovalAmount", "BloodFlow", "BloodTransfusion", "ExtraFluid",
    "Duration", "Frequency", "AdministeredDate", "Anticoagulant", "AcPerSession",
    "InitialAmount", "MaintainAmount", "ReasonForRefraining", "AcPerSessionMl",
    "InitialAmountMl", "MaintainAmountMl", "DialysateK", "DialysateCa", "HCO3", "Na",
    "DialysateTemperature", "DialysateFlowRate", "BloodAccessRoute", "DialyzerId", "Dialyzer",
    "DialyzerSurfaceArea", "AvgDialyzerReuse", "DialysisNurse", "Note",
]


class DialysisPrescriptionManager:
    def __init__(self, profile: PatientProfile, rng: random.Random) -> None:
        self.profile = profile
        self.rng = rng
        self._current = self._make_initial()
        self.sessions_on_rx = 0
        self.max_sessions = rng.choice([3, 4])

    def _make_initial(self) -> DialysisPrescriptionRow:
        p = self.profile
        rx_id = str(uuid.uuid4())
        return DialysisPrescriptionRow(
            id=rx_id,
            administered_date=dt.datetime.now(dt.timezone.utc),
            fields=self._fields_from_profile(p, rx_id, p.dry_weight, p.blood_flow, p.dialysate_flow, p.hco3, p.na),
        )

    def _fields_from_profile(
        self,
        p: PatientProfile,
        rx_id: str,
        dry: float,
        bfr: int,
        dfr: int,
        hco3: int,
        na: int,
    ) -> list[str]:
        now = dt.datetime.now(dt.timezone.utc)
        ts = to_sql_timestamp(now)
        return [
            sql_quote(rx_id),
            ts,
            sql_quote(CREATED_BY),
            ts,
            sql_quote(CREATED_BY),
            sql_bool(True),
            sql_quote(p.patient.patient_id),
            sql_bool(False),
            "0",
            "NULL",
            "NULL",
            "NULL",
            "NULL",
            str(int(dry)),
            "NULL",
            str(bfr),
            "480",
            "300",
            sql_quote("05:20:00"),
            "1",
            to_sql_timestamp(now),
            sql_quote(p.anticoagulant),
            str(p.ac_per_session),
            str(p.initial_amount),
            str(p.maintain_amount),
            "NULL",
            "NULL",
            "NULL",
            "NULL",
            "2",
            "2",
            str(hco3),
            str(na),
            str(p.dialysate_temp),
            str(dfr),
            sql_quote(p.blood_access),
            str(p.dialyzer_id),
            sql_quote(p.dialyzer_name),
            str(p.dialyzer_surface),
            "NULL",
            "NULL",
            sql_quote(f"Hogwarts gen {p.patient.patient_id}"),
        ]

    def maybe_rotate(self, administered: dt.datetime) -> DialysisPrescriptionRow | None:
        if self.sessions_on_rx < self.max_sessions:
            return None
        p = self.profile
        dry = float(self._current.fields[B02_COLUMNS.index("DryWeight")]) - self.rng.uniform(0.3, 1.2)
        bfr = int(self._current.fields[B02_COLUMNS.index("BloodFlow")]) + self.rng.choice([-20, -10, 10, 20])
        dfr = int(self._current.fields[B02_COLUMNS.index("DialysateFlowRate")]) + self.rng.choice([-10, 0, 10])
        hco3 = int(self._current.fields[B02_COLUMNS.index("HCO3")])
        na = int(self._current.fields[B02_COLUMNS.index("Na")])
        rx_id = str(uuid.uuid4())
        row = DialysisPrescriptionRow(
            id=rx_id,
            administered_date=administered,
            fields=self._fields_from_profile(p, rx_id, dry, bfr, dfr, hco3, na),
        )
        row.fields[B02_COLUMNS.index("AdministeredDate")] = to_sql_timestamp(administered)
        self._current = row
        self.sessions_on_rx = 0
        self.max_sessions = self.rng.choice([3, 4])
        return row

    def active(self) -> DialysisPrescriptionRow:
        return self._current

    def on_session_completed(self) -> None:
        self.sessions_on_rx += 1

    def new_prescription_rows_for_session(
        self, administered: dt.datetime, is_first: bool
    ) -> list[list[str]]:
        if is_first:
            self._current.administered_date = administered
            self._current.fields[B02_COLUMNS.index("AdministeredDate")] = to_sql_timestamp(administered)
            return [self._current.fields]
        rotated = self.maybe_rotate(administered)
        if rotated:
            return [rotated.fields]
        return []

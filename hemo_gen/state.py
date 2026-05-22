from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatientState:
    last_treatment_no: int = 0
    last_session_date: str | None = None
    dialysis_prescription_count: int = 0
    sessions_on_current_rx: int = 0
    max_sessions_on_rx: int = 3
    medicine_prescription_ids: dict[str, str] = field(default_factory=dict)


@dataclass
class GenState:
    patients: dict[str, PatientState] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> GenState:
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        patients: dict[str, PatientState] = {}
        for pid, data in raw.get("patients", {}).items():
            patients[pid] = PatientState(
                last_treatment_no=data.get("last_treatment_no", 0),
                last_session_date=data.get("last_session_date"),
                dialysis_prescription_count=data.get("dialysis_prescription_count", 0),
                sessions_on_current_rx=data.get("sessions_on_current_rx", 0),
                max_sessions_on_rx=data.get("max_sessions_on_rx", 3),
                medicine_prescription_ids=data.get("medicine_prescription_ids", {}),
            )
        return cls(patients=patients)

    def save(self, path: Path) -> None:
        payload = {
            "patients": {
                pid: {
                    "last_treatment_no": ps.last_treatment_no,
                    "last_session_date": ps.last_session_date,
                    "dialysis_prescription_count": ps.dialysis_prescription_count,
                    "sessions_on_current_rx": ps.sessions_on_current_rx,
                    "max_sessions_on_rx": ps.max_sessions_on_rx,
                    "medicine_prescription_ids": ps.medicine_prescription_ids,
                }
                for pid, ps in self.patients.items()
            }
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def for_patient(self, patient_id: str) -> PatientState:
        if patient_id not in self.patients:
            self.patients[patient_id] = PatientState()
        return self.patients[patient_id]

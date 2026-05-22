from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatientInfo:
    patient_id: str
    name: str
    doctor_id: str | None


@dataclass(frozen=True)
class SlotAssignment:
    section_id: int
    slot: int  # 0=Mon .. 4=Fri


def load_patients(path: Path) -> list[PatientInfo]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\(\s*(\d+)\s*,\s*'[^']+'\s*,\s*TRUE\s*,\s*\d+\s*,\s*'[^']*'\s*,\s*'([^']+)'\s*,"
        r"[^,]*,[^,]*,[^,]*,(?:'([0-9a-f-]{36})'|NULL)\s*,",
        re.IGNORECASE,
    )
    # simpler line-based parse
    patients: list[PatientInfo] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("("):
            continue
        m = re.match(r"\(\s*([^,]+)\s*,", line)
        if not m:
            continue
        pid = m.group(1).strip()
        name_m = re.search(r",\s*'([^']+)'\s*,\s*'[MF]'\s*,", line)
        doc_m = re.search(r",\s*'([0-9a-f-]{36})'\s*,\s*-?\d+\s*\)", line)
        if name_m:
            patients.append(
                PatientInfo(
                    patient_id=pid,
                    name=name_m.group(1),
                    doctor_id=doc_m.group(1) if doc_m else None,
                )
            )
    return patients


def load_slot_assignments(path: Path, patient_id: str) -> list[SlotAssignment]:
    text = path.read_text(encoding="utf-8")
    out: list[SlotAssignment] = []
    for line in text.splitlines():
        if patient_id not in line:
            continue
        m = re.search(r"true,\s*(\d+)\s*,\s*'" + re.escape(patient_id) + r"'\s*,\s*(\d+)", line, re.I)
        if m:
            out.append(SlotAssignment(section_id=int(m.group(1)), slot=int(m.group(2))))
    return out


def load_section_times(path: Path) -> dict[int, tuple[int, int, int]]:
    """SectionId -> (hour, minute, second) UTC from StartTime."""
    text = path.read_text(encoding="utf-8")
    result: dict[int, tuple[int, int, int]] = {}
    for line in text.splitlines():
        m = re.search(r"\(\s*(\d+)\s*,.*?'(\d{2}):(\d{2}):(\d{2})'\s*\)", line)
        if m and int(m.group(1)) <= 4:
            result[int(m.group(1))] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return result

from __future__ import annotations

import random
from dataclasses import dataclass

from hemo_gen.config import CREATED_BY, SECTION_UTC_TIMES
from hemo_gen.patient_loader import PatientInfo, SlotAssignment


@dataclass
class AvShuntProfile:
    av_shunt_id: str
    catheter_type: int
    side: int
    shunt_site: str
    display_site: str
    ac: str
    a_fill: int | None
    v_fill: int | None
    a_catheter: int | None
    v_catheter: int | None
    a_needle: int | None
    v_needle: int | None
    blood_access_route: str


@dataclass
class PatientProfile:
    patient: PatientInfo
    section_id: int
    slot_weekdays: list[int]
    dry_weight: float
    blood_flow: int
    dialysate_flow: int
    hco3: int
    na: int
    dialysate_temp: float
    anticoagulant: str
    initial_amount: int
    maintain_amount: float
    ac_per_session: int
    dialyzer_name: str
    dialyzer_id: int
    dialyzer_surface: float
    blood_access: str
    av: AvShuntProfile
    bed_number: int


def _shunt_for_type(ct: int, side: int) -> tuple[str, str, str]:
    side_s = "Left" if side == 0 else "Right"
    if ct == 0:
        return "subclavian", f"AVF / {side_s} / SUB", f"LT AVF" if side == 0 else "RT AVF"
    if ct == 1:
        return "jugular", f"AVG / {side_s} / JUG", f"LT AVG" if side == 0 else "RT AVG"
    if ct == 2:
        return "subclavian", f"Perm Cath / {side_s} / SUB", "Perm Cath"
    return "jugular", f"Double Lumen / {side_s} / JUG", "Double Lumen"


def build_profile(patient: PatientInfo, slots: list[SlotAssignment], rng: random.Random) -> PatientProfile:
    if slots:
        primary = min(slots, key=lambda s: (s.section_id, s.slot))
        section_id = primary.section_id
        slot_days = sorted({s.slot for s in slots})
    else:
        section_id = 1
        slot_days = [0, 2]

    pid = abs(hash(patient.patient_id)) % 100000
    if patient.patient_id.isdigit():
        pid = int(patient.patient_id)
    ct = pid % 4
    side = pid % 2
    site, display, route = _shunt_for_type(ct, side)
    dry = 55.0 + (pid % 25) + rng.uniform(-0.5, 0.5)
    bfr = 240 + (pid % 8) * 10
    dialyzer_names = ["FDY-21", "F160", "FDX-21"]
    dialyzer = dialyzer_names[pid % len(dialyzer_names)]

    ac = "Heparin" if ct in (0, 1) else "Clexane"
    if ac == "Heparin":
        init_amt, maint, ac_sess = 1000 + (pid % 5) * 100, 500.0 + (pid % 3) * 100, 1500 + (pid % 4) * 100
        a_n, v_n = 15 + (pid % 3), 15 + (pid % 3)
        a_f, v_f = None, None
        a_c, v_c = None, None
    else:
        init_amt, maint, ac_sess = 28 + (pid % 5), 95.0 + (pid % 3), 300 + (pid % 4) * 10
        a_n, v_n = 16, 16
        a_f, v_f = 20 + (pid % 10), 20 + (pid % 8)
        a_c, v_c = 22 + (pid % 8), 22 + (pid % 8)

    import uuid

    av_id = str(uuid.uuid4())
    return PatientProfile(
        patient=patient,
        section_id=section_id if section_id in SECTION_UTC_TIMES else 1,
        slot_weekdays=slot_days if slot_days else [0, 2],
        dry_weight=round(dry, 1),
        blood_flow=bfr,
        dialysate_flow=500 + (pid % 4) * 10,
        hco3=30 + (pid % 4),
        na=138 + (pid % 4),
        dialysate_temp=35.0 + (pid % 3) * 0.5,
        anticoagulant=ac,
        initial_amount=init_amt,
        maintain_amount=maint,
        ac_per_session=ac_sess,
        dialyzer_name=dialyzer,
        dialyzer_id=-2,
        dialyzer_surface=2.1,
        blood_access=route,
        av=AvShuntProfile(
            av_shunt_id=av_id,
            catheter_type=ct,
            side=side,
            shunt_site=site,
            display_site=display,
            ac=ac,
            a_fill=a_f,
            v_fill=v_f,
            a_catheter=a_c,
            v_catheter=v_c,
            a_needle=a_n,
            v_needle=v_n,
            blood_access_route=route,
        ),
        bed_number=1 + (pid % 15),
    )

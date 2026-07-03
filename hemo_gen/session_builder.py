from __future__ import annotations

import datetime as dt
import random
import uuid
from dataclasses import dataclass

from hemo_gen.config import (
    COMPLETED_OFFSET_MIN,
    CYCLE_END_OFFSET_MIN,
    DURATION_HOURS,
    MACHINE_MODEL,
    WARD,
    CREATED_BY,
)
from hemo_gen.prescription import DialysisPrescriptionRow
from hemo_gen.profiles import PatientProfile
from hemo_gen.schedule import SessionSlot
from hemo_gen.sql_io import sql_bool, sql_nullable_str, sql_quote, sql_uuid_array, to_sql_timestamp


B03_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "PatientId", "CompletedTime",
    "Admission", "OutsideUnit", "Ward", "Bed", "CycleStartTime", "CycleEndTime", "IsICU", "Type",
    "AcNotUsed", "ReasonForRefraining", "FlushNSS", "FlushNSSInterval", "FlushTimes",
    "Dehydration_LastPostWeight", "Dehydration_CheckInTime", "Dehydration_PreTotalWeight",
    "Dehydration_WheelchairWeight", "Dehydration_ClothWeight", "Dehydration_FoodDrinkWeight",
    "Dehydration_BloodTransfusion", "Dehydration_ExtraFluid", "Dehydration_UFGoal",
    "Dehydration_PostTotalWeight", "Dehydration_PostWheelchairWeight", "Dehydration_Abnormal",
    "Dehydration_Reason", "DialysisPrescriptionId", "Dialyzer_DialyzerId", "Dialyzer_DialyzerName",
    "Dialyzer_UseNo", "Dialyzer_TCV", "Dialyzer_Grade", "BloodCollection_Pre", "BloodCollection_Post",
    "AvShunt_AVShuntId", "AvShunt_ShuntSite", "AvShunt_Ac", "AvShunt_AFillVolume",
    "AvShunt_VFillVolume", "AvShunt_ACatheterVolume", "AvShunt_VCatheterVolume",
    "AvShunt_ANeedleSize", "AvShunt_VNeedleSize", "AvShunt_ANeedleTimes", "AvShunt_VNeedleTimes",
    "DoctorConsent", "ShiftSectionId", "NursesInShift", "StaffAllocation", "TreatmentNo",
    "DoctorId", "AutoStockId", "SentPDF",
]


@dataclass
class BuiltSession:
    hemo_id: str
    b03_fields: list[str]
    cycle_start: dt.datetime
    cycle_end: dt.datetime
    completed: dt.datetime
    uf_goal: float
    pre_weight: float
    post_weight: float
    dry_weight: float
    pre_bps: int = 0
    pre_bpd: int = 0
    pre_hr: int = 0


def _nurse_uuids(rng: random.Random, count: int = 4) -> list[str]:
    pool = [
        "6e535885-692f-4f0c-b605-0d537154f835",
        "69c8793e-81ee-483a-ad47-ef1d3fa6337f",
        "367be69f-584a-49e4-a0b6-cab3635a9083",
        "0322c1c8-5b34-4199-a0e2-81d08ab67a82",
        "638a7f0d-fe84-4256-b714-63071d9ce516",
        "de87de9b-5cac-4a3b-88f0-592f702048a5",
    ]
    rng.shuffle(pool)
    return pool[:count]


def build_b01_row(profile: PatientProfile, established: dt.datetime) -> list[str]:
    av = profile.av
    ts = to_sql_timestamp(established)
    def n(v):
        return "NULL" if v is None else str(v)

    return [
        sql_quote(av.av_shunt_id),
        ts,
        sql_quote(CREATED_BY),
        ts,
        sql_quote(CREATED_BY),
        sql_bool(True),
        sql_quote(profile.patient.patient_id),
        to_sql_timestamp(established),
        "NULL",
        str(av.catheter_type),
        str(av.side),
        sql_quote(av.shunt_site),
        sql_quote("Hogwarts Infirmary"),
        sql_quote("hemo_gen B01"),
        sql_quote(""),
        sql_quote(av.ac),
        n(av.a_fill),
        n(av.v_fill),
        n(av.a_catheter),
        n(av.v_catheter),
        n(av.a_needle),
        n(av.v_needle),
    ]


B01_COLUMNS = [
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive",
    "PatientId", "EstablishedDate", "EndDate",
    "CatheterType", "Side", "ShuntSite", "CatheterizationInstitution", "Note", "ReasonForDiscontinuation",
    "Ac", "AFillVolume", "VFillVolume", "ACatheterVolume", "VCatheterVolume", "ANeedleSize", "VNeedleSize",
]


def build_session(
    slot: SessionSlot,
    profile: PatientProfile,
    rx: DialysisPrescriptionRow,
    treatment_no: int,
    last_post_weight: float | None,
    rng: random.Random,
) -> BuiltSession:
    hemo_id = str(uuid.uuid4())
    cycle_start = slot.cycle_start
    cycle_end = cycle_start + dt.timedelta(hours=4)
    completed = cycle_end + dt.timedelta(minutes=COMPLETED_OFFSET_MIN)
    check_in = cycle_start - dt.timedelta(minutes=rng.randint(15, 45))

    from hemo_gen.prescription import B02_COLUMNS

    dry = float(rx.fields[B02_COLUMNS.index("DryWeight")])
    if last_post_weight is None:
        last_post_weight = dry + rng.uniform(0.5, 2.0)
    uf = round(max(1.5, rng.uniform(1.8, 3.5)), 1)
    pre = round(dry + uf + rng.uniform(-0.3, 0.5), 1)
    post = round(pre - uf - rng.uniform(0, 0.2), 1)
    pre_bps = 155 + rng.randint(5, 25)
    pre_bpd = 75 + rng.randint(0, 10)
    pre_hr = 75 + rng.randint(0, 10)

    created = check_in - dt.timedelta(minutes=5)
    nurses = _nurse_uuids(rng)
    bed = f"{profile.bed_number} ({MACHINE_MODEL.split('/')[0]})"

    fields = [
        sql_quote(hemo_id),
        to_sql_timestamp(created),
        sql_quote(CREATED_BY),
        to_sql_timestamp(completed),
        sql_quote(CREATED_BY),
        sql_bool(True),
        sql_quote(profile.patient.patient_id),
        to_sql_timestamp(completed),
        "0",
        sql_bool(False),
        sql_quote(WARD),
        sql_nullable_str(bed),
        to_sql_timestamp(cycle_start),
        to_sql_timestamp(cycle_end),
        sql_bool(False),
        "0",
        sql_bool(False),
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        str(round(last_post_weight, 1)),
        to_sql_timestamp(check_in),
        str(pre),
        "0",
        "0",
        "0",
        "NULL",
        "NULL",
        str(uf),
        str(post),
        "0",
        sql_bool(False),
        "NULL",
        sql_quote(rx.id),
        str(profile.dialyzer_id),
        sql_quote(profile.dialyzer_name),
        str(1 + (treatment_no % 15)),
        "0",
        "0",
        "NULL",
        "NULL",
        sql_quote(profile.av.av_shunt_id),
        sql_quote(profile.av.display_site),
        sql_quote(profile.av.ac),
        "NULL" if profile.av.a_fill is None else str(profile.av.a_fill),
        "NULL" if profile.av.v_fill is None else str(profile.av.v_fill),
        "NULL" if profile.av.a_catheter is None else str(profile.av.a_catheter),
        "NULL" if profile.av.v_catheter is None else str(profile.av.v_catheter),
        "NULL" if profile.av.a_needle is None else str(profile.av.a_needle),
        "NULL" if profile.av.v_needle is None else str(profile.av.v_needle),
        "NULL",
        "NULL",
        sql_bool(False),
        str(slot.section_id),
        sql_uuid_array(nurses),
        sql_uuid_array([]),
        str(treatment_no),
        sql_nullable_str(profile.patient.doctor_id),
        "NULL",
        sql_bool(False),
    ]
    return BuiltSession(
        hemo_id=hemo_id,
        b03_fields=fields,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        completed=completed,
        uf_goal=uf,
        pre_weight=pre,
        post_weight=post,
        dry_weight=dry,
        pre_bps=pre_bps,
        pre_bpd=pre_bpd,
        pre_hr=pre_hr,
    )

# Patient Dialysis Generator (hemo_gen)

สคริปต์สร้างข้อมูลฟอกไต **ครบ 1 session** ต่อรอบ (B01–B07) ทีละ **1 ผู้ป่วย** ตาม [HEMO_COMPLETE_SESSION_SPEC.md](HEMO_COMPLETE_SESSION_SPEC.md)

ไม่แก้ `generate_b03_incremental.py` — ใช้ชุดใหม่นี้แทนเมื่อต้องการข้อมูลครบชุด

## ความต้องการ

- Python 3.10+
- Core seed + INIT แล้ว (`Medicines` Espogen `-234`, `Assessments` ฯลฯ)
- อ่าน schedule จาก `05-Patients.sql`, `08-Sections.sql`, `11-SectionSlotPatient.sql`

## คำสั่ง

```bash
# แสดงรายชื่อผู้ป่วย
python generate_patient_dialysis.py --list-patients

# สร้างข้อมูล (default span = วันนี้ ตาม Asia/Bangkok)
python generate_patient_dialysis.py --patient-id 6505315 --span today

# ช่วง 2 / 4 / 6 เดือนจาก 2025-08-01
python generate_patient_dialysis.py --patient-id 6455308 --span 4m

# สรุปจำนวนแถว ไม่เขียนไฟล์
python generate_patient_dialysis.py --patient-id 6505315 --span 2m --dry-run

# seed คงที่ (ถ้าไม่ระบุ ใช้ hash ของ patient-id)
python generate_patient_dialysis.py --patient-id 6505315 --seed 42

# แก้น้ำหนัก/UF goal ใน B03 seed (UFGoal=0)
python generate_patient_dialysis.py --patch-b03-weights

# เติม B04 ให้ hemosheet ใน B03 ที่ยังไม่มี DialysisRecord (รวม seed เดิม)
python generate_patient_dialysis.py --rebuild-b04
python generate_patient_dialysis.py --rebuild-b04 --patient-id 6505315

# สร้าง B04 ใหม่ทั้งไฟล์ (NSS, 50% Glucose, BP/HR ครบ)
python generate_patient_dialysis.py --rebuild-b04-all

# สร้าง Pre/Post vital + Assessment ครบทุกรอบใน B03
python generate_patient_dialysis.py --rebuild-b05

# สร้าง B05 ใหม่จาก B03 ทั้งไฟล์ (กรณี Pre/Post vitals หาย)
python generate_patient_dialysis.py --rebuild-b05
```

| พารามิเตอร์ | ค่า |
|-------------|-----|
| `--patient-id` | บังคับ (ยกเว้น `--list-patients` / `--rebuild-b05`) |
| `--span` | `2m` \| `4m` \| `6m` \| `today` (default) |
| `--start-date` | ตายตัว `2025-08-01` ใน v1 |
| `--dry-run` | พิมพ์สรุป ไม่เขียน SQL |
| `--force-b01` | เขียน AvShunt ซ้ำแม้มี patient แล้ว |
| `--rebuild-b05` | สร้าง `B05-Assessment.sql` ใหม่จาก `B03` |

## ไฟล์ที่สร้าง / append

| ลำดับ | ไฟล์ | ตาราง |
|-------|------|--------|
| 1 | `B01-AvShunts.sql` | AvShunts (ข้ามถ้ามี PatientId แล้ว) |
| 2 | `B02-DialysisPrescriptions.sql` | ใบสั่งฟอก — episode 3–4 session/ใบ |
| 3 | `B07-MedicinePrescriptions.sql` | Espogen ก่อน execution |
| 4 | `B03-HemodialysisRecords.sql` | HDR + NursesInShift |
| 5 | `B04-DialysisRecords.sql` | 8–9 แถว/รอบ, `IsFromMachine=false` |
| 6 | `B05-Assessment.sql` | Pre/Post vitals + AssessmentItems |
| 7 | `B06-ExecutionRecords.sql` | MedicineRecord อ้าง `PrescriptionId` จาก B07 |

State: `.hemo_gen_state.json` (TreatmentNo, ใบสั่งยา Espogen UUID ฯลฯ)

## รัน seed หลัง generate

```bat
run_bgroup_supplemental_seed.bat
```

ลำดับ: **B01 → B02 → B07 → B03 → B04 → B05 → B06**

## โครงสร้างโค้ด

```
generate_patient_dialysis.py
hemo_gen/
  cli.py, config.py, state.py, sql_io.py
  patient_loader.py, schedule.py, prescription.py
  medicine_prescription.py, session_builder.py
  dialysis_records.py, assessment.py, execution.py
  generator.py, profiles.py, rebuild_b05.py
  data/assessment_map.json, medicine_catalog.json
```

## หมายเหตุ

- รันทีละ 1 คน — คนถัดไปจะ **append** เป็น `INSERT` บล็อกใหม่ต่อท้ายไฟล์ (ไม่ merge เข้า VALUES เดิมของ seed — ป้องกัน syntax error)
- B06 ต้องมี B07 ก่อนเสมอ (`PrescriptionId` required)
- ถ้า assessment ใน DB ไม่ตรง INIT ให้ regenerate `hemo_gen/data/assessment_map.json` จาก `assessments.csv` ใน HemoDialysisPro repo

## แก้ปัญหา seed

| อาการ | วิธีแก้ |
|--------|---------|
| `syntax error at or near "Id"` ใน B01/B02/B03 | ไฟล์ seed ถูก merge ผิด — คืนจาก `290426_backup/` แล้วรัน generator ใหม่ |
| `duplicate key` B07 | รัน B07 ซ้ำใน DB แล้ว — ลบแถว `MedicinePrescriptions` ที่ซ้ำ หรือข้าม B07 ใน bat ถ้าโหลดแล้ว |
| FK B05/B06 ล้มเหลว | มักเพราะ B03 ยังไม่ผ่าน — แก้ B01–B04 ก่อน แล้วรัน B03 → B05 → B06 |
| Hemosheet ต้นๆมี DialysisRecord แต่รอบหลังไม่มี | B03 **seed** ไม่มี B04 — รัน `--rebuild-b04` หลัง B03 seed โหลดแล้ว |
| B05 ไม่มี Pre/Post vitals | `python generate_patient_dialysis.py --rebuild-b05` (หลัง B03 สำเร็จ) |

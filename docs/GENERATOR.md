# Patient Dialysis Generator (hemo_gen)

สร้างข้อมูลฟอกไต **ครบ 1 session** ต่อรอบ (B01–B07) ตาม [SESSION_SPEC.md](SESSION_SPEC.md)

Legacy B03-only: `scripts/legacy/generate_b03_incremental.py` — ใช้ `hemo_gen` เมื่อต้องการครบชุด

## ความต้องการ

- Python 3.10+
- Core seed + INIT แล้ว (`Medicines` Espogen `-234`, `Assessments` ฯลฯ)
- อ่าน schedule จาก `seeds/a_core/05-Patients.sql`, `08-Sections.sql`, `11-SectionSlotPatient.sql`
- เขียนผลลัพธ์ลง `seeds/b_sessions/`

## คำสั่ง

รันจาก **repo root** (หรือใช้ `scripts\generate_all.bat` ซึ่ง `cd` ไป root ให้)

```bash
python generate_patient_dialysis.py --list-patients
python generate_patient_dialysis.py --patient-id 6505315 --span today
python generate_patient_dialysis.py --generate-all --span today

scripts\generate_all.bat
scripts\generate_all.bat --span 4m
scripts\generate_all.bat --dry-run

python generate_patient_dialysis.py --generate-all --span today --skip-post-steps
python generate_patient_dialysis.py --patient-id 6455308 --span 4m
python generate_patient_dialysis.py --patient-id 6505315 --span 2m --dry-run
python generate_patient_dialysis.py --patient-id 6505315 --seed 42
python generate_patient_dialysis.py --patch-b03-weights
python generate_patient_dialysis.py --rebuild-b04
python generate_patient_dialysis.py --rebuild-b04-all
python generate_patient_dialysis.py --rebuild-b05
python generate_patient_dialysis.py --restore-b07 --patient-id 6505315
python generate_patient_dialysis.py --validate-b03
```

| พารามิเตอร์ | ค่า |
|-------------|-----|
| `--patient-id` | บังคับเมื่อ generate 1 คน (หรือใช้ `--generate-all`) |
| `--generate-all` | สร้าง B01–B07 ทุกคนใน `seeds/a_core/05-Patients.sql` |
| `--skip-post-steps` | กับ `--generate-all`: ข้าม patch B03 / rebuild B05 / B04-all |
| `--span` | `2m` \| `4m` \| `6m` \| `today` (default) |
| `--dry-run` | พิมพ์สรุป ไม่เขียน SQL |
| `--force-b01` | เขียน AvShunt ซ้ำแม้มี patient แล้ว |

## ไฟล์ที่สร้าง / append

ทั้งหมดอยู่ใต้ `seeds/b_sessions/`:

| ลำดับ | ไฟล์ | ตาราง |
|-------|------|--------|
| 1 | `B01-AvShunts.sql` | AvShunts |
| 2 | `B02-DialysisPrescriptions.sql` | DialysisPrescriptions |
| 3 | `B07-MedicinePrescriptions.sql` | MedicinePrescriptions |
| 4 | `B03-HemodialysisRecords.sql` | HemodialysisRecords |
| 5 | `B04-DialysisRecords.sql` | DialysisRecords |
| 6 | `B05-Assessment.sql` | Assessment + vitals |
| 7 | `B06-ExecutionRecords.sql` | ExecutionRecords |

State: `.hemo_gen_state.json` ที่ repo root

## รัน seed หลัง generate

```bat
scripts\seed_b.bat
```

ลำดับ: **B01 → B02 → B07 → B03 → B04 → B05 → B06**

## โครงสร้าง

```text
generate_patient_dialysis.py   # entry
hemo_gen/                      # package (paths via config.repo_root / a_file / b_file)
seeds/a_core/                  # inputs
seeds/b_sessions/              # outputs (tracked in git)
scripts/generate_all.bat
scripts/legacy/generate_b03_incremental.py
```

## แก้ปัญหา seed

| อาการ | วิธีแก้ |
|--------|---------|
| `syntax error at or near "Id"` ใน B01/B02/B03 | `git checkout seed-2026-07-23 -- seeds/b_sessions/` แล้ว regenerate ถ้าจำเป็น |
| `duplicate key` B07 | ลบแถวซ้ำใน DB หรือข้าม B07 ถ้าโหลดแล้ว |
| `null value in column "RegimenLineId"` (B07) | schema บังคับ `RegimenLineId` — regenerate / แก้ B07 |
| FK B06 → MedicinePrescriptions | แก้ B07 ให้ผ่านก่อน แล้ว B07 → B06 |
| FK B05/B06 ล้ม | แก้ B01–B04 ก่อน แล้ว B03 → B05 → B06 |
| ไม่มี `B07-MedicinePrescriptions.sql` | `--restore-b07` หรือลบ `medicine_prescription_ids` ใน state แล้ว generate ใหม่ |
| B05 ไม่มี Pre/Post vitals | `--rebuild-b05` หลัง B03 พร้อม |

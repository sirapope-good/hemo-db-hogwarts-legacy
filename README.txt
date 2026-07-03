================================================================================
README — Hogwarts SQL seed & Python generators
================================================================================

เอกสารหลัก (อัปเดตล่าสุด)
-------------------------
- README.txt              ไฟล์นี้ — ภาพรวม + คำสั่งที่ใช้บ่อย
- README_GENERATOR.md     รายละเอียด generate_patient_dialysis.py (hemo_gen)
- HEMO_COMPLETE_SESSION_SPEC.md   สเปกข้อมูล 1 session ครบชุด

================================================================================
A) ลำดับรัน seed เข้า DB (แนะนำ)
================================================================================

1) Core (ครั้งเดียว / หลัง reset DB):
    run_agroup_hogwarts_core_seed.bat
    → 00-Units, 01-Users, 05-Patients, 08-Sections, 09-ScheduleMeta,
      10-ShiftMeta, 11-SectionSlotPatient ฯลฯ

2) Generate SQL ชุด B (Python — ดูหัวข้อ B ด้านล่าง)

3) โหลด C group (Stock — อุปกรณ์และวัสดุสิ้นเปลือง):
    run_cgroup_stock_seed.bat
    → C01-Equipments.sql (Id 1–9)
    → C02-MedicalSupplies.sql (Id 1–13)
    → C03-AutoStock-Equipments.sql (ชุด AutoStock อุปกรณ์)
    → C04-AutoStock-MedicalSupplies.sql (ชุด AutoStock วัสดุ)

4) โหลด B group:
    run_bgroup_supplemental_seed.bat
    → B01 → B02 → B07 → B03 → B04 → B05 → B06

หมายเหตุ Shift menu (เพิ่มพนักงานลง shift):
- 09-ScheduleMeta.sql และ 10-ShiftMeta.sql มี setval() หลัง INSERT Id manual
  เพื่อไม่ให้ชน PK เมื่อ UI สร้าง ShiftMeta เดือนใหม่
- ถ้า DB seed ไปก่อนแก้ไฟล์ ให้รัน setval ใน DB เอง (ดู FAQ ท้ายไฟล์)

================================================================================
B) generate_patient_dialysis.py — B01–B07 ครบชุด (แนะนำ)
================================================================================

วัตถุประสงค์
-----------
สร้างข้อมูลฟอกไตครบ 1 session ต่อรอบ (B01–B07) ตาม HEMO_COMPLETE_SESSION_SPEC.md
อ่าน schedule จาก 05-Patients.sql, 08-Sections.sql, 11-SectionSlotPatient.sql

ข้อกำหนด
---------
- Python 3.10+
- รันจากโฟลเดอร์โปรเจกต์ (working directory = โฟลเดอร์ที่มีไฟล์ SQL)
- Core seed + INIT ใน DB แล้ว (Medicines Espogen -234, Assessments ฯลฯ)

คำสั่งหลัก — หลาย patient (30 คน)
---------------------------------
    generate_all_patients.bat
    generate_all_patients.bat --span 4m
    generate_all_patients.bat --dry-run

หรือ:
    python generate_patient_dialysis.py --generate-all --span today

หลัง loop จะรันอัตโนมัติ: patch B03 → rebuild B05 → rebuild B04-all
(ข้าม post-steps: --skip-post-steps)

คำสั่ง — ทีละ 1 คน
-------------------
    python generate_patient_dialysis.py --list-patients
    python generate_patient_dialysis.py --patient-id 6505315 --span today
    python generate_patient_dialysis.py --patient-id 6455308 --span 4m
    python generate_patient_dialysis.py --patient-id 6505315 --dry-run

span: today | 2m | 4m | 6m  (เริ่ม 2025-08-01)

คำสั่งซ่อม / rebuild (หลังมี B03)
---------------------------------
    python generate_patient_dialysis.py --patch-b03-weights
    python generate_patient_dialysis.py --rebuild-b05
    python generate_patient_dialysis.py --rebuild-b04-all
    python generate_patient_dialysis.py --rebuild-b04
    python generate_patient_dialysis.py --restore-b07 --patient-id 6505315
    python generate_patient_dialysis.py --validate-b03

ไฟล์ที่สร้าง
------------
B01-AvShunts.sql
B02-DialysisPrescriptions.sql
B07-MedicinePrescriptions.sql   (ก่อน B06 — FK PrescriptionId)
B03-HemodialysisRecords.sql
B04-DialysisRecords.sql
B05-Assessment.sql
B06-ExecutionRecords.sql

State: .hemo_gen_state.json

เริ่มใหม่ทั้งชุด (ก่อน generate-all)
--------------------------------------
    ลบ B01–B07 *.sql และ .hemo_gen_state.json แล้วรัน generate-all

รายละเอียดเพิ่ม: README_GENERATOR.md

================================================================================
C-group) Stock — Equipments & MedicalSupplies
================================================================================

ไฟล์
----
C01-Equipments.sql              อุปกรณ์ 9 รายการ (Id 1–9)
C02-MedicalSupplies.sql         ยาและวัสดุสิ้นเปลือง 13 รายการ (Id 1–13)
C03-AutoStock-Equipments.sql    ชุด AutoStock อุปกรณ์ครบ 9 รายการ (StockType=3)
C04-AutoStock-MedicalSupplies.sql ชุด AutoStock วัสดุครบ 13 รายการ (StockType=2)
run_cgroup_stock_seed.bat       รัน C01 → C02 → C03 → C04

คำสั่ง
------
    run_cgroup_stock_seed.bat

ลำดับแนะนำ: รันหลัง run_agroup_hogwarts_core_seed.bat (ก่อนหรือหลัง B group ก็ได้)

หมายเหตุ
--------
- Equipments / MedicalSupplies ใช้ Id บวก 1, 2, 3 … (C03/C04 อ้างอิง Id เหล่านี้)
- AutoStock UnitId = -1 (Hogwarts), UUID ชุด C03/C04 คงที่ใน seed
- field ที่ไม่มีข้อมูลจริง (Barcode, Note, Quantity ฯลฯ) ใส่ค่าสมมุติไว้แล้ว
- รันซ้ำจะ error duplicate key — ลบแถว seed ก่อน re-seed
- ถ้าเคย seed ด้วย Id ลบ (-501..-613) ให้ลบแถวเก่าก่อนรันชุดใหม่

================================================================================
C) generate_b03_incremental.py — เติมแค่ B03 (legacy)
================================================================================

ใช้เมื่อ: มี B03 seed อยู่แล้ว ต้องการซ่อม/เติมแถว HemodialysisRecords เท่านั้น
ไม่สร้าง B04–B07 — ถ้าต้องการครบชุด ใช้ generate_patient_dialysis.py แทน

โหมดเริ่มต้น (gap-fill):
  • ต่อคู่ (PatientId, SectionId) จาก 11-SectionSlotPatient
  • เติมวันทำการที่หายระหว่างสองวันที่มีแถว (จำกัด --max-internal-gap-days)
  • เติมหางจากวันล่าสุดของคู่นั้น +1 ถึง --to-date

โหมด tail (--mode tail): clone ทุกแถวของวันล่าสุดแล้วต่อท้าย

ไฟล์ที่อ่าน (ค่าเริ่มต้น)
-------------------------
- B03-HemodialysisRecords.sql
- 08-Sections.sql
- 09-ScheduleMeta.sql
- 10-ShiftMeta.sql
- 11-SectionSlotPatient.sql

คำสั่งที่ใช้บ่อย
----------------
    python generate_b03_incremental.py
    python generate_b03_incremental.py --to-date 2026-04-30
    python generate_b03_incremental.py --no-merge-into-base
    python generate_b03_incremental.py --mode tail
    python generate_b03_incremental.py --max-internal-gap-days 45

หลัง merge เข้า B03 แล้ว รัน run_bgroup_supplemental_seed.bat (หรือเฉพาะ B03 ใน bat)

FAQ gap-fill: ดูหมายเหตุเดิมด้านล่าง (ทำไมยังสร้างแถวทั้งที่วันล่าสุดเป็นวันนี้)

================================================================================
FAQ
================================================================================

ทำไมรัน generate_b03_incremental แล้วยังสร้างแถว ทั้งที่วันล่าสุดเป็นวันนี้?
  gap-fill แยกต่อคู่ (PatientId, ShiftSectionId) ไม่ใช่แค่วันล่าสุดของทั้งไฟล์

กดเพิ่มพนักงานในเมนู Shift แล้ว error PK_ShiftMeta?
  สาเหตุ: seed ใส่ ShiftMeta Id=1,2 แต่ sequence ไม่ถูก sync
  แก้ใน DB (ครั้งเดียว):
    SELECT setval(pg_get_serial_sequence('local."ShiftMeta"', 'Id'),
      COALESCE((SELECT MAX("Id") FROM local."ShiftMeta"), 1));
    SELECT setval(pg_get_serial_sequence('local."ScheduleMeta"', 'Id'),
      COALESCE((SELECT MAX("Id") FROM local."ScheduleMeta"), 1));
  หรือ re-run 09-ScheduleMeta.sql + 10-ShiftMeta.sql (ถ้ายังไม่มีแถวซ้ำ)

รัน generate แล้วไม่มี B07?
  รัน: python generate_patient_dialysis.py --restore-b07 --patient-id <id>
  หรือลบ .hemo_gen_state.json แล้ว generate ใหม่

generate-all vs generate ทีละคน?
  generate-all = วนทุกคนใน 05-Patients.sql + post-steps
  รันซ้ำคนเดิม = append ซ้ำ — ระวัง

Timezone / วันทำการ (b03 incremental):
- เวลาใน SQL เป็น UTC
- --to-date today ใช้ --today-tz (default Asia/Bangkok)
- ข้ามเสาร์–อาทิตย์

================================================================================

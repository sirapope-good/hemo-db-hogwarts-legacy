================================================================================
README — การใช้ generate_b03_incremental.py
================================================================================

วัตถุประสงค์
-----------
สคริปต์ Python นี้ใช้ซ่อม/เติมแถว HemodialysisRecords (B03) เมื่อไฟล์ B03
ถูกแก้เล่นจนพัง (ลบวันที่ ลบแถว ฯลฯ) โดยอิง slot ผู้ป่วย–section จาก
11-SectionSlotPatient และเวลา section จาก 08 / 09

โหมดเริ่มต้น (gap-fill) ไม่ได้ “สร้างทุกวันทำการย้อนหลังตั้งแต่ต้นไฟล์”
เพราะ seed เดิมเว้นวันได้ — แต่จะ:
  • ต่อคู่ (PatientId, SectionId): ดูวันที่มีแถวในไฟล์จริง
  • เติมวันทำการที่หาย “ระหว่าง” สองวันนั้น ถ้าห่างกันไม่เกิน
    --max-internal-gap-days (กันช่องว่างยาวผิดจริง / ไม่สร้างย้อนหลังมหาศาล)
  • เติม “หาง” จากวันล่าสุดของคู่นั้น +1 ถึงวันปลายทาง (--to-date)

โหมด tail (--mode tail): พฤติกรรมแบบเดิม — clone ทุกแถวของ “วันล่าสุดในไฟล์”
แล้วต่อท้ายจนถึง to-date (ไม่ใช้ logic ช่องว่างต่อคู่)

ข้อกำหนด
---------
- Python 3 (แนะนำ 3.10+)
- รันจากโฟลเดอร์ที่มีไฟล์ seed ชุดนี้ (working directory = โฟลเดอร์โปรเจกต์)

ไฟล์ที่สคริปต์อ่าน (ค่าเริ่มต้น)
---------------------------------
- B03-HemodialysisRecords.sql     แหล่งข้อมูล baseline + ปลายทาง merge
- 08-Sections.sql                 map เวลาเริ่ม -> ShiftSectionId
- 09-ScheduleMeta.sql             เวลา section ต่อ unit (Hogwarts / Dark Arts)
- 10-ShiftMeta.sql                ใช้เตือนความสอดคล้องเดือน (ไม่ block การ generate)
- 11-SectionSlotPatient.sql       validate คู่ PatientId + SectionId

กฎการ generate (ตามที่ตั้งค่าไว้)
---------------------------------
- เวลาที่เขียนลง SQL เป็น UTC เสมอ
- วันที่ปลายทางเมื่อใช้ --to-date today:
  ใช้ timezone จาก --today-tz (ค่าเริ่มต้น: Asia/Bangkok)
- ข้ามเฉพาะวันเสาร์–อาทิตย์ (วันทำการ = จันทร์–ศุกร์)
- ไม่มีวันหยุดพิเศษใน logic นี้

คำสั่งที่ใช้บ่อย
----------------
รันแบบเริ่มต้น (gap-fill ถึง today ตาม Asia/Bangkok + merge เข้า B03 + ลบ incremental):
    python generate_b03_incremental.py

กำหนด timezone สำหรับ today (เช่น UTC):
    python generate_b03_incremental.py --today-tz UTC

ระบุวันปลายทางเอง (ยัง merge เข้า B03 ตามเดิม):
    python generate_b03_incremental.py --to-date 2026-04-30

สร้างไฟล์ incremental อย่างเดียว ไม่ merge เข้า B03:
    python generate_b03_incremental.py --no-merge-into-base

ขยายแบบเดิม (clone วันล่าสุดทั้งก้อน):
    python generate_b03_incremental.py --mode tail

จำกัดความยาวช่องว่างที่ยอมเติมระหว่างสองวันที่มีข้อมูล (ค่าเริ่มต้น 90 วันปฏิทิน):
    python generate_b03_incremental.py --max-internal-gap-days 45

ยอมเติมช่องว่างยาวไม่จำกัด (ระวังแถวพุ่งถ้า seed เว้นช่วงยาว):
    python generate_b03_incremental.py --max-internal-gap-days 0

merge แล้วแต่เก็บไฟล์ incremental ไว้ตรวจสอบ:
    python generate_b03_incremental.py --keep-incremental-file

เปลี่ยนชื่อไฟล์ input/output (กรณี path พิเศษ):
    python generate_b03_incremental.py --input MyB03.sql --output MyInc.sql

หลัง generate เสร็จ — รัน seed เข้า DB
--------------------------------------
สคริปต์ bat เดิมรันเฉพาะ B03-HemodialysisRecords.sql ดังนั้นหลัง merge แล้วให้รัน:
    run_bgroup_supplemental_seed.bat

ถ้าใช้ --no-merge-into-base ต้องเอา SQL จากไฟล์ incremental ไปรันเองหรือ merge เข้า B03 ก่อน
จึงจะสอดคล้องกับ bat เดิม

FAQ — ทำไมรันแล้วยังสร้างแถว ทั้งที่วันล่าสุดในไฟล์เป็นวันนี้แล้ว?
------------------------------------------------------------------
โหมด gap-fill ไม่ได้ดูแค่ “วันล่าสุดของทั้งไฟล์” แต่แยกต่อคู่
(PatientId, ShiftSectionId) ตาม 11-SectionSlotPatient:
- ผู้ป่วยคนเดียวอาจมีหลาย section; บางคู่ยังมีแถวล่าสุดก่อน to-date
  ระบบจึงเติม “หาง” ของคู่นั้นจนถึงวันปลายทาง
- ถ้ามีช่องว่างวันทำการระหว่างสองวันที่มีข้อมูลของคู่เดียวกัน (และอยู่ใน
  --max-internal-gap-days) ก็จะถูกเติม
สคริปต์จะพิมพ์บรรทัดสรุปตัวเลขเมื่อมีแถวถูกสร้าง ช่วยให้เห็นว่าเกิดจากหางหรือช่องว่างระหว่าง anchor

หมายเหตุ
---------
- คู่ (patient, section) ที่ไม่เคยมีแถวในไฟล์เลย จะไม่ถูก gap-fill (ไม่มี template)
- Warning เรื่อง ShiftMeta เดือนไม่ตรง: เป็นการแจ้งเตือนเท่านั้น ไม่หยุดการ generate
- รูปแบบแถวที่ merge จะจัดให้สอดคล้องกับแถวเดิมใน B03
- บนบางเครื่อง Windows ที่ไม่มี timezone database:
  ถ้า --today-tz เป็น Asia/Bangkok ระบบจะ fallback เป็น UTC+7 ให้อัตโนมัติ

================================================================================

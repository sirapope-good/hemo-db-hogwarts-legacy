-- =============================================================================
-- B01-AvShunts.sql — ข้อมูลทดสอบ AvShunts สำหรับผู้ป่วยทุกคนใน 05-Patients.sql
-- รันหลัง 05-Patients.sql (ไม่ใช่ core seed — แก้วันที่/เวลาได้ตามต้องการ)
-- =============================================================================
--
-- CatheterType (เก็บเป็นเลข index ตาม enum Wasenshi.HemoDialysisPro.Models.Enums.CatheterType):
--   0 = AVFistula
--   1 = AVGraft
--   2 = PermCath   (Perm Cath / long-term)
--   3 = DoubleLumen
--
-- Side (เก็บเป็นเลข index ตาม enum SideEnum):
--   0 = Left
--   1 = Right
--
-- =============================================================================

INSERT INTO local."AvShunts"(
	"Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive",
	"PatientId", "EstablishedDate", "EndDate",
	"CatheterType", "Side",
	"ShuntSite", "CatheterizationInstitution", "Note", "ReasonForDiscontinuation",
	"Ac", "AFillVolume", "VFillVolume", "ACatheterVolume", "VCatheterVolume", "ANeedleSize", "VNeedleSize"
)
VALUES
-- PatientId = 49082/54 (=908), CatheterType=2 PermCath, Side=0 Left
('96937342-fb3e-4cd9-a8a3-f138ce5a9aec','2026-04-21 02:00:00+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:00+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
908,'2025-08-12 01:00:00+00',NULL,
2,0,
'subclavian','Hogwarts Infirmary','seed B01','',
'Clexane',33,23,23,43,16,16),

('f49a6112-870c-43fd-af48-c9be22e995d5','2026-04-21 02:00:01+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:01+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
213860,'2025-11-03 02:30:00+00','2026-07-15 02:30:00+00',
0,1,
'subclavian','St Mungo''s','B01 seed - มี EndDate','',
NULL,NULL,NULL,NULL,NULL,17,16),

('65b2b3ea-4609-4df5-87e5-91699927a623','2026-04-21 02:00:02+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:02+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
48324,'2026-02-18 03:00:00+00',NULL,
1,0,
'jugular','Hogsmeade Clinic','','',
'Heparin',20,20,NULL,NULL,15,15),

('e68d8660-4669-49e3-9388-bca62b9aa6fd','2026-04-21 02:00:03+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:03+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
670001117,'2026-04-19 01:42:00+00','2026-05-31 01:42:00+00',
0,1,
'subcravian','CI Test','Route Test pattern (B01)','',
NULL,NULL,NULL,NULL,NULL,17,16),

('ada63a9e-d5c2-453a-bd6c-7d4fdd9ad874','2026-04-21 02:00:04+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:04+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6802740,'2025-05-20 04:00:00+00',NULL,
3,0,
'femoral','Ministry Medical Wing','','',
NULL,NULL,NULL,NULL,NULL,NULL,NULL),

('b2a603af-6dc3-4e2b-9db8-d5cf0c1bb5ef','2026-04-21 02:00:05+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:05+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6505315,'2025-09-01 00:00:00+00','2026-03-01 00:00:00+00',
2,1,
'subclavian','Hogwarts Infirmary','สิ้นสุดตามแผน','infection resolved',
'Clexane',25,25,20,20,14,14),

('586d6e67-2903-4df7-8449-ebeb14a651f2','2026-04-21 02:00:06+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:06+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6455308,'2026-04-13 01:46:00+00',NULL,
2,0,
'subcravian','456','123','',
'Clexane',33,23,23,43,16,16),

('7163a81a-1d63-4e98-8ed8-656c986013e1','2026-04-21 02:00:07+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:07+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6602502,'2025-12-05 06:00:00+00','2026-09-30 06:00:00+00',
1,1,
'jugular','Hogwarts Infirmary','','',
NULL,18,18,NULL,NULL,16,15),

('d13fa60e-268e-4d26-85ed-035204612dba','2026-04-21 02:00:08+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:08+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6603132,'2025-07-22 07:15:00+00',NULL,
0,0,
'subclavian','St Mungo''s','','',
'Heparin',NULL,NULL,NULL,NULL,15,15),

('9dd85bae-6f72-4097-9575-beee370232d3','2026-04-21 02:00:09+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:09+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
5333974,'2026-01-10 08:00:00+00','2026-06-01 08:00:00+00',
3,1,
'femoral','Hogsmeade Clinic','','',
NULL,NULL,NULL,30,30,14,14),

('c722b535-bcb1-4df6-95c2-b0b15c772ab9','2026-04-21 02:00:10+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:10+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6521515,'2025-10-14 09:30:00+00',NULL,
2,0,
'subclavian','Ministry Medical Wing','B01','',
'Clexane',22,22,21,21,16,16),

('08cd9848-427c-43b7-bedf-86ee041f18de','2026-04-21 02:00:11+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:11+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6521637,'2025-04-25 10:00:00+00','2025-11-30 10:00:00+00',
1,1,
'jugular','Hogwarts Infirmary','ยกเลิกแล้ว','thrombosis',
NULL,NULL,NULL,NULL,NULL,17,17),

('a0ac2631-c421-4d48-9784-821bc1daecdc','2026-04-21 02:00:12+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:12+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6508733,'2026-03-01 11:00:00+00',NULL,
0,0,
'subclavian','St Mungo''s','','',
'Heparin',30,28,NULL,NULL,16,16),

('d6d13add-ac24-41f0-b903-b6b03317cf58','2026-04-21 02:00:13+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:13+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6512620,'2025-06-30 12:00:00+00','2026-12-31 12:00:00+00',
3,1,
'jugular','Hogwarts Infirmary','','',
NULL,19,19,25,25,15,14),

('773cfc69-657c-44a6-ad72-31a56c473386','2026-04-21 02:00:14+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:14+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6300865,'2025-11-18 13:20:00+00',NULL,
1,0,
'subclavian','Hogsmeade Clinic','B01','',
'Clexane',NULL,NULL,NULL,NULL,18,18),

('4a3aba83-6fda-49b9-a397-5b2f8f4d4f11','2026-04-21 02:00:15+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:15+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6519635,'2025-08-01 14:00:00+00','2026-02-28 14:00:00+00',
2,1,
'femoral','Ministry Medical Wing','','relocated',
NULL,24,24,22,22,15,15),

('0ed19211-0fd1-4ebc-b8b5-adfa20d211b2','2026-04-21 02:00:16+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:16+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6800776,'2026-04-05 15:00:00+00',NULL,
0,0,
'subclavian','Hogwarts Infirmary','','',
'Heparin',21,21,NULL,NULL,16,15),

('1d3e6ab2-2a72-49a1-9027-83fdd61370d2','2026-04-21 02:00:17+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:17+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6802616,'2025-03-11 16:45:00+00','2025-12-20 16:45:00+00',
3,1,
'jugular','St Mungo''s','','completed course',
NULL,NULL,NULL,28,28,14,13),

('e9ee1a37-9290-47a6-b995-0346bf2028e9','2026-04-21 02:00:18+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:18+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6802588,'2025-12-28 17:00:00+00',NULL,
1,0,
'subclavian','Hogwarts Infirmary','','',
'Clexane',26,26,NULL,NULL,17,17),

('c781cdfa-b5c9-4d31-9cf7-4f8bfebdd5a2','2026-04-21 02:00:19+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:19+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6411508,'2025-02-02 18:00:00+00','2026-08-02 18:00:00+00',
2,1,
'jugular','Hogsmeade Clinic','pediatric line','',
NULL,20,20,18,18,14,14),

('e3008742-1cb2-4281-84b9-c94e41de635e','2026-04-21 02:00:20+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:20+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6701952,'2025-09-15 19:00:00+00',NULL,
0,0,
'subclavian','Ministry Medical Wing','B01','',
'Heparin',NULL,NULL,NULL,NULL,18,17),

('52a575c2-899d-46de-9e8a-d294b9eef6c0','2026-04-21 02:00:21+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:21+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6702221,'2025-01-08 20:00:00+00','2025-10-08 20:00:00+00',
1,1,
'femoral','Hogwarts Infirmary','','occlusion',
'Clexane',27,27,NULL,NULL,16,16),

('f030ad58-0687-4d5c-8340-dd60215602c2','2026-04-21 02:00:22+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:22+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
67030106,'2026-02-25 21:00:00+00',NULL,
3,0,
'subclavian','St Mungo''s','','',
NULL,22,22,24,24,15,15),

('294cf861-ca52-4610-88de-a3c6a6849e66','2026-04-21 02:00:23+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:23+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
184706,'2025-07-01 22:00:00+00','2027-01-01 22:00:00+00',
2,1,
'jugular','Hogwarts Infirmary','long-term plan','',
NULL,NULL,NULL,22,22,17,16),

('06b03a31-3980-42c8-93d7-201c6f5d8b63','2026-04-21 02:00:24+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:24+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6706961,'2025-10-30 23:00:00+00',NULL,
0,0,
'subclavian','Ministry Medical Wing','','',
'Heparin',29,29,NULL,NULL,16,16),

('9bba656d-d81b-4378-a84d-90ae2f8a35a4','2026-04-21 02:00:25+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:25+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
530323,'2025-05-05 00:30:00+00','2026-04-30 00:30:00+00',
1,1,
'subcravian','St Mungo''s','B01','',
NULL,NULL,NULL,NULL,NULL,15,15),

('27b246d3-3c52-4df8-9d34-39152b0c25b8','2026-04-21 02:00:26+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:26+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6706476,'2026-03-20 01:00:00+00',NULL,
3,0,
'femoral','Hogwarts Infirmary','','',
'Clexane',23,23,26,26,14,14),

('cdfb64ed-9aa4-4203-af4f-ed617341dd14','2026-04-21 02:00:27+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:27+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
361343,'2025-11-11 02:00:00+00','2026-05-11 02:00:00+00',
2,1,
'jugular','Hogsmeade Clinic','','',
NULL,25,25,NULL,NULL,16,15),

('216855f4-6083-4f46-8dd0-865ca4425e38','2026-04-21 02:00:28+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:28+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6705071,'2025-08-30 03:00:00+00',NULL,
0,0,
'subclavian','Hogwarts Infirmary','','',
'Heparin',NULL,NULL,NULL,NULL,17,17),

('9542f049-5c84-4af7-9a61-829833a4f6ca','2026-04-21 02:00:29+00','866dabc4-6501-44d2-a0e5-65da9c45a46e','2026-04-21 02:00:29+00','866dabc4-6501-44d2-a0e5-65da9c45a46e',TRUE,
6800002,'2025-12-12 04:00:00+00','2026-10-01 04:00:00+00',
1,1,
'subclavian','Ministry Medical Wing','B01 final row','',
'Clexane',24,24,20,20,16,16);

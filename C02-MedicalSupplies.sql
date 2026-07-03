-- C-group Stock: MedicalSupplies (ยาและวัสดุสิ้นเปลือง — Hogwarts hemodialysis unit)
-- Id 1–13 — รันหลัง core seed (A group)

INSERT INTO local."MedicalSupplies" (
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy",
    "IsActive", "Name", "Code", "PieceUnit", "Barcode", "Note", "Image"
)
VALUES
(
    1, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'สายนำเลือด (Bloodline / AV Fistula Blood Tubing Set)',
    'MS-BLD-001', 'ชุด', '8850502002001',
    'Bloodline / AV Fistula Blood Tubing Set สำหรับเชื่อมต่อกับเครื่องฟอกไต', NULL
),
(
    2, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'เข็มแทงเส้นฟอกไต (AV Fistula Needle)',
    'MS-AVN-002', 'อัน', '8850502002002',
    'เบอร์ 15G, 16G, 17G — ใช้แทง AV fistula', NULL
),
(
    3, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'น้ำยาฟอกเลือด (Dialysate Concentrates)',
    'MS-DIA-003', 'ถัง', '8850502002003',
    'Acid Concentrate และ Bicarbonate Powder/Cartridge', NULL
),
(
    4, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'น้ำยาฆ่าเชื้อเครื่องไตเทียม (Disinfectant for HD Machine)',
    'MS-DIS-004', 'ขวด', '8850502002004',
    'Citric acid, Peracetic acid, Sodium hypochlorite', NULL
),
(
    5, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'Transducer Protector (ตัวป้องกันเซนเซอร์ตรวจวัดแรงดัน)',
    'MS-TRD-005', 'ชิ้น', '8850502002005',
    'ป้องกันเซนเซอร์ตรวจวัดแรงดันในวงจรฟอกไต', NULL
),
(
    6, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'ชุดทำหัตถการปลอดเชื้อ (Sterile Dressing Set / On-Off HD Set)',
    'MS-DRS-006', 'ชุด', '8850502002006',
    'Sterile Dressing Set / On-Off HD Set', NULL
),
(
    7, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'ถุงมือ (Gloves)',
    'MS-GLV-007', 'คู่', '8850502002007',
    'ถุงมือปลอดเชื้อ (Sterile Gloves) และถุงมือตรวจโรค (Clean Gloves)', NULL
),
(
    8, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'อุปกรณ์ทำความสะอาดผิวหนัง (Skin Antiseptics)',
    'MS-ANT-008', 'ขวด', '8850502002008',
    '2% Chlorhexidine in 70% Alcohol หรือ Povidone-Iodine', NULL
),
(
    9, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'พลาสเตอร์และวัสดุกดห้ามเลือด (Hemostatic Dressing / Dialysis Tape)',
    'MS-HEM-009', 'ชุด', '8850502002009',
    'พลาสเตอร์เหนียว, ก๊อซสเตอไรล์, สายรัดห้ามเลือด (Tourniquet)', NULL
),
(
    10, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'กระบอกฉีดยาและเข็ม (Syringes & Needles)',
    'MS-SYR-010', 'ชุด', '8850502002010',
    'ขนาด 1 ml, 3 ml, 5 ml, 10 ml, 20 ml และเข็มเบอร์ต่างๆ', NULL
),
(
    11, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'ชุดให้น้ำยา (Infusion Set)',
    'MS-INF-011', 'ชุด', '8850502002011',
    'Infusion Set สำหรับให้สารน้ำ/ยาทาง IV', NULL
),
(
    12, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'อุปกรณ์ล้างแผลและดูแลสายสวน (Catheter Care Kits)',
    'MS-CAT-012', 'ชุด', '8850502002012',
    'สำหรับผู้ป่วยที่ใส่ Double Lumen Catheter', NULL
),
(
    13, '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    '2025-08-22 02:17:30.920047+00', '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    'หน้ากากอนามัยและผ้ากันเปื้อนกันน้ำ (Mask & Waterproof Apron)',
    'MS-MSK-013', 'ชุด', '8850502002013',
    'สำหรับบุคลากรเพื่อป้องกันการกระเด็นของเลือด', NULL
);

SELECT setval(
    pg_get_serial_sequence('local."MedicalSupplies"', 'Id'),
    COALESCE((SELECT MAX("Id") FROM local."MedicalSupplies"), 1)
);

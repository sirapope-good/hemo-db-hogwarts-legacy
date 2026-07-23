INSERT INTO local."ScheduleMeta" 
(
    "Id", "Created", "CreatedBy", "Updated", "UpdatedBy", 
    "IsActive", "UnitId", "UnitName", 
    "Section1", "Section2", "Section3", "Section4", "Section5", "Section6"
)
VALUES 
(
    1, '2026-02-11 04:45:19.263035+00', '00000000-0000-0000-0000-000000000000', '2026-02-11 04:47:41.039815+00', '00000000-0000-0000-0000-000000000000', 
    true, -1, 'Hogwarts Hospital Wing', 
    '05:00:00', '09:00:00', '13:00:00', '17:00:00', NULL, NULL
),
(
    2, '2026-02-11 04:46:37.127247+00', '00000000-0000-0000-0000-000000000000', '2026-02-11 04:47:57.575303+00', '00000000-0000-0000-0000-000000000000', 
    true, 1, 'Azkaban Ward', 
    '12:00:00', '16:00:00', '20:00:00', NULL, NULL, NULL
);

-- หลัง INSERT Id แบบ manual ต้อง sync identity sequence (มิฉะนั้น UI สร้าง ShiftMeta ใหม่จะชน PK)
SELECT setval(
    pg_get_serial_sequence('local."ScheduleMeta"', 'Id'),
    COALESCE((SELECT MAX("Id") FROM local."ScheduleMeta"), 1)
);
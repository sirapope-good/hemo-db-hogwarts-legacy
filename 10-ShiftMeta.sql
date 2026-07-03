INSERT INTO local."ShiftMeta" 
("Id", "Created", "CreatedBy", "Updated", "UpdatedBy", "IsActive", "Month", "ScheduleMetaId")
VALUES 
(1, '2026-02-11 02:18:04.791043+00', '00000000-0000-0000-0000-000000000000', '2026-02-11 02:18:04.791043+00', '00000000-0000-0000-0000-000000000000', true, '2026-02-01', 1),
(2, '2026-02-11 02:19:51.007434+00', '00000000-0000-0000-0000-000000000000', '2026-02-11 02:19:51.007434+00', '00000000-0000-0000-0000-000000000000', true, '2026-02-01', 2);

-- หลัง INSERT Id แบบ manual ต้อง sync identity sequence (มิฉะนั้นกดเพิ่มพนักงานใน Shift จะ duplicate PK_ShiftMeta)
SELECT setval(
    pg_get_serial_sequence('local."ShiftMeta"', 'Id'),
    COALESCE((SELECT MAX("Id") FROM local."ShiftMeta"), 1)
);
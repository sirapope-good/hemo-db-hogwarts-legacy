-- Local HemoAdmin starter accounts (master DB hemo-master, public."AdminUsers").
-- Username good / nott, display Goody / Nott, password Test@1234.
-- Role 2 = SuperAdmin (Platform Admin: every named permission).
-- Re-run updates these two rows and resets the password to the seed value.

INSERT INTO public."AdminUsers"(
    "Id", "Username", "Email", "DisplayName", "PasswordHash", "Role",
    "IsSupervisor", "Region", "IsActive", "CreatedDate", "LastLoginDate"
)
VALUES
(
    '11111111-1111-4111-8111-111111111001',
    'good',
    NULL,
    'Goody',
    'v1|200000|XRd/k4PqikB9U0gZrvTc0g==|OiYzxth4WmTieS1XrGmX4B9KNDwNL6PWun+okNRimV4=',
    2,
    FALSE,
    NULL,
    TRUE,
    timezone('utc', now()),
    NULL
),
(
    '11111111-1111-4111-8111-111111111002',
    'nott',
    NULL,
    'Nott',
    'v1|200000|4+RYildDvKlrd5xLfp6xZg==|GvmjVd30AJSX/YYuoBUUwlrTy34PB0BIzDj07o2LHX8=',
    2,
    FALSE,
    NULL,
    TRUE,
    timezone('utc', now()),
    NULL
)
ON CONFLICT ("Username") DO UPDATE SET
    "DisplayName" = EXCLUDED."DisplayName",
    "PasswordHash" = EXCLUDED."PasswordHash",
    "Role" = EXCLUDED."Role",
    "IsActive" = TRUE;

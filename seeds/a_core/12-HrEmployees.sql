-- HR employees for the same HemoPro seed users.
-- Register() would call EnsureEmployeeProfile for Doctor / Nurse / PN / HeadNurse / HD / SpecialHD.
-- This script does that link in SQL: Sites (from clinical units), Employees, EmployeeSites, Users.EmployeeId.
-- Safe to re-run: skips rows that already exist. Login again so the token picks up employee_code.

DROP TABLE IF EXISTS hogwarts_workforce;
CREATE TEMP TABLE hogwarts_workforce AS
SELECT DISTINCT
    u."Id",
    u."UserName",
    COALESCE(NULLIF(btrim(u."FirstName"), ''), u."UserName") AS "FirstName",
    u."LastName"
FROM local."Users" u
JOIN local."AspNetUserRoles" ur ON ur."UserId" = u."Id"
JOIN local."Roles" r ON r."Id" = ur."RoleId"
WHERE (
    r."Name" IN ('Doctor', 'Nurse', 'PN', 'HeadNurse', 'HD', 'SpecialHD')
    OR (
        r."AutoLinkEmployee" = TRUE
        AND r."Name" NOT IN ('Administrator', 'SuperAdministrator')
    )
)
  AND u."UserName" <> 'rootadmin';

INSERT INTO local."Sites"(
    "Id", "Created", "CreatedBy", "IsActive", "Name", "Code", "ClinicalUnitId")
SELECT
    gen_random_uuid(),
    CURRENT_TIMESTAMP,
    '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    COALESCE(NULLIF(btrim(unit."Name"), ''), 'Unit ' || unit."Id"::text),
    unit."Code",
    unit."Id"
FROM local."Units" unit
WHERE unit."Id" IN (
    SELECT uu."UnitId"
    FROM local."UserUnits" uu
    JOIN hogwarts_workforce w ON w."Id" = uu."UserId"
    UNION
    SELECT -1
)
AND NOT EXISTS (
    SELECT 1 FROM local."Sites" site WHERE site."ClinicalUnitId" = unit."Id"
);

INSERT INTO local."Employees"(
    "Id", "Created", "CreatedBy", "IsActive",
    "EmployeeCode", "FirstName", "LastName",
    "EmploymentType", "Status", "UserId")
SELECT
    gen_random_uuid(),
    CURRENT_TIMESTAMP,
    '866dabc4-6501-44d2-a0e5-65da9c45a46e',
    TRUE,
    w."UserName",
    w."FirstName",
    w."LastName",
    0,
    0,
    w."Id"
FROM hogwarts_workforce w
WHERE NOT EXISTS (
    SELECT 1 FROM local."Employees" employee WHERE employee."UserId" = w."Id"
)
AND NOT EXISTS (
    SELECT 1 FROM local."Employees" employee WHERE employee."EmployeeCode" = w."UserName"
);

INSERT INTO local."EmployeeSites"("EmployeeId", "SiteId")
SELECT employee."Id", site."Id"
FROM local."Employees" employee
JOIN hogwarts_workforce w ON w."Id" = employee."UserId"
JOIN local."UserUnits" uu ON uu."UserId" = w."Id"
JOIN local."Sites" site ON site."ClinicalUnitId" = uu."UnitId"
ON CONFLICT ("SiteId", "EmployeeId") DO NOTHING;

INSERT INTO local."EmployeeSites"("EmployeeId", "SiteId")
SELECT employee."Id", site."Id"
FROM local."Employees" employee
JOIN hogwarts_workforce w ON w."Id" = employee."UserId"
JOIN local."Sites" site ON site."ClinicalUnitId" = -1
WHERE NOT EXISTS (
    SELECT 1 FROM local."UserUnits" uu WHERE uu."UserId" = w."Id"
)
ON CONFLICT ("SiteId", "EmployeeId") DO NOTHING;

UPDATE local."Users" u
SET "EmployeeId" = employee."EmployeeCode"
FROM local."Employees" employee
JOIN hogwarts_workforce w ON w."Id" = employee."UserId"
WHERE u."Id" = w."Id"
  AND (u."EmployeeId" IS NULL OR btrim(u."EmployeeId") = '');

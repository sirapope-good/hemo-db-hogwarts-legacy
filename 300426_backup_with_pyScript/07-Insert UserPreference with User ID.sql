INSERT INTO local."UserPreferences" ("UserId", "Is24HourFormat")
SELECT "Id", true
FROM local."Users"
ON CONFLICT ("UserId") 
DO UPDATE SET "Is24HourFormat" = EXCLUDED."Is24HourFormat";
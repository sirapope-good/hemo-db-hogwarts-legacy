INSERT INTO local."UserPreferences" ("UserId", "Is24HourFormat", "WeekStartsOn")
SELECT "Id", true, 1
FROM local."Users"
ON CONFLICT ("UserId") 
DO UPDATE SET "Is24HourFormat" = EXCLUDED."Is24HourFormat", "WeekStartsOn" = EXCLUDED."WeekStartsOn";
INSERT INTO public."UserPreferences" ("UserId", "Is24HourFormat")
SELECT "Id", true
FROM public."Users"
ON CONFLICT ("UserId") 
DO UPDATE SET "Is24HourFormat" = EXCLUDED."Is24HourFormat";
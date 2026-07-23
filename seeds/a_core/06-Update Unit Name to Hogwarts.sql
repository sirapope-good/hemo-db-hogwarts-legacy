UPDATE local."Units"
SET "Name" = 'Hogwarts Hospital Wing',
    "Updated" = CURRENT_TIMESTAMP
WHERE "Id" = -1;

UPDATE local."Units"
SET "Name" = 'Azkaban Ward',
    "Updated" = CURRENT_TIMESTAMP
WHERE "Id" = 1;

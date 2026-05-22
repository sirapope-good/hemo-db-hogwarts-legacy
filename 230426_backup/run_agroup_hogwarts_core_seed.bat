@echo off
SETLOCAL EnableDelayedExpansion
SET CONTAINER_NAME=db
SET DB_USER=postgres
SET DB_NAME=hemopro-local
SET PGPASSWORD=your_password_here

:: SET COLOR CODE ANSI
set "ESC="
set "G=%ESC%[92m"
set "R=%ESC%[91m"
set "Y=%ESC%[93m"
set "B=%ESC%[94m"
set "W=%ESC%[0m"

:: TITLE
cls
echo %B%============================================================%W%
echo   %Y%HEMODIALYSIS PRO - HOGWARTS LEGACY%W%
echo %B%============================================================%W%

SET "TOTAL_ERRORS=0"

:: --- STEP 1: CORE DATA ---
echo [STEP 1] Importing Core Data...
echo ------------------------------------------------------------
call :exec_sql "00-Units.sql"
call :exec_sql "01-Users.sql"
call :exec_sql "02-AspNetUserRoles.sql"
call :exec_sql "03-UserUnits.sql"
call :exec_sql "04-Incomes.sql"
call :exec_sql "05-Patients.sql"

:: --- STEP 2: CONFIGURATION ---
echo.
echo [STEP 2] Update patch and configuration...
echo ------------------------------------------------------------
call :exec_sql "06-Update Unit Name to Hogwarts.sql"
call :exec_sql "07-Insert UserPreference with User ID.sql"

:: --- STEP 3: SECTIONS SETUP ---
echo.
echo [STEP 3] Setting up Sections...
echo ------------------------------------------------------------
call :exec_sql "08-Sections.sql"
call :exec_sql "09-ScheduleMeta.sql"
call :exec_sql "10-ShiftMeta.sql"
call :exec_sql "11-SectionSlotPatient.sql"

:: --- SUMMARY ---
echo.
echo %B%============================================================%W%
if %TOTAL_ERRORS% equ 0 (
    echo   RESULT: %G%[SUCCESS] All scripts passed.%W%
) else (
    echo   RESULT: %R%[FAILED] Found %TOTAL_ERRORS% files with SQL errors.%W%
)
echo %B%============================================================%W%
if exist psql_log.tmp del psql_log.tmp

echo Process finished at %TIME%
echo Press any key to exit this window...
pause >nul
goto :eof

:: --- Subroutine: Support color and emtry string ---
:exec_sql
set "FILE_NAME=%~1"
set /p ="  > Executing: %FILE_NAME% ... " <nul

:: รัน SQL ๝ละเฝ็บ Log
docker exec -i %CONTAINER_NAME% psql -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 < "%FILE_NAME%" > psql_log.tmp 2>&1

if %errorlevel% equ 0 (
    echo %G%[PASS]%W%
) else (
    echo %R%[!!!! FAIL !!!!]%W%
    echo %R%------------------------------------------------------------%W%
    type psql_log.tmp
    echo %R%------------------------------------------------------------%W%
    SET /a TOTAL_ERRORS+=1
)
goto :eof
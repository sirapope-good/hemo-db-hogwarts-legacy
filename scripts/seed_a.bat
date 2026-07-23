@echo off
SETLOCAL EnableDelayedExpansion
cd /d "%~dp0.."
call "%~dp0_db_env.bat"

set "ESC="
set "G=%ESC%[92m"
set "R=%ESC%[91m"
set "Y=%ESC%[93m"
set "B=%ESC%[94m"
set "W=%ESC%[0m"

cls
echo %B%============================================================%W%
echo   %Y%HEMODIALYSIS PRO - HOGWARTS LEGACY (A-core)%W%
echo %B%============================================================%W%

SET "TOTAL_ERRORS=0"
SET "SEED_DIR=seeds\a_core"

echo [STEP 1] Importing Core Data...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\00-Units.sql"
call :exec_sql "%SEED_DIR%\01-Users.sql"
call :exec_sql "%SEED_DIR%\02-AspNetUserRoles.sql"
call :exec_sql "%SEED_DIR%\03-UserUnits.sql"
call :exec_sql "%SEED_DIR%\04-Incomes.sql"
call :exec_sql "%SEED_DIR%\05-Patients.sql"

echo.
echo [STEP 2] Update patch and configuration...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\06-Update Unit Name to Hogwarts.sql"
call :exec_sql "%SEED_DIR%\07-Insert UserPreference with User ID.sql"

echo.
echo [STEP 3] Setting up Sections...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\08-Sections.sql"
call :exec_sql "%SEED_DIR%\09-ScheduleMeta.sql"
call :exec_sql "%SEED_DIR%\10-ShiftMeta.sql"
call :exec_sql "%SEED_DIR%\11-SectionSlotPatient.sql"

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

:exec_sql
set "FILE_NAME=%~1"
set /p ="  > Executing: %FILE_NAME% ... " <nul
if not exist "%FILE_NAME%" (
    echo %Y%[SKIP - file not found]%W%
    goto :eof
)
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

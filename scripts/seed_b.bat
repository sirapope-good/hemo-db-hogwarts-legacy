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
echo   %Y%HEMODIALYSIS PRO - B01-B07 supplemental seed%W%
echo %B%============================================================%W%
echo   Order: %Y%B01%W% ^> %Y%B02%W% ^> %Y%B07%W% ^> %Y%B03%W% ^> %Y%B04%W% ^> %Y%B05%W% ^> %Y%B06%W%
echo %B%============================================================%W%

SET "TOTAL_ERRORS=0"
SET "SEED_DIR=seeds\b_sessions"

echo.
echo [B01] AvShunts...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B01-AvShunts.sql" 01

echo.
echo [B02] DialysisPrescriptions...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B02-DialysisPrescriptions.sql" 02

echo.
echo [B07] MedicinePrescriptions...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B07-MedicinePrescriptions.sql" 07

echo.
echo [B03] HemodialysisRecords...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B03-HemodialysisRecords.sql" 03

echo.
echo [B04] DialysisRecords...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B04-DialysisRecords.sql" 04

echo.
echo [B05] Assessment (Pre/Post vitals + AssessmentItems)...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B05-Assessment.sql" 05

echo.
echo [B06] ExecutionRecords...
echo ------------------------------------------------------------
call :exec_sql "%SEED_DIR%\B06-ExecutionRecords.sql" 06

echo.
echo %B%============================================================%W%
if %TOTAL_ERRORS% equ 0 (
    echo   RESULT: %G%[SUCCESS] All B01-B07 scripts passed.%W%
) else (
    echo   RESULT: %R%[FAILED] Found %TOTAL_ERRORS% SQL error^(s^).%W%
)
echo %B%============================================================%W%
if exist psql_log_b_01.tmp del psql_log_b_01.tmp
if exist psql_log_b_02.tmp del psql_log_b_02.tmp
if exist psql_log_b_03.tmp del psql_log_b_03.tmp
if exist psql_log_b_04.tmp del psql_log_b_04.tmp
if exist psql_log_b_05.tmp del psql_log_b_05.tmp
if exist psql_log_b_06.tmp del psql_log_b_06.tmp
if exist psql_log_b_07.tmp del psql_log_b_07.tmp

echo Process finished at %TIME%
echo Press any key to exit this window...
pause >nul
goto :eof

:exec_sql
set "FILE_NAME=%~1"
set "LOG_ID=%~2"
if "%LOG_ID%"=="" set "LOG_ID=run"
set /p ="  ^> Executing: %FILE_NAME% ... " <nul

if not exist "%FILE_NAME%" (
    echo %Y%[SKIP - file not found]%W%
    goto :eof
)

docker exec -i %CONTAINER_NAME% psql -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 < "%FILE_NAME%" > "psql_log_b_%LOG_ID%.tmp" 2>&1

if %errorlevel% equ 0 (
    echo %G%[PASS]%W%
) else (
    echo %R%[!!!! FAIL !!!!]%W%
    echo %R%------------------------------------------------------------%W%
    type "psql_log_b_%LOG_ID%.tmp"
    echo %R%------------------------------------------------------------%W%
    SET /a TOTAL_ERRORS+=1
)
goto :eof

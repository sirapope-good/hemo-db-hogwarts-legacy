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

cls
echo %B%============================================================%W%
echo   %Y%HEMODIALYSIS PRO - B01/B02/B03 supplemental seed%W%
echo %B%============================================================%W%
echo   ??????? core seed: %Y%B01-AvShunts%W% ^> %Y%B02-DialysisPrescriptions%W% ^> %Y%B03-HemodialysisRecords%W%
echo   (????????? %Y%11-SectionSlotPatient.sql%W% ???????? B02/B03 ????????????????)
echo %B%============================================================%W%

SET "TOTAL_ERRORS=0"

echo.
echo [B01] AvShunts...
echo ------------------------------------------------------------
call :exec_sql "B01-AvShunts.sql" 01

echo.
echo [B02] DialysisPrescriptions...
echo ------------------------------------------------------------
call :exec_sql "B02-DialysisPrescriptions.sql" 02

echo.
echo [B03] HemodialysisRecords...
echo ------------------------------------------------------------
call :exec_sql "B03-HemodialysisRecords.sql" 03

echo.
echo %B%============================================================%W%
if %TOTAL_ERRORS% equ 0 (
    echo   RESULT: %G%[SUCCESS] All B01/B02/B03 scripts passed.%W%
) else (
    echo   RESULT: %R%[FAILED] Found %TOTAL_ERRORS% SQL error^(s^).%W%
)
echo %B%============================================================%W%
if exist psql_log_b_01.tmp del psql_log_b_01.tmp
if exist psql_log_b_02.tmp del psql_log_b_02.tmp
if exist psql_log_b_03.tmp del psql_log_b_03.tmp

echo Process finished at %TIME%
echo Press any key to exit this window...
pause >nul
goto :eof

:exec_sql
set "FILE_NAME=%~1"
set "LOG_ID=%~2"
if "%LOG_ID%"=="" set "LOG_ID=run"
set /p ="  ^> Executing: %FILE_NAME% ... " <nul

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

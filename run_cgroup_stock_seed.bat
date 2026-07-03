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
echo   %Y%HEMODIALYSIS PRO - C-group Stock seed%W%
echo %B%============================================================%W%
echo   Order: %Y%C01 Equipments%W% ^> %Y%C02 MedicalSupplies%W% ^> %Y%C03 AutoStock (EQ)%W% ^> %Y%C04 AutoStock (MS)%W%
echo   (run after A-group core seed)
echo %B%============================================================%W%

SET "TOTAL_ERRORS=0"

echo.
echo [C01] Equipments...
echo ------------------------------------------------------------
call :exec_sql "C01-Equipments.sql" 01

echo.
echo [C02] MedicalSupplies...
echo ------------------------------------------------------------
call :exec_sql "C02-MedicalSupplies.sql" 02

echo.
echo [C03] AutoStock Equipments...
echo ------------------------------------------------------------
call :exec_sql "C03-AutoStock-Equipments.sql" 03

echo.
echo [C04] AutoStock MedicalSupplies...
echo ------------------------------------------------------------
call :exec_sql "C04-AutoStock-MedicalSupplies.sql" 04

echo.
echo %B%============================================================%W%
if %TOTAL_ERRORS% equ 0 (
    echo   RESULT: %G%[SUCCESS] All C-group scripts passed.%W%
) else (
    echo   RESULT: %R%[FAILED] Found %TOTAL_ERRORS% SQL error^(s^).%W%
)
echo %B%============================================================%W%
if exist psql_log_c_01.tmp del psql_log_c_01.tmp
if exist psql_log_c_02.tmp del psql_log_c_02.tmp
if exist psql_log_c_03.tmp del psql_log_c_03.tmp
if exist psql_log_c_04.tmp del psql_log_c_04.tmp

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

docker exec -i %CONTAINER_NAME% psql -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 < "%FILE_NAME%" > "psql_log_c_%LOG_ID%.tmp" 2>&1

if %errorlevel% equ 0 (
    echo %G%[PASS]%W%
) else (
    echo %R%[!!!! FAIL !!!!]%W%
    echo %R%------------------------------------------------------------%W%
    type "psql_log_c_%LOG_ID%.tmp"
    echo %R%------------------------------------------------------------%W%
    SET /a TOTAL_ERRORS+=1
)
goto :eof

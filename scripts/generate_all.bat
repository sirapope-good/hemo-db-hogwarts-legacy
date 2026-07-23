@echo off
SETLOCAL EnableDelayedExpansion
cd /d "%~dp0.."

set "SPAN=today"
set "DRY="
set "SKIP_POST="
set "FORCE_B01="

:parse_args
if "%~1"=="" goto run
if /I "%~1"=="--span" (
    set "SPAN=%~2"
    shift
    shift
    goto parse_args
)
if /I "%~1"=="--dry-run" (
    set "DRY=--dry-run"
    shift
    goto parse_args
)
if /I "%~1"=="--skip-post-steps" (
    set "SKIP_POST=--skip-post-steps"
    shift
    goto parse_args
)
if /I "%~1"=="--force-b01" (
    set "FORCE_B01=--force-b01"
    shift
    goto parse_args
)
if /I "%~1"=="--help" goto help
echo Unknown option: %~1
goto help

:help
echo.
echo Usage: scripts\generate_all.bat [options]
echo.
echo   --span today^|2m^|4m^|6m     default: today
echo   --dry-run                   summarize only, do not write SQL
echo   --skip-post-steps           skip patch B03 / rebuild B05 / B04-all
echo   --force-b01                 rewrite B01 for every patient
echo.
echo Next step after generate: scripts\seed_b.bat
echo.
exit /b 0

:run
echo ============================================================
echo   HEMO - Generate B01-B07 for ALL patients (seeds/a_core/05-Patients.sql)
echo   span=%SPAN%  dry_run=%DRY%  skip_post=%SKIP_POST%
echo ============================================================
echo.

python generate_patient_dialysis.py --generate-all --span %SPAN% %DRY% %SKIP_POST% %FORCE_B01%
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo [FAILED] exit code %RC%
    exit /b %RC%
)

echo [OK] generate-all completed.
if defined DRY (
    echo dry-run only — no files written
) else (
    echo Next: scripts\seed_b.bat
)
exit /b 0

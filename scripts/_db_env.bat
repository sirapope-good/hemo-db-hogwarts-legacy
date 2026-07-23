@echo off
REM Shared DB connection defaults for seed scripts.
REM Override via environment or copy db.env.bat.example -> db.env.bat

if exist "%~dp0db.env.bat" call "%~dp0db.env.bat"

if not defined HEMO_DB_CONTAINER set "HEMO_DB_CONTAINER=db"
if not defined HEMO_DB_USER set "HEMO_DB_USER=postgres"
if not defined HEMO_DB_NAME set "HEMO_DB_NAME=hemopro-local"
if not defined PGPASSWORD set "PGPASSWORD=your_password_here"

set "CONTAINER_NAME=%HEMO_DB_CONTAINER%"
set "DB_USER=%HEMO_DB_USER%"
set "DB_NAME=%HEMO_DB_NAME%"

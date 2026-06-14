@echo off
REM Build submitted_v42.zip (V4.2 rank-6 logic, does not touch submitted_v4.zip)
REM Usage: make_submitted_v42_zip.bat

uv run python scripts/build_v42_zip.py
if errorlevel 1 exit /b 1

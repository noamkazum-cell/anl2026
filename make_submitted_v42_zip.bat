@echo off
REM Build drafts/submitted_v42.zip (frozen V4.2 A/B snapshot)
REM Usage: make_submitted_v42_zip.bat

uv run python scripts/build_v42_zip.py
if errorlevel 1 exit /b 1

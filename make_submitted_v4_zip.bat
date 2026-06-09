@echo off
REM Build submitted_v4.zip (does not overwrite submitted.zip)
REM Usage: make_submitted_v4_zip.bat

uv run python scripts/build_submission_zip.py --source agent360_submit_v4.py --output submitted_v4.zip
if errorlevel 1 exit /b 1

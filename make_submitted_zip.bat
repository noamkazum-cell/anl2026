@echo off
REM Build submitted.zip: agent360_submit.py packaged as agent360.py + requirements.txt
REM Usage: make_submitted_zip.bat

uv run python scripts/build_submission_zip.py
if errorlevel 1 exit /b 1

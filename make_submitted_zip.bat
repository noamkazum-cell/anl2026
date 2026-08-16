@echo off
REM Build drafts/submitted.zip from legacy V3 source
REM Usage: make_submitted_zip.bat

uv run python scripts/build_submission_zip.py --source drafts/agent360_submit.py --output drafts/submitted.zip
if errorlevel 1 exit /b 1

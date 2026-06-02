@echo off
REM Minimal ANL 2026 work-in-progress submission zip (Agent360 only).
REM
REM Includes ONLY what the competition server needs to load your agent:
REM   - agent360.py   (module: agent360, class: Agent360)
REM   - requirements.txt
REM
REM Does NOT include experimental variants, scripts, docs, tests, or dev files.
REM For a full local backup use make_submission.bat instead.
REM
REM Usage: make_submitted_zip.bat

set OUTPUT=submitted.zip

if exist %OUTPUT% del %OUTPUT%

echo Creating %OUTPUT% (agent360.py + requirements.txt)...
echo.

powershell -Command "$ProgressPreference = 'SilentlyContinue'; Compress-Archive -Path 'agent360.py','requirements.txt' -DestinationPath '%OUTPUT%' -Force"

if exist %OUTPUT% (
    echo.
    echo Created %OUTPUT%
    echo Contents:
    tar -tf %OUTPUT%
    echo.
    echo Upload this zip on the ANL submission form.
    echo   Agent Module: agent360
    echo   Agent Class:  Agent360
) else (
    echo ERROR: Failed to create %OUTPUT%
    exit /b 1
)

#!/usr/bin/env bash
# Build drafts/submitted.zip from legacy V3 source
set -euo pipefail
uv run python scripts/build_submission_zip.py --source drafts/agent360_submit.py --output drafts/submitted.zip

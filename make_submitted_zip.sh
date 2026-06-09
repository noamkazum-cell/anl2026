#!/bin/bash
# Build submitted.zip: agent360_submit.py packaged as agent360.py + requirements.txt
# Usage: ./make_submitted_zip.sh

set -e
uv run python scripts/build_submission_zip.py

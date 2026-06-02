#!/bin/bash
# Minimal ANL 2026 work-in-progress submission zip (Agent360 only).
#
# Includes ONLY what the competition server needs:
#   - agent360.py
#   - requirements.txt
#
# Usage: ./make_submitted_zip.sh

set -e

OUTPUT="submitted.zip"
rm -f "$OUTPUT"

echo "Creating $OUTPUT (agent360.py + requirements.txt)..."
zip "$OUTPUT" agent360.py requirements.txt

echo ""
echo "Created $OUTPUT"
echo "Contents:"
unzip -l "$OUTPUT"
echo ""
echo "Upload on the ANL submission form:"
echo "  Agent Module: agent360"
echo "  Agent Class:  Agent360"

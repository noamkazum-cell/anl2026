#!/usr/bin/env python3
"""Build submitted_v42.zip from frozen V4.2 snapshot (rank-6 logic)."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "agent360_submit_v42.py"
OUTPUT = ROOT / "submitted_v42.zip"
REQUIREMENTS = ROOT / "requirements.txt"

UPLOAD_HEADER = '''"""Agent360 — ANL 2026 submission (V4.2 as ``Agent360``).

Packaged as ``agent360.py`` in ``submitted_v42.zip``.
Same negotiation logic as tournament #19055 (rank 6).
"""

'''


def payload_from_v42() -> str:
    raw = SOURCE.read_text(encoding="utf-8")
    start = raw.index("from __future__ import annotations")
    body = raw[start:]
    if not body.startswith("from __future__ import annotations"):
        raise ValueError("unexpected V4.2 file layout")
    body = body.replace(
        "from __future__ import annotations\n\nimport random",
        'from __future__ import annotations\n\n__version__ = "4.2.0"\n\nimport random',
        1,
    )
    return UPLOAD_HEADER + body


def main() -> int:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing {SOURCE}")
    if not REQUIREMENTS.is_file():
        raise SystemExit(f"Missing {REQUIREMENTS}")

    payload = payload_from_v42()
    if "_should_stall_accept" in payload:
        raise SystemExit("V4.2 source unexpectedly contains stall-accept code")

    if OUTPUT.exists():
        OUTPUT.unlink()

    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("agent360.py", payload)
        zf.writestr("requirements.txt", REQUIREMENTS.read_text(encoding="utf-8"))

    print(f"Created {OUTPUT}")
    with zipfile.ZipFile(OUTPUT) as zf:
        for name in zf.namelist():
            print(f"  {name}")
    print()
    print("Upload on the ANL submission form:")
    print("  Agent Module: agent360")
    print("  Agent Class:  Agent360")
    print("  Version label on portal: 4.2.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build submission zip from a self-contained submit module (packaged as agent360.py)."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "agent360_submit.py"
DEFAULT_OUTPUT = ROOT / "submitted.zip"
REQUIREMENTS = ROOT / "requirements.txt"


def build_submission_zip(
    source: Path = DEFAULT_SOURCE,
    output: Path = DEFAULT_OUTPUT,
) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"Missing submission source: {source}")
    if not REQUIREMENTS.is_file():
        raise FileNotFoundError(f"Missing requirements: {REQUIREMENTS}")

    payload = source.read_text(encoding="utf-8")
    if output.exists():
        output.unlink()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("agent360.py", payload)
        zf.writestr("requirements.txt", REQUIREMENTS.read_text(encoding="utf-8"))

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Submit module path (default: {DEFAULT_SOURCE.name})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output zip path (default: {DEFAULT_OUTPUT.name})",
    )
    args = parser.parse_args()
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output

    out = build_submission_zip(source=source, output=output)
    print(f"Created {out}")
    with zipfile.ZipFile(out) as zf:
        for name in zf.namelist():
            print(f"  {name}")
    print()
    print("Upload on the ANL submission form:")
    print("  Agent Module: agent360")
    print("  Agent Class:  Agent360")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

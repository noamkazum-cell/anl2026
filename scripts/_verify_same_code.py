#!/usr/bin/env python3
"""Verify V4.6 zip == V4.2 logic (rank-6 code)."""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def strip_meta(text: str) -> str:
    lines = []
    skip_doc = False
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.strip().startswith('"""'):
            if line.count('"""') >= 2:
                continue
            skip_doc = True
            continue
        if skip_doc:
            if '"""' in line:
                skip_doc = False
            continue
        if line.startswith("__version__"):
            continue
        lines.append(line)
    return "\n".join(lines)


def main() -> None:
    v4 = strip_meta((ROOT / "agent360_FINAL.py").read_text(encoding="utf-8"))
    v42 = strip_meta((ROOT / "drafts" / "agent360_submit_v42.py").read_text(encoding="utf-8"))
    zip_t = strip_meta(
        zipfile.ZipFile(ROOT / "submitted_v4.zip").read("agent360.py").decode()
    )
    v45 = (ROOT / "drafts" / "agent360_submit_v45.py").read_text(encoding="utf-8")

    h4 = hashlib.sha256(v4.encode()).hexdigest()
    h42 = hashlib.sha256(v42.encode()).hexdigest()
    hz = hashlib.sha256(zip_t.encode()).hexdigest()

    print("Logic hash v4.6 (submit):", h4[:20])
    print("Logic hash v4.2 (frozen): ", h42[:20])
    print("Logic hash zip:           ", hz[:20])
    print()
    print("v4.6 == v4.2 logic:", v4 == v42)
    print("zip  == v4.6 logic:", zip_t == v4)
    print("zip has stall-accept:", "_should_stall_accept" in zip_t)
    print("v45 has stall-accept: ", "_should_stall_accept" in v45)


if __name__ == "__main__":
    main()

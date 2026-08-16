#!/usr/bin/env python3
import difflib
from pathlib import Path

def strip_header(text: str) -> str:
    lines = []
    in_doc = False
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.strip().startswith('"""'):
            if line.count('"""') >= 2:
                continue
            in_doc = True
            continue
        if in_doc:
            if '"""' in line:
                in_doc = False
            continue
        if line.startswith("__version__"):
            continue
        lines.append(line)
    return "\n".join(lines)

a = strip_header(Path("agent360_FINAL.py").read_text(encoding="utf-8"))
b = strip_header(Path("drafts/agent360_submit_v42.py").read_text(encoding="utf-8"))
if a == b:
    print("IDENTICAL: V4.6 submission logic == frozen V4.2")
else:
    diff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))
    print(f"DIFFER: {len(diff)} diff lines")
    for line in diff[:30]:
        print(line)

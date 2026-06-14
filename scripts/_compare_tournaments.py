#!/usr/bin/env python3
"""Compare Agent360 rows across tournaments in saved HTML."""
import re
import sys
from pathlib import Path

html = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
tids = sys.argv[2:] if len(sys.argv) > 2 else ["19043", "19041", "19036", "19038"]

labels = [
    "rank", "score", "min", "q1", "median", "q3", "max",
    "mean", "std", "time_ms", "self_exc", "partner_exc", "negs",
]

for tid in tids:
    parts = html.split(f"Tournament {tid} Results")
    if len(parts) < 2:
        print(f"=== {tid}: not found ===")
        continue
    chunk = parts[1][:120000]
    row = re.search(r"Agent360[^<]*</td>(.*?)</tr>", chunk, re.DOTALL)
    print(f"=== Tournament {tid} ===")
    if not row:
        print("  Agent360 row not found")
        continue
    cells = re.findall(r'align="right">\s*([^<]+?)\s*</td>', row.group(0))
    for i, c in enumerate(cells[: len(labels)]):
        print(f"  {labels[i]:12} {c.strip().replace(',', '')}")
    print(f"  all_cells    {cells}")
    print()

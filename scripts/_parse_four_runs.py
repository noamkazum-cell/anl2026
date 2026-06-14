#!/usr/bin/env python3
"""Parse the four latest tournament HTML exports."""
from __future__ import annotations

import re
from pathlib import Path

FILES = [
    ("last", Path(r"C:\Users\noamk\Downloads\new anl results\last.html")),
    ("one before last", Path(r"C:\Users\noamk\Downloads\new anl results\one before last.html")),
    ("2 before last", Path(r"C:\Users\noamk\Downloads\new anl results\2 before last.html")),
    ("3 before last", Path(r"C:\Users\noamk\Downloads\new anl results\3 before last.html")),
]


def parse_file(label: str, path: Path) -> None:
    html = path.read_text(encoding="utf-8", errors="replace")
    tid_m = re.search(r"Tournament (\d+) Results", html)
    tid = tid_m.group(1) if tid_m else "?"

    def time_cell(name: str) -> str:
        m = re.search(
            rf">{name}</td>\s*<td>(?:<time[^>]*datetime=\"([^\"]+)\"[^>]*class=\"local-time\">([^<]*)</time>|([^<]*))</td>",
            html,
        )
        if not m:
            return "-"
        return (m.group(2) or m.group(1) or m.group(3) or "").strip() or m.group(1) or "-"

    comps = re.search(r">N\. Competitors</td>\s*<td>(\d+)", html)
    configs = re.search(r">N\. Configs</td>\s*<td>(\d+)", html)
    negs = re.search(r">N\. Negotiations</td>\s*<td>(\d+)", html)

    a360 = re.search(
        r"<tr><td>(Agent360:[^<]+)</td>(.*?)</tr>",
        html,
        re.DOTALL,
    )
    print(f"\n=== {label} -> Tournament #{tid} ===")
    print(f"  Downloaded: {time_cell('Downloaded')}")
    print(f"  Started:    {time_cell('Started')}")
    print(f"  Ended:      {time_cell('Ended')}")
    print(
        f"  Panel: {configs.group(1) if configs else '?'} configs, "
        f"{comps.group(1) if comps else '?'} competitors, "
        f"{negs.group(1) if negs else '?'} negotiations"
    )
    if a360:
        cells = re.findall(r'align="right">([^<]+)', a360.group(2))
        keys = ["rank", "score", "min", "q1", "median", "q3", "max", "mean", "std", "time_ms", "negs"]
        stats = dict(zip(keys, [c.strip() for c in cells]))
        print(f"  Version: {a360.group(1)}")
        print(
            f"  Rank {stats.get('rank')} | Score {stats.get('score')} | "
            f"Min {stats.get('min')} | Q1 {stats.get('q1')} | Median {stats.get('median')} | "
            f"Std {stats.get('std')}"
        )

    # upload history snippet if present
    uploads = re.findall(
        r"<td class=\"text-right\">(\d+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>",
        html,
    )
    if uploads:
        print("  Upload history (from page):")
        for num, utc, local in uploads[:8]:
            print(f"    #{num}: {local.strip()} ({utc.strip()})")


for label, path in FILES:
    if path.is_file():
        parse_file(label, path)
    else:
        print(f"MISSING: {path}")

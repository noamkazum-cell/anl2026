#!/usr/bin/env python3
"""Extract Agent360 tournament timeline from saved ANAC HTML."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def extract(path: Path) -> list[dict[str, str]]:
    html = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"Tournament (\d+) Results", html)
    rows: list[dict[str, str]] = []
    for tid, chunk in zip(parts[1::2], parts[2::2]):
        def cell(label: str) -> str:
            m = re.search(
                rf">{label}</td>\s*<td>(?:<time[^>]*datetime=\"([^\"]+)\"[^>]*>)?"
                rf"([^<]*)",
                chunk,
            )
            if not m:
                return ""
            return (m.group(1) or m.group(2)).strip()

        a360 = re.search(
            r"<tr><td>(Agent360:[^<]+)</td>\s*"
            r"<td align=\"right\">(\d+)</td>\s*"
            r"<td align=\"right\">([^<]+)</td>",
            chunk,
        )
        if not a360:
            continue
        rows.append(
            {
                "tid": tid,
                "version": a360.group(1),
                "rank": a360.group(2),
                "score": a360.group(3).strip(),
                "downloaded": cell("Downloaded"),
                "started": cell("Started"),
                "completed": cell("Completed"),
                "agents": cell("Agents") or re.search(r">Agents</td>\s*<td>(\d+)", chunk).group(1) if re.search(r">Agents</td>\s*<td>(\d+)", chunk) else "",
                "scenarios": cell("Scenarios") or (re.search(r">Scenarios</td>\s*<td>(\d+)", chunk).group(1) if re.search(r">Scenarios</td>\s*<td>(\d+)", chunk) else ""),
            }
        )
    return rows


def main() -> int:
    paths = sys.argv[1:] or [
        str(Path.home() / "Downloads" / "anl v4 results.html"),
        str(Path.home() / "Downloads" / "anl v42 results 2.html"),
    ]
    for path_str in paths:
        path = Path(path_str)
        if not path.is_file():
            print(f"MISSING {path}")
            continue
        print(f"\n=== {path.name} ===")
        print(f"{'TID':>6} {'version':<22} {'rank':>4} {'score':>10}  completed / downloaded")
        for r in extract(path):
            when = r["completed"] or r["downloaded"] or r["started"]
            panel = f"{r['scenarios']}sc/{r['agents']}ag" if r["scenarios"] else ""
            print(
                f"{r['tid']:>6} {r['version']:<22} {r['rank']:>4} {r['score']:>10}  "
                f"{when}  {panel}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

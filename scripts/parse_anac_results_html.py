#!/usr/bin/env python3
"""Parse saved ANAC tournament results HTML export."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROW_RE = re.compile(
    r"<tr><td>([^<]+)</td>\s*<td align=\"right\">(\d+)</td>\s*<td align=\"right\">([^<]+)</td>"
)


def _row_stats(chunk: str, name_prefix: str) -> dict[str, str] | None:
    m = re.search(
        r"<tr><td>(" + re.escape(name_prefix) + r"[^<]*)</td>(.*?)</tr>",
        chunk,
        re.DOTALL,
    )
    if not m:
        return None
    cells = re.findall(r'align="right">\s*([^<]+?)\s*</td>', m.group(0))
    keys = [
        "rank",
        "score",
        "min",
        "q1",
        "median",
        "q3",
        "max",
        "mean",
        "std",
        "time_ms",
        "self_exc",
        "partner_exc",
        "negs",
    ]
    return dict(zip(keys, [c.strip().replace(",", "") for c in cells]))


def compare_19035(path: Path) -> None:
    html = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"Tournament (\d+) Results", html)
    chunk = dict(zip(parts[1::2], parts[2::2])).get("19035")
    if not chunk:
        return
    names = [
        "Agent360",
        "AgentNexus_20",
        "ChangAgent",
        "swingv2",
        "DecepTor",
        "DefaultAgent",
        "GroupN",
        "NashtyNegotiator6",
    ]
    print("=== 19035 distribution comparison ===")
    header = "agent                rank   score      min       q1   median    std  p_exc"
    print(header)
    for name in names:
        r = _row_stats(chunk, name)
        if not r:
            continue
        print(
            f"{name:20} {int(r['rank']):4d} "
            f"{float(r['score']):8.0f} {float(r['min']):8.0f} "
            f"{float(r['q1']):8.0f} {float(r['median']):8.0f} "
            f"{float(r['std']):6.0f} {r['partner_exc']:>5}"
        )


def parse(path: Path) -> None:
    html = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"Tournament (\d+) Results", html)
    tids = parts[1::2]
    chunks = parts[2::2]

    for tid, chunk in zip(tids, chunks):
        rows = ROW_RE.findall(chunk)
        if not rows:
            continue
        a360 = [r for r in rows if "Agent360" in r[0]]
        print(f"=== Tournament {tid} ===")
        print("Top 5:")
        for name, rank, score in rows[:5]:
            short = name.split(":")[0]
            print(f"  #{rank} {short}: {score}")
        for name, rank, score in a360:
            m = re.search(
                re.escape(name) + r"</td>(.*?)</tr>", chunk, re.DOTALL
            )
            detail = ""
            if m:
                cells = re.findall(r'align="right">([^<]+)', m.group(1))
                if len(cells) >= 12:
                    detail = (
                        f" min={cells[1]} Q1={cells[2]} median={cells[3]}"
                        f" std={cells[7]} partner_exc={cells[11]}"
                    )
            print(f"  >>> Agent360 #{rank} score {score}{detail}")
        print()


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "anl v3 results.html"
    parse(path)
    print()
    compare_19035(path)

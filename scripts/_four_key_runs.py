#!/usr/bin/env python3
import re
from pathlib import Path

html = Path(r"C:\Users\noamk\Downloads\new anl results\last.html").read_text(
    encoding="utf-8", errors="replace"
)
parts = re.split(r"Tournament (\d+) Results", html)
chunks = dict(zip(parts[1::2], parts[2::2]))

print("UPLOAD TIMELINE (from screenshot):")
uploads = [
    ("#7", "2026-06-09 23:15:50 UTC", "06/10/2026 02:15:50 AM", "V4.6 restore"),
    ("#6", "2026-06-09 13:57:55 UTC", "06/09/2026 04:57:55 PM", "V4.5 stall-accept"),
    ("#5", "2026-06-08 18:26:56 UTC", "06/08/2026 09:26:56 PM", "likely V4.3/V4.2"),
]
for u in uploads:
    print(f"  {u[0]}: {u[2]} ({u[1]}) -> {u[3]}")

print()
for tid in ["19077", "19074", "19055", "19047"]:
    chunk = chunks.get(tid, "")
    a = re.search(r"<tr><td>(Agent360:[^<]+)</td>(.*?)</tr>", chunk, re.DOTALL)
    dl = re.search(
        r"Downloaded</td>\s*<td>(?:<time[^>]*datetime=\"([^\"]+)\"[^>]*class=\"local-time\">([^<]*)</time>|([^<]*))",
        chunk,
    )
    end = re.search(
        r">Ended</td>\s*<td><time datetime=\"([^\"]+)\"[^>]*class=\"local-time\">([^<]*)</time>",
        chunk,
    )
    cfg = re.search(r">N\. Configs</td>\s*<td>(\d+)", chunk)
    cmp_ = re.search(r">N\. Competitors</td>\s*<td>(\d+)", chunk)
    neg = re.search(r">N\. Negotiations</td>\s*<td>(\d+)", chunk)
    if not a:
        print(f"#{tid}: NO Agent360")
        continue
    cells = re.findall(r'align="right">([^<]+)', a.group(2))
    dl_s = (dl.group(2) or dl.group(1) or dl.group(3) or "-").strip() if dl else "-"
    print(f"#{tid} {a.group(1)}")
    print(f"  rank={cells[0]} score={cells[1]} min={cells[2]} q1={cells[3]} median={cells[4]} std={cells[8]}")
    print(
        f"  panel={cfg.group(1) if cfg else '?'}sc "
        f"{cmp_.group(1) if cmp_ else '?'}ag "
        f"negs={neg.group(1) if neg else '?'}"
    )
    print(f"  downloaded={dl_s} ended={end.group(2) if end else '-'}")
    print()

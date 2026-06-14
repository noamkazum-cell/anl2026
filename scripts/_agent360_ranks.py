#!/usr/bin/env python3
import re
from pathlib import Path

path = Path(r"C:\Users\noamk\Downloads\anl v4 results.html")
html = path.read_text(encoding="utf-8", errors="replace")
parts = re.split(r"Tournament (\d+) Results", html)
for tid, chunk in zip(parts[1::2], parts[2::2]):
    m = re.search(
        r"<tr><td>(Agent360:[^<]+)</td>\s*<td align=\"right\">(\d+)</td>\s*<td align=\"right\">([^<]+)</td>",
        chunk,
    )
    if not m:
        continue
    comps = re.search(r">N\. Competitors</td>\s*<td>(\d+)", chunk)
    configs = re.search(r">N\. Configs</td>\s*<td>(\d+)", chunk)
    negs = re.search(r">N\. Negotiations</td>\s*<td>(\d+)", chunk)
    dl = re.search(r"Downloaded</td>\s*<td>(?:<time[^>]*datetime=\"([^\"]+)\"[^>]*>)?", chunk)
    end = re.search(r">Ended</td>\s*<td><time datetime=\"([^\"]+)\"", chunk)
    print(
        f"#{tid}: rank={m.group(2):>2} score={m.group(3):>10} ver={m.group(1)} "
        f"panel={configs.group(1) if configs else '?'}sc/{comps.group(1) if comps else '?'}ag "
        f"negs={negs.group(1) if negs else '?'} "
        f"dl={dl.group(1) if dl and dl.group(1) else '-'} "
        f"end={end.group(1) if end else '-'}"
    )

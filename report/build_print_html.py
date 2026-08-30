"""Build print-friendly HTML (large font, spaced, note lines) from oral MD files."""
from __future__ import annotations

from pathlib import Path

import markdown

REPORT = Path(__file__).resolve().parent

CSS = """
@page {
  size: A4;
  margin: 1.8cm 1.6cm 2cm 1.6cm;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "Segoe UI", "David", "Arial Hebrew", Arial, sans-serif;
  font-size: 18pt;
  line-height: 2.05;
  color: #111;
  max-width: 46rem;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
}
body.rtl { direction: rtl; text-align: right; }
body.ltr { direction: ltr; text-align: left; }
h1 {
  font-size: 28pt;
  line-height: 1.35;
  margin: 0 0 1.4rem;
  padding-bottom: 0.6rem;
  border-bottom: 3px solid #222;
}
h2 {
  font-size: 22pt;
  line-height: 1.4;
  margin: 2.6rem 0 1rem;
  padding-top: 0.4rem;
  page-break-after: avoid;
}
h3 {
  font-size: 18pt;
  line-height: 1.45;
  margin: 2.2rem 0 0.85rem;
  page-break-after: avoid;
}
p {
  margin: 0 0 1.35rem;
}
ul, ol {
  margin: 0 0 1.6rem;
  padding-inline-start: 1.6rem;
}
li {
  margin: 0 0 0.85rem;
  padding-inline-start: 0.25rem;
}
strong { font-weight: 700; }
hr {
  border: none;
  border-top: 1.5px dashed #bbb;
  margin: 2.2rem 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 1.8rem;
  font-size: 16pt;
  line-height: 1.7;
}
th, td {
  border: 1px solid #888;
  padding: 0.55rem 0.7rem;
  vertical-align: top;
}
th { background: #f0f0f0; }
code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.88em;
  background: #f3f3f3;
  padding: 0.05em 0.25em;
}
.meta {
  font-size: 15pt;
  line-height: 1.85;
  margin-bottom: 1.8rem;
  padding: 0.9rem 1rem;
  background: #f7f7f7;
  border: 1px solid #ddd;
}
.print-hint {
  font-size: 13pt;
  line-height: 1.5;
  color: #444;
  margin: 0 0 1.8rem;
  padding: 0.7rem 0.9rem;
  border: 1px dashed #999;
}
.notes {
  margin: 0.4rem 0 2rem;
  padding: 0.35rem 0 0;
  min-height: 4.2rem;
  border-bottom: 1.5px dotted #999;
  page-break-inside: avoid;
}
.notes::before {
  content: "הערות: ";
  font-size: 12pt;
  color: #777;
  display: block;
  margin-bottom: 0.35rem;
}
body.ltr .notes::before { content: "Notes: "; }
.notes-tall {
  min-height: 6.5rem;
}
.block {
  margin-bottom: 0.5rem;
  page-break-inside: avoid;
}
@media print {
  body { padding: 0; max-width: none; }
  .print-hint { display: none; }
  a { color: inherit; text-decoration: none; }
  h2, h3 { page-break-after: avoid; }
}
"""


def md_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )


def inject_notes(html: str) -> str:
    """Add a handwritten-note strip after each h2/h3 section body."""
    import re

    # After each </h2> or </h3> ... until next h2/h3/hr/end: wrap and append notes
    parts: list[str] = []
    pattern = re.compile(r"(<h[23][^>]*>.*?</h[23]>)", re.DOTALL | re.IGNORECASE)
    tokens = pattern.split(html)
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if pattern.fullmatch(token):
            parts.append('<div class="block">')
            parts.append(token)
            # next chunk is content until next heading
            if i + 1 < len(tokens) and not pattern.fullmatch(tokens[i + 1]):
                content = tokens[i + 1]
                # stop content before a lone <hr /> that starts a new major break — keep hr outside
                parts.append(content)
                tall = " notes-tall" if token.lower().startswith("<h3") else ""
                parts.append(f'<div class="notes{tall}"></div>')
                parts.append("</div>")
                i += 2
            else:
                parts.append('<div class="notes"></div></div>')
                i += 1
        else:
            parts.append(token)
            i += 1
    return "".join(parts)


def build(md_path: Path, out_path: Path, rtl: bool) -> None:
    raw = md_path.read_text(encoding="utf-8")
    # Split title / meta lines (bold lines at top) for a clean header
    lines = raw.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else out_path.stem
    body_md = "\n".join(lines[1:]).lstrip("\n")
    html_body = inject_notes(md_to_html(body_md))
    direction = "rtl" if rtl else "ltr"
    lang = "he" if rtl else "en"
    hint = (
        "להדפסה: Ctrl+P → שמרו על שוליים רגילים / Default. מומלץ דו־צדדי. "
        "אחרי כל קטע יש קו מקווקו להערות ביד."
        if rtl
        else "Print with Ctrl+P. Note lines appear under each section for handwritten comments."
    )
    doc = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body class="{direction}">
  <p class="print-hint">{hint}</p>
  <h1>{title}</h1>
  {html_body}
</body>
</html>
"""
    out_path.write_text(doc, encoding="utf-8")
    print(f"Wrote {out_path}")


def main() -> None:
    jobs = [
        ("oral-5min-presentation-he.md", "oral-5min-presentation-he-print.html", True),
        ("oral-5min-qa-he.md", "oral-5min-qa-he-print.html", True),
        ("oral-5min-presentation.md", "oral-5min-presentation-print.html", False),
        ("oral-5min-qa.md", "oral-5min-qa-print.html", False),
    ]
    for src, dst, rtl in jobs:
        build(REPORT / src, REPORT / dst, rtl=rtl)


if __name__ == "__main__":
    main()

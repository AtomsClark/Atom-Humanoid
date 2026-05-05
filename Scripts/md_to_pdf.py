#!/usr/bin/env python3
"""
md_to_pdf.py — Convert a markdown file to a styled PDF.

Usage:
    python md_to_pdf.py <input.md> [output.pdf]

If output path is omitted, the PDF is saved alongside the input file.
"""

import sys
import os
import subprocess

def convert(md_path, pdf_path=None):
    if not os.path.exists(md_path):
        print(f"Error: file not found: {md_path}")
        sys.exit(1)

    if pdf_path is None:
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"

    with open(md_path) as f:
        md = f.read()

    try:
        import markdown
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown", "-q"])
        import markdown

    try:
        from weasyprint import HTML
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint", "-q"])
        from weasyprint import HTML

    html_body = markdown.markdown(md, extensions=["tables", "fenced_code"])

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: -apple-system, Arial, sans-serif;
    font-size: 11pt;
    max-width: 900px;
    margin: 40px auto;
    color: #222;
    line-height: 1.6;
  }}
  h1 {{
    font-size: 22pt;
    border-bottom: 2px solid #111;
    padding-bottom: 8px;
    margin-bottom: 6px;
  }}
  h2 {{
    font-size: 15pt;
    border-bottom: 1px solid #ccc;
    padding-bottom: 4px;
    margin-top: 32px;
    color: #111;
  }}
  h3 {{
    font-size: 12pt;
    margin-top: 22px;
    color: #444;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
    font-size: 10pt;
  }}
  th {{
    background: #1a1a1a;
    color: white;
    padding: 7px 12px;
    text-align: left;
  }}
  td {{
    padding: 6px 12px;
    border-bottom: 1px solid #e0e0e0;
  }}
  tr:nth-child(even) {{
    background: #f7f7f7;
  }}
  code {{
    background: #f0f0f0;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 9.5pt;
  }}
  hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 28px 0;
  }}
  ul, ol {{
    margin: 8px 0;
    padding-left: 24px;
  }}
  li {{
    margin: 4px 0;
  }}
  strong {{
    color: #111;
  }}
  p {{
    margin: 8px 0;
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=html, base_url="/").write_pdf(pdf_path)
    print(f"PDF written to {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    md_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else None
    convert(md_path, pdf_path)

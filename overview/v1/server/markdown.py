"""Safe Markdown rendering for untrusted reader content (stdlib only)."""
from __future__ import annotations

import html
import re


def render_markdown(text: str) -> str:
    lines = (text or "").splitlines()
    out: list[str] = []
    in_code = False
    in_list = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                if in_list:
                    out.append("</ul>")
                    in_list = False
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3 id=\"{heading_id(line[4:])}\">{html.escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2 id=\"{heading_id(line[3:])}\">{html.escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1 id=\"{heading_id(line[2:])}\">{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if line == "":
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        out.append("</ul>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def heading_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "section"


def outline_from_html(html_text: str) -> list[dict]:
    items: list[dict] = []
    for match in re.finditer(r"<h([23]) id=\"([^\"]+)\">([^<]+)</h\1>", html_text):
        items.append({"level": int(match.group(1)), "id": match.group(2), "title": match.group(3)})
    return items


def render_reader_content(text: str, *, collapsible_after: int = 36) -> dict:
    html_text = render_markdown(text)
    outline = outline_from_html(html_text)
    if len((text or "").splitlines()) >= collapsible_after and outline:
        html_text = collapse_sections(html_text)
    return {"html": html_text, "outline": outline}


def collapse_sections(html_text: str) -> str:
    parts = re.split(r"(?=<h2 id=)", html_text)
    if len(parts) <= 1:
        return html_text
    head, *sections = parts
    wrapped: list[str] = [head]
    for section in sections:
        if not section.strip():
            continue
        title_match = re.match(r"<h2 id=\"([^\"]+)\">([^<]+)</h2>", section)
        if not title_match:
            wrapped.append(section)
            continue
        section_id, title = title_match.groups()
        body = section[title_match.end():]
        wrapped.append(
            f"<details class=\"bp-md-section\" id=\"{section_id}\"><summary>{html.escape(title)}</summary><div>{body}</div></details>"
        )
    return "".join(wrapped)

"""PROCESS ## Glance extract for Map WO light list (pc-921).

List API stays light — never ship full description/card_html — but rows need
a short Glance so the left rail is not title-only for minutes after create.
"""

from __future__ import annotations

import re
from typing import Any

_GLANCE_HEAD = re.compile(
    r"(?im)^##\s*Glance\s*\n([\s\S]*?)(?=\n##\s|\n#\s[^#]|$)"
)
_WS = re.compile(r"\s+")


def extract_task_glance(description: Any, max_len: int = 160) -> str:
    """Return short Glance prose from a work-order description.

    Prefers ``## Glance`` body (PROCESS §5 Intake). Falls back to the first
    non-heading line for older tickets. Collapses whitespace; ellipsizes.
    """
    text = str(description or "").replace("\r\n", "\n").strip()
    if not text:
        return ""
    body = ""
    m = _GLANCE_HEAD.search(text)
    if m:
        body = m.group(1) or ""
    else:
        for line in text.split("\n"):
            s = line.strip()
            if not s:
                if body:
                    break
                continue
            if s.startswith("#"):
                if body:
                    break
                continue
            # Skip bare section markers / intake chrome
            if s.lower() in ("glance", "where", "done when", "detail"):
                continue
            body = s
            break
    body = _WS.sub(" ", body).strip()
    # Drop leading bullets for one-line rail
    body = re.sub(r"^[-*•]\s+", "", body)
    if not body:
        return ""
    if len(body) > max_len:
        cut = body[: max_len - 1].rstrip()
        # Prefer word boundary
        sp = cut.rfind(" ")
        if sp >= int(max_len * 0.6):
            cut = cut[:sp]
        body = cut.rstrip(".,;:") + "…"
    return body

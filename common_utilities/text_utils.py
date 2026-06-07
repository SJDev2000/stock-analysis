from __future__ import annotations

import html
import re


def strip_html(raw: str) -> str:
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"submitted by\s*/u/\S+.*$", "", text, flags=re.DOTALL).strip()
    return text

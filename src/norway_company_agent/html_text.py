"""Decode retained HTML consistently during extraction and offline evidence audit."""
from __future__ import annotations

import re
from bs4 import UnicodeDammit


def decode_html(body: bytes, content_type: str = "", encoding: str | None = None) -> tuple[str, str]:
    header = re.search(r"charset\s*=\s*[\"']?([^\s;\"']+)", content_type, re.I)
    hint = encoding or (header.group(1) if header else None)
    decoded = UnicodeDammit(body, known_definite_encodings=[hint] if hint else [], is_html=True)
    return decoded.unicode_markup or "", decoded.original_encoding or "utf-8"

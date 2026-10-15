"""Decode retained HTML consistently during extraction and offline evidence audit."""
from __future__ import annotations

import re
import gzip
import io
import zlib
from bs4 import UnicodeDammit

MAX_DECOMPRESSED_HTML_BYTES = 8_000_000


def decode_html(body: bytes, content_type: str = "", encoding: str | None = None) -> tuple[str, str]:
    # Some origins send gzip even without content negotiation. Retain and hash
    # the original response bytes; extraction and offline audit decode them in
    # exactly the same bounded way. Never feed compressed data to a text guesser.
    if body.startswith(b'\x1f\x8b'):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as compressed:
                body = compressed.read(MAX_DECOMPRESSED_HTML_BYTES + 1)
        except (OSError, EOFError, zlib.error) as exc:
            raise ValueError('Invalid compressed HTML') from exc
        if len(body) > MAX_DECOMPRESSED_HTML_BYTES:
            raise ValueError('Compressed HTML exceeds decoded byte limit')
    header = re.search(r"charset\s*=\s*[\"']?([^\s;\"']+)", content_type, re.I)
    hint = encoding or (header.group(1) if header else None)
    decoded = UnicodeDammit(body, known_definite_encodings=[hint] if hint else [], is_html=True)
    return decoded.unicode_markup or "", decoded.original_encoding or "utf-8"

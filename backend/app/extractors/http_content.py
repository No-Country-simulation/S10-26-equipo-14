"""Bounded HTTP content decoding for public store pages."""

from __future__ import annotations

import zlib

from app.extractors.base import ExtractionError


def decode_http_body(
    body: bytes,
    *,
    content_encoding: str | None,
    charset: str | None,
    max_bytes: int,
) -> str:
    """Decode identity, gzip, or zlib-wrapped deflate responses within a size cap."""
    if len(body) > max_bytes:
        raise ExtractionError("UNSUPPORTED: respuesta demasiado grande.")

    decoded = body
    encodings = [
        item.strip().lower()
        for item in (content_encoding or "identity").split(",")
        if item.strip() and item.strip().lower() != "identity"
    ]
    for encoding in reversed(encodings):
        if encoding in {"gzip", "x-gzip"}:
            window_bits = zlib.MAX_WBITS | 16
        elif encoding == "deflate":
            window_bits = zlib.MAX_WBITS
        else:
            raise ExtractionError("UNSUPPORTED: codificación HTTP no admitida.")
        try:
            decompressor = zlib.decompressobj(window_bits)
            decoded = decompressor.decompress(decoded, max_bytes + 1)
            if len(decoded) > max_bytes or decompressor.unconsumed_tail:
                raise ExtractionError("UNSUPPORTED: respuesta descomprimida demasiado grande.")
            if not decompressor.eof or decompressor.unused_data:
                raise ExtractionError("UNSUPPORTED: respuesta comprimida incompleta o ambigua.")
            tail = decompressor.flush(max_bytes + 1 - len(decoded))
            decoded += tail
        except zlib.error as exc:
            raise ExtractionError("UNSUPPORTED: respuesta comprimida inválida.") from exc
        if len(decoded) > max_bytes:
            raise ExtractionError("UNSUPPORTED: respuesta descomprimida demasiado grande.")

    try:
        return decoded.decode(charset or "utf-8", errors="replace")
    except LookupError as exc:
        raise ExtractionError("UNSUPPORTED: codificación de texto no reconocida.") from exc

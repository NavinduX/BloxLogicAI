"""
QR code generation and scanning for tea-batch traceability (FR10).

Encodes the batch's full recorded journey as human-readable text -- not just
the batch ID. Scanning the QR with any phone camera or QR app shows every
stage (location, details) immediately, with zero dependency on this app or a
network connection (NFR1). The payload still ends with the batch ID so a
viewer who wants the cryptographic VALID/TAMPERED integrity check can search
it in the BloxLogicAI app afterward. Rendered in-memory only; nothing is
written to disk.

Payload text is ASCII-sanitized before encoding: some QR encoder/decoder
implementations mis-round-trip non-ASCII bytes (e.g. "°") by misinterpreting
them as Kanji-mode segments, corrupting the scanned result. Sticking to ASCII
keeps every scanner -- ours and third-party phone apps -- reading the exact
text that was encoded.
"""

from __future__ import annotations

import io
import re
import unicodedata

import qrcode

_TRACE_HEADER_RE = re.compile(r"^TEA BATCH TRACE - (\S+)", re.MULTILINE)


def batch_qr_payload(batch_id: str) -> str:
    """Canonical, normalized batch ID (uppercased, trimmed)."""
    return batch_id.upper().strip()


def _ascii_safe(text: str) -> str:
    """Best-effort transliteration to plain ASCII (drops accents/symbols QR round-trip poorly)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def format_batch_trace(batch_id: str, blocks: list[dict]) -> str:
    """Human-readable full batch journey -- the text actually encoded into the QR.

    Timestamps are omitted to keep the payload short and reliably scannable --
    they're already visible in the app's timeline view.
    """
    bid = batch_qr_payload(batch_id)
    lines = [f"TEA BATCH TRACE - {bid}", ""]
    for blk in blocks:
        lines.append(f"{blk['seq']}. {_ascii_safe(blk['stage'])}")
        lines.append(f"   Location: {_ascii_safe(blk['location'])}")
        lines.append(f"   Details: {_ascii_safe(blk['details'])}")
        lines.append("")
    lines.append(f"Verify chain integrity: search '{bid}' in the BloxLogicAI app.")
    return "\n".join(lines)


def extract_batch_id(payload_text: str) -> str | None:
    """Pull the batch ID back out of a scanned `format_batch_trace()` payload.

    Returns None if `payload_text` doesn't look like a BloxLogicAI batch QR
    (e.g. an unrelated QR code was scanned).
    """
    match = _TRACE_HEADER_RE.search(payload_text or "")
    return match.group(1) if match else None


def generate_qr_png_bytes(data: str, box_size: int = 12, border: int = 2) -> bytes:
    """Render `data` as a QR code and return raw PNG bytes."""
    img = qrcode.make(data, box_size=box_size, border=border)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def decode_qr_image(image_bytes: bytes) -> str | None:
    """Decode the first QR code found in an image (e.g. a camera snapshot).

    Returns the decoded text, or None if no QR code was detected. Imports
    pyzbar lazily so the (optional, camera-only) scanning path doesn't cost
    startup time or the extra dependency on the plain generate/display path.
    """
    from PIL import Image
    from pyzbar.pyzbar import decode as zbar_decode

    image = Image.open(io.BytesIO(image_bytes))
    results = zbar_decode(image)
    if not results:
        return None
    return results[0].data.decode("utf-8", errors="replace")

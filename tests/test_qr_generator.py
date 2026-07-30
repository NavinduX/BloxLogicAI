"""
Tests for blockchain/qr_generator.py — payload formatting, PNG output, and the
generate -> scan -> decode -> extract round trip used by the in-app QR scanner.
"""

from __future__ import annotations

from blockchain.qr_generator import (
    batch_qr_payload,
    decode_qr_image,
    extract_batch_id,
    format_batch_trace,
    generate_qr_png_bytes,
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

SAMPLE_BLOCKS = [
    {
        "batch_id": "TEA001",
        "seq": 1,
        "stage": "Harvested",
        "location": "Nuwara Eliya Estate",
        "details": "2,500 kg Orthodox Black Tea harvested; leaf grade: BOP",
        "timestamp": "2026-01-05T08:00:00",
        "previous_hash": "0" * 16,
        "current_hash": "a" * 64,
    },
    {
        "batch_id": "TEA001",
        "seq": 2,
        "stage": "Processed",
        "location": "Tea Factory A, Nuwara Eliya",
        "details": "Withered 18h; CTC rolled; dried at 90°C; moisture 3.4%",
        "timestamp": "2026-01-07T10:30:00",
        "previous_hash": "a" * 64,
        "current_hash": "b" * 64,
    },
]


def test_generate_qr_png_bytes_is_valid_png():
    data = generate_qr_png_bytes("TEA001")
    assert data.startswith(PNG_MAGIC)


def test_batch_qr_payload_normalizes_case_and_whitespace():
    assert batch_qr_payload(" tea001 ") == "TEA001"


def test_format_batch_trace_includes_every_stage_detail():
    text = format_batch_trace("tea001", SAMPLE_BLOCKS)
    assert "TEA001" in text
    assert "Harvested" in text
    assert "Nuwara Eliya Estate" in text
    assert "2,500 kg Orthodox Black Tea harvested; leaf grade: BOP" in text
    assert "Processed" in text
    assert "Tea Factory A, Nuwara Eliya" in text


def test_format_batch_trace_ascii_sanitizes_non_ascii_characters():
    # Non-ASCII bytes (e.g. "°") round-trip incorrectly through some QR
    # encoder/decoder implementations (mis-detected as Kanji-mode segments),
    # so the payload is transliterated to plain ASCII before encoding.
    text = format_batch_trace("TEA001", SAMPLE_BLOCKS)
    assert "°" not in text
    assert "90C" in text
    assert text.isascii()


def test_format_batch_trace_omits_timestamps():
    text = format_batch_trace("TEA001", SAMPLE_BLOCKS)
    for blk in SAMPLE_BLOCKS:
        assert blk["timestamp"] not in text
        assert blk["timestamp"].replace("T", " ") not in text


def test_format_batch_trace_renders_as_valid_qr_png():
    text = format_batch_trace("TEA001", SAMPLE_BLOCKS)
    data = generate_qr_png_bytes(text)
    assert data.startswith(PNG_MAGIC)


def test_extract_batch_id_finds_id_in_trace_payload():
    text = format_batch_trace("TEA001", SAMPLE_BLOCKS)
    assert extract_batch_id(text) == "TEA001"


def test_extract_batch_id_returns_none_for_unrelated_qr_content():
    assert extract_batch_id("https://example.com/some-other-product") is None
    assert extract_batch_id("") is None
    assert extract_batch_id(None) is None


def test_decode_qr_image_round_trips_generated_qr():
    text = format_batch_trace("TEA001", SAMPLE_BLOCKS)
    png = generate_qr_png_bytes(text)
    assert decode_qr_image(png) == text


def test_decode_qr_image_returns_none_when_no_qr_present():
    from PIL import Image
    import io

    blank = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    blank.save(buf, format="PNG")
    assert decode_qr_image(buf.getvalue()) is None


def test_scan_round_trip_recovers_original_batch_id():
    """End-to-end: generate a batch's QR, decode the image, extract the batch ID
    -- mirrors exactly what the in-app camera scanner does with a photo."""
    original_batch_id = "TEA001"
    text = format_batch_trace(original_batch_id, SAMPLE_BLOCKS)
    png = generate_qr_png_bytes(text)

    decoded_text = decode_qr_image(png)
    scanned_batch_id = extract_batch_id(decoded_text)

    assert scanned_batch_id == original_batch_id

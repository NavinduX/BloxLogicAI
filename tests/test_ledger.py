"""
Tests for blockchain/ledger.py — verifies SHA-256 chain integrity, per-batch
isolation, stage-sequence enforcement, filtering, and tamper detection.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from blockchain.ledger import (
    GENESIS_HASH,
    InvalidStageError,
    _hash_block,
    add_block,
    get_batch,
    next_stage,
    verify_chain,
)


# ---------------------------------------------------------------------------
# Fixture — temporary ledger path (file does NOT exist yet, so load_ledger returns [])
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_ledger(tmp_path):
    """Return a path inside a temp directory that does not exist yet."""
    return str(tmp_path / "test_ledger.json")


def _seed(path: str) -> list[dict]:
    """Write demo blocks to *path* and return them."""
    with patch("blockchain.ledger.LEDGER_PATH", path):
        add_block("TEA001", "Harvested", "Nuwara Eliya", "2,000 kg BOP", "2026-01-01T08:00:00")
        add_block("TEA001", "Processed", "Factory A",    "Dried at 90°C",  "2026-01-03T10:00:00")
        add_block("TEA002", "Harvested", "Kandy Estate", "1,500 kg BOPF",  "2026-01-05T09:00:00")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# _hash_block
# ---------------------------------------------------------------------------

def test_hash_block_deterministic():
    h1 = _hash_block("TEA001", 1, "Harvested", "Nuwara Eliya", "test", "2026-01-01T08:00:00", GENESIS_HASH)
    h2 = _hash_block("TEA001", 1, "Harvested", "Nuwara Eliya", "test", "2026-01-01T08:00:00", GENESIS_HASH)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest is always 64 chars


def test_hash_block_sensitive_to_each_field():
    base = ("TEA001", 1, "Harvested", "Nuwara Eliya", "test", "2026-01-01T08:00:00", GENESIS_HASH)
    base_hash = _hash_block(*base)
    variants = [
        ("TEA002", 1, "Harvested", "Nuwara Eliya", "test", "2026-01-01T08:00:00", GENESIS_HASH),
        ("TEA001", 2, "Harvested", "Nuwara Eliya", "test", "2026-01-01T08:00:00", GENESIS_HASH),
        ("TEA001", 1, "Processed", "Nuwara Eliya", "test", "2026-01-01T08:00:00", GENESIS_HASH),
        ("TEA001", 1, "Harvested", "Other Estate", "test", "2026-01-01T08:00:00", GENESIS_HASH),
        ("TEA001", 1, "Harvested", "Nuwara Eliya", "diff", "2026-01-01T08:00:00", GENESIS_HASH),
        ("TEA001", 1, "Harvested", "Nuwara Eliya", "test", "2026-01-02T08:00:00", GENESIS_HASH),
        ("TEA001", 1, "Harvested", "Nuwara Eliya", "test", "2026-01-01T08:00:00", "a" * 16),
    ]
    for args in variants:
        assert _hash_block(*args) != base_hash


# ---------------------------------------------------------------------------
# verify_chain
# ---------------------------------------------------------------------------

def test_verify_chain_valid(tmp_ledger):
    blocks = _seed(tmp_ledger)
    assert verify_chain(blocks) is True


def test_verify_chain_empty():
    assert verify_chain([]) is True


def test_verify_chain_detects_data_tampering(tmp_ledger):
    blocks = _seed(tmp_ledger)
    tampered = copy.deepcopy(blocks)
    tampered[0]["location"] = "Hacked Location"  # data changed, stored hash unchanged
    assert verify_chain(tampered) is False


def test_verify_chain_detects_hash_tampering(tmp_ledger):
    blocks = _seed(tmp_ledger)
    tampered = copy.deepcopy(blocks)
    tampered[1]["current_hash"] = "a" * 64  # hash replaced with garbage
    assert verify_chain(tampered) is False


def test_verify_chain_detects_backlink_break(tmp_ledger):
    blocks = _seed(tmp_ledger)
    tampered = copy.deepcopy(blocks)
    tampered[1]["previous_hash"] = "b" * 64  # back-link severed
    assert verify_chain(tampered) is False


def test_verify_chain_per_batch_isolation(tmp_ledger):
    """Tampering one batch's block must not invalidate another batch's chain."""
    blocks = _seed(tmp_ledger)
    tampered = copy.deepcopy(blocks)
    tea002_block = next(b for b in tampered if b["batch_id"] == "TEA002")
    tea002_block["location"] = "Hacked Location"

    tea001_blocks = [b for b in tampered if b["batch_id"] == "TEA001"]
    tea002_blocks = [b for b in tampered if b["batch_id"] == "TEA002"]

    assert verify_chain(tea001_blocks) is True
    assert verify_chain(tea002_blocks) is False
    assert verify_chain(tampered) is False  # whole-ledger check still catches it


# ---------------------------------------------------------------------------
# get_batch / next_stage
# ---------------------------------------------------------------------------

def test_get_batch_filters_by_id(tmp_ledger):
    _seed(tmp_ledger)
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        tea1 = get_batch("TEA001")
        tea2 = get_batch("TEA002")
        none = get_batch("TEA999")

    assert len(tea1) == 2
    assert all(b["batch_id"] == "TEA001" for b in tea1)
    assert len(tea2) == 1
    assert len(none) == 0


def test_get_batch_case_insensitive(tmp_ledger):
    _seed(tmp_ledger)
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        lower = get_batch("tea001")
        upper = get_batch("TEA001")
    assert len(lower) == len(upper) == 2


def test_next_stage_progression(tmp_ledger):
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        assert next_stage("TEA001") == "Harvested"
        add_block("TEA001", "Harvested", "Estate A", "details")
        assert next_stage("TEA001") == "Processed"


# ---------------------------------------------------------------------------
# add_block round-trip
# ---------------------------------------------------------------------------

def test_add_block_seq_is_per_batch(tmp_ledger):
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        b1 = add_block("TEA001", "Harvested", "Estate A", "details")
        b2 = add_block("TEA002", "Harvested", "Estate B", "details")
        b3 = add_block("TEA001", "Processed", "Factory B", "details")
    assert b1["seq"] == 1
    assert b2["seq"] == 1  # independent counter for TEA002
    assert b3["seq"] == 2
    assert b3["previous_hash"] == b1["current_hash"]


def test_add_block_genesis_previous_hash(tmp_ledger):
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        b = add_block("TEA001", "Harvested", "Estate A", "details")
    assert b["previous_hash"] == GENESIS_HASH


def test_add_block_enforces_stage_order(tmp_ledger):
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        with pytest.raises(InvalidStageError):
            add_block("TEA001", "Processed", "Estate A", "details")  # must start at Harvested

        add_block("TEA001", "Harvested", "Estate A", "details")
        with pytest.raises(InvalidStageError):
            add_block("TEA001", "Exported", "Estate A", "details")  # skips stages


def test_add_block_rejects_duplicate_stage(tmp_ledger):
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        add_block("TEA001", "Harvested", "Estate A", "details")
        with pytest.raises(InvalidStageError):
            add_block("TEA001", "Harvested", "Estate A", "details")


def test_add_block_rejects_after_exported(tmp_ledger):
    with patch("blockchain.ledger.LEDGER_PATH", tmp_ledger):
        for stage in ["Harvested", "Processed", "Blended", "Packaged", "Exported"]:
            add_block("TEA001", stage, "Estate A", "details")
        with pytest.raises(InvalidStageError):
            add_block("TEA001", "Exported", "Estate A", "details")

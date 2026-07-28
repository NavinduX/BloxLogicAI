"""
SHA-256 hash chain ledger for tea batch traceability.

Each block records one supply-chain event for a tea batch and is linked to the
previous block via its hash, making tampering detectable.

Ledger is persisted as a flat JSON file (data/blockchain_ledger.json).
Run this module as a script once to seed the ledger with demo data:

    .venv/Scripts/python.exe blockchain/ledger.py
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(ROOT, "data", "blockchain_ledger.json")

GENESIS_HASH = "0" * 16
_ledger_lock = threading.Lock()


def _hash_block(batch_id: str, stage: str, location: str, details: str,
                timestamp: str, previous_hash: str) -> str:
    content = f"{batch_id}|{stage}|{location}|{details}|{timestamp}|{previous_hash}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_ledger() -> list[dict]:
    """Load all blocks from the JSON ledger. Returns empty list if not found."""
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_ledger(blocks: list[dict]) -> None:
    """Persist the block list to disk (overwrites)."""
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as fh:
        json.dump(blocks, fh, indent=2)


def add_block(batch_id: str, stage: str, location: str,
              details: str, timestamp: str | None = None) -> dict:
    """Append a new block and return it. Thread-safe via _ledger_lock."""
    with _ledger_lock:
        blocks = load_ledger()
        previous_hash = blocks[-1]["current_hash"] if blocks else GENESIS_HASH
        ts = timestamp or datetime.now().isoformat(timespec="seconds")
        current_hash = _hash_block(batch_id, stage, location, details, ts, previous_hash)
        block = {
            "block_num": len(blocks) + 1,
            "batch_id": batch_id.upper().strip(),
            "stage": stage,
            "location": location,
            "details": details,
            "timestamp": ts,
            "previous_hash": previous_hash,
            "current_hash": current_hash,
        }
        blocks.append(block)
        save_ledger(blocks)
    return block


def verify_chain(blocks: list[dict]) -> bool:
    """Return True if every block's hash and back-link are intact."""
    for i, blk in enumerate(blocks):
        expected = _hash_block(
            blk["batch_id"], blk["stage"], blk["location"],
            blk["details"], blk["timestamp"], blk["previous_hash"],
        )
        if blk["current_hash"] != expected:
            return False
        expected_prev = blocks[i - 1]["current_hash"] if i > 0 else GENESIS_HASH
        if blk["previous_hash"] != expected_prev:
            return False
    return True


def get_batch(batch_id: str) -> list[dict]:
    """Return all blocks for a given batch ID (case-insensitive)."""
    return [b for b in load_ledger() if b["batch_id"] == batch_id.upper().strip()]


# ---------------------------------------------------------------------------
# Seed script — run once to create demo data
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if os.path.exists(LEDGER_PATH):
        os.remove(LEDGER_PATH)
        print("Cleared existing ledger.")

    seed: list[tuple[str, str, str, str, str]] = [
        # batch_id, stage, location, details, timestamp
        ("TEA001", "Harvested",  "Nuwara Eliya Estate",    "2,500 kg Orthodox Black Tea harvested; leaf grade: BOP",                "2026-01-05T08:00:00"),
        ("TEA001", "Processed",  "Tea Factory A, Nuwara Eliya", "Withered 18h; CTC rolled; dried at 90°C; moisture 3.4%",          "2026-01-07T10:30:00"),
        ("TEA001", "Blended",    "Colombo Blending Hub",   "Blended with BOPF grade; final moisture 3.2%; lot #NE-2601-A",        "2026-01-09T09:00:00"),
        ("TEA001", "Packaged",   "Colombo Export Hub",     "Packed in 50 kg foil-lined bags; 50 bags; pallet #P-2601-NE",          "2026-01-10T14:00:00"),
        ("TEA001", "Exported",   "Port of Colombo",        "Destination: UK; container HLCU4421839; vessel MSC Beatrice",          "2026-01-12T06:00:00"),

        ("TEA002", "Harvested",  "Kandy Estate",           "1,800 kg CTC Black Tea harvested; leaf grade: BOPF",                   "2026-01-15T07:30:00"),
        ("TEA002", "Processed",  "Tea Factory B, Kandy",   "Withered 16h; CTC processed; dried; moisture 3.6%",                   "2026-01-17T11:00:00"),
        ("TEA002", "Packaged",   "Colombo Export Hub",     "Packed in 50 kg foil-lined bags; 36 bags; pallet #P-2601-KD",          "2026-01-20T13:00:00"),

        ("TEA003", "Harvested",  "Uva Estate, Badulla",    "2,200 kg BOP Grade; high-elevation single-estate",                     "2026-01-20T08:00:00"),
        ("TEA003", "Processed",  "Tea Factory C, Badulla", "Processed orthodox method; withered 20h; fired at 85°C",               "2026-01-22T10:00:00"),
        ("TEA003", "Blended",    "Colombo Blending Hub",   "Blended with OP grade; cupped and approved by master taster",         "2026-01-24T09:30:00"),
        ("TEA003", "Packaged",   "Colombo Export Hub",     "Packed in 50 kg foil-lined bags; 44 bags; pallet #P-2601-UV",          "2026-01-25T15:00:00"),
        ("TEA003", "Exported",   "Port of Colombo",        "Destination: UAE; container MSCU3312765; vessel MSC Arabia",            "2026-01-27T06:00:00"),
    ]

    for batch_id, stage, location, details, ts in seed:
        blk = add_block(batch_id, stage, location, details, timestamp=ts)
        print(f"  Block {blk['block_num']:>2} | {batch_id} | {stage:<12} | {blk['current_hash'][:20]}...")

    blocks = load_ledger()
    valid = verify_chain(blocks)
    print(f"\nTotal blocks : {len(blocks)}")
    print(f"Chain valid  : {valid}")
    if not valid:
        print("ERROR: chain verification failed — check seed data.")

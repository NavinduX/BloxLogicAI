"""
SHA-256 hash chain ledger for tea batch traceability.

Each tea batch owns its own independent hash chain: a block's previous_hash
links only to the prior block of the SAME batch, seeded at GENESIS_HASH.
Stage transitions are enforced in strict order (Harvested -> Processed ->
Blended -> Packaged -> Exported) -- no skipping, no duplicates, no re-opening
a batch once Exported.

Ledger is persisted as a flat JSON file (data/blockchain_ledger.json) -- one
list containing all batches' blocks, in insertion order.

    .venv/Scripts/python.exe blockchain/ledger.py             # reseed demo data
    .venv/Scripts/python.exe blockchain/ledger.py --tamper    # non-destructive tamper demo
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import threading
from datetime import datetime
from typing import TypedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(ROOT, "data", "blockchain_ledger.json")

GENESIS_HASH = "0" * 16
STAGE_ORDER = ["Harvested", "Processed", "Blended", "Packaged", "Exported"]
_ledger_lock = threading.Lock()


class Block(TypedDict):
    batch_id: str
    seq: int
    stage: str
    location: str
    details: str
    timestamp: str
    previous_hash: str
    current_hash: str


class InvalidStageError(ValueError):
    """Raised by add_block() when a stage violates STAGE_ORDER for its batch."""


# --- hashing -----------------------------------------------------------------

def _hash_block(batch_id: str, seq: int, stage: str, location: str, details: str,
                timestamp: str, previous_hash: str) -> str:
    content = f"{batch_id}|{seq}|{stage}|{location}|{details}|{timestamp}|{previous_hash}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# --- persistence ---------------------------------------------------------------

def load_ledger() -> list[Block]:
    """Load all blocks from the JSON ledger. Returns empty list if not found."""
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_ledger(blocks: list[Block]) -> None:
    """Persist the block list to disk (overwrites)."""
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w", encoding="utf-8") as fh:
        json.dump(blocks, fh, indent=2)


# --- queries ---------------------------------------------------------------------

def get_batch(batch_id: str) -> list[Block]:
    """Return all blocks for a given batch ID (case-insensitive), in seq order."""
    bid = batch_id.upper().strip()
    return [b for b in load_ledger() if b["batch_id"] == bid]


def next_stage(batch_id: str, blocks: list[Block] | None = None) -> str | None:
    """Return the only valid next stage for batch_id, or None if already Exported."""
    batch_blocks = get_batch(batch_id) if blocks is None else blocks
    if not batch_blocks:
        return STAGE_ORDER[0]
    last_stage = batch_blocks[-1]["stage"]
    idx = STAGE_ORDER.index(last_stage)
    if idx == len(STAGE_ORDER) - 1:
        return None
    return STAGE_ORDER[idx + 1]


# --- mutation ------------------------------------------------------------------

def add_block(batch_id: str, stage: str, location: str,
              details: str, timestamp: str | None = None) -> Block:
    """Append a new block, enforcing STAGE_ORDER for the batch. Thread-safe.

    Raises InvalidStageError if the batch is already complete (Exported) or
    if `stage` is not the batch's expected next stage.
    """
    batch_id = batch_id.upper().strip()
    with _ledger_lock:
        blocks = load_ledger()
        batch_blocks = [b for b in blocks if b["batch_id"] == batch_id]
        expected = next_stage(batch_id, batch_blocks)
        if expected is None:
            raise InvalidStageError(f"Batch {batch_id} is already complete (Exported).")
        if stage != expected:
            raise InvalidStageError(
                f"Invalid stage for {batch_id}: expected '{expected}', got '{stage}'."
            )
        seq = len(batch_blocks) + 1
        previous_hash = batch_blocks[-1]["current_hash"] if batch_blocks else GENESIS_HASH
        ts = timestamp or datetime.now().isoformat(timespec="seconds")
        current_hash = _hash_block(batch_id, seq, stage, location, details, ts, previous_hash)
        block: Block = {
            "batch_id": batch_id,
            "seq": seq,
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


# --- verification --------------------------------------------------------------

def verify_chain(blocks: list[Block]) -> bool:
    """Return True iff every batch's hash sub-chain is internally consistent.

    Blocks are grouped by batch_id (insertion order) and each batch's chain
    is verified independently against its own GENESIS_HASH -- a tampered
    block in one batch does not affect another batch's validity.
    """
    by_batch: dict[str, list[Block]] = {}
    for b in blocks:
        by_batch.setdefault(b["batch_id"], []).append(b)

    for batch_blocks in by_batch.values():
        prev_hash = GENESIS_HASH
        for blk in batch_blocks:
            expected = _hash_block(
                blk["batch_id"], blk["seq"], blk["stage"], blk["location"],
                blk["details"], blk["timestamp"], blk["previous_hash"],
            )
            if blk["current_hash"] != expected or blk["previous_hash"] != prev_hash:
                return False
            prev_hash = blk["current_hash"]
    return True


# ---------------------------------------------------------------------------
# Seed script / tamper demo — run as a script
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed or inspect the blockchain ledger.")
    parser.add_argument(
        "--tamper", action="store_true",
        help="Run a non-destructive tamper-detection demo (does not modify the saved file).",
    )
    args = parser.parse_args()

    if args.tamper:
        blocks = load_ledger()
        if not blocks:
            print("Ledger is empty — run without --tamper first to seed demo data.")
        else:
            print(f"Original chain valid : {verify_chain(blocks)}")
            tampered = copy.deepcopy(blocks)
            victim = tampered[0]
            print(f"Tampering {victim['batch_id']} #{victim['seq']} ({victim['stage']}): location changed.")
            victim["location"] = "HACKED — " + victim["location"]
            print(f"Tampered chain valid  : {verify_chain(tampered)}")
            print("(In-memory only — data/blockchain_ledger.json was not modified.)")
    else:
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
            ("TEA002", "Blended",    "Colombo Blending Hub",   "Blended with OPA grade; final moisture 3.5%; lot #KD-2601-B",         "2026-01-18T09:00:00"),
            ("TEA002", "Packaged",   "Colombo Export Hub",     "Packed in 50 kg foil-lined bags; 36 bags; pallet #P-2601-KD",          "2026-01-20T13:00:00"),

            ("TEA003", "Harvested",  "Uva Estate, Badulla",    "2,200 kg BOP Grade; high-elevation single-estate",                     "2026-01-20T08:00:00"),
            ("TEA003", "Processed",  "Tea Factory C, Badulla", "Processed orthodox method; withered 20h; fired at 85°C",               "2026-01-22T10:00:00"),
            ("TEA003", "Blended",    "Colombo Blending Hub",   "Blended with OP grade; cupped and approved by master taster",         "2026-01-24T09:30:00"),
            ("TEA003", "Packaged",   "Colombo Export Hub",     "Packed in 50 kg foil-lined bags; 44 bags; pallet #P-2601-UV",          "2026-01-25T15:00:00"),
            ("TEA003", "Exported",   "Port of Colombo",        "Destination: UAE; container MSCU3312765; vessel MSC Arabia",            "2026-01-27T06:00:00"),
        ]

        for batch_id, stage, location, details, ts in seed:
            blk = add_block(batch_id, stage, location, details, timestamp=ts)
            print(f"  {batch_id} #{blk['seq']:>2} | {stage:<12} | {blk['current_hash'][:20]}...")

        blocks = load_ledger()
        valid = verify_chain(blocks)
        print(f"\nTotal blocks : {len(blocks)}")
        print(f"Chain valid  : {valid}")
        if not valid:
            print("ERROR: chain verification failed — check seed data.")

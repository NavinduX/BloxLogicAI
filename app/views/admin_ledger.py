"""
Admin — Blockchain Ledger: view all blocks and add new batch events.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.style import metric_card
from blockchain.ledger import add_block, load_ledger, verify_chain

_STAGES = ["Harvested", "Processed", "Blended", "Packaged", "Exported"]


def render() -> None:
    st.header("Blockchain Ledger")
    st.caption(
        "Immutable SHA-256 hash chain for tea batch traceability. "
        "Each row is one supply-chain event."
    )

    blocks = load_ledger()
    chain_ok = verify_chain(blocks) if blocks else True
    batch_ids = sorted({b["batch_id"] for b in blocks})

    # ── Summary cards ─────────────────────────────────────────────────────
    s1, s2, s3 = st.columns(3)
    with s1:
        metric_card("Total Blocks", str(len(blocks)), note="SHA-256 linked")
    with s2:
        metric_card("Unique Batches", str(len(batch_ids)), note=" · ".join(batch_ids))
    with s3:
        validity = "VALID ✓" if chain_ok else "TAMPERED ✗"
        metric_card("Chain Status", validity, positive=chain_ok)

    st.divider()

    # ── Ledger table ──────────────────────────────────────────────────────
    st.subheader("All Blocks")

    if blocks:
        df = pd.DataFrame(blocks)
        df["Hash (preview)"]    = df["current_hash"].str[:20] + "…"
        df["timestamp"]         = df["timestamp"].str.replace("T", " ")
        display = df[[
            "block_num", "batch_id", "stage", "location", "timestamp", "Hash (preview)",
        ]].rename(columns={
            "block_num": "Block #",
            "batch_id":  "Batch ID",
            "stage":     "Stage",
            "location":  "Location",
            "timestamp": "Timestamp",
        })
        st.dataframe(display, use_container_width=True, hide_index=True, height=320)

        with st.expander("View full block details"):
            options = [
                f"Block #{b['block_num']} — {b['batch_id']} / {b['stage']}"
                for b in blocks
            ]
            selected = st.selectbox("Select block", options=options)
            idx = options.index(selected)
            st.json(blocks[idx])
    else:
        st.info("No blocks in the ledger yet. Add the first batch event below.")

    st.divider()

    # ── Add new batch event ───────────────────────────────────────────────
    st.subheader("Add New Batch Event")
    st.caption(
        "Each submission appends a new SHA-256 block linked to the previous one. "
        "Tampering with any prior block invalidates the chain."
    )

    with st.form("add_block_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_batch_id = st.text_input(
                "Batch ID",
                placeholder="e.g. TEA004",
                help="Use an existing batch ID to extend its chain, or a new ID for a fresh batch.",
            )
            new_stage = st.selectbox("Stage", _STAGES)
        with col2:
            new_location = st.text_input("Location", placeholder="e.g. Nuwara Eliya Estate")
            new_details  = st.text_area(
                "Details",
                placeholder="e.g. 2,000 kg Orthodox Black Tea, lot #NE-2602",
                height=100,
            )
        submitted = st.form_submit_button("Add to Ledger", use_container_width=True, type="primary")

    if submitted:
        if new_batch_id and new_location and new_details:
            blk = add_block(new_batch_id, new_stage, new_location, new_details)
            st.success(
                f"Block #{blk['block_num']} added for batch **{blk['batch_id']}** "
                f"({blk['stage']}).  \n"
                f"Hash: `{blk['current_hash'][:32]}…`"
            )
            st.rerun()
        else:
            st.error("Please fill in Batch ID, Location, and Details.")

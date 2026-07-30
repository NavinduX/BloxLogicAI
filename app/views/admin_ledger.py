"""
Admin — Blockchain Ledger: view all blocks and add new batch events.
"""

from __future__ import annotations

import copy
from datetime import datetime

import pandas as pd
import streamlit as st

from app.style import metric_card
from blockchain.ledger import (
    STAGE_ORDER,
    InvalidStageError,
    add_block,
    get_batch,
    load_ledger,
    next_stage,
    verify_chain,
)
from blockchain.qr_generator import format_batch_trace, generate_qr_png_bytes


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
        df = pd.DataFrame(blocks).sort_values(["batch_id", "seq"])
        df["Hash (preview)"]    = df["current_hash"].str[:20] + "…"
        df["timestamp"]         = df["timestamp"].str.replace("T", " ")
        display = df[[
            "batch_id", "seq", "stage", "location", "timestamp", "Hash (preview)",
        ]].rename(columns={
            "batch_id":  "Batch ID",
            "seq":       "Seq",
            "stage":     "Stage",
            "location":  "Location",
            "timestamp": "Timestamp",
        })
        st.dataframe(display, use_container_width=True, hide_index=True, height=320)

        with st.expander("View full block details"):
            sorted_blocks = sorted(blocks, key=lambda b: (b["batch_id"], b["seq"]))
            options = [
                f"{b['batch_id']} #{b['seq']} — {b['stage']}"
                for b in sorted_blocks
            ]
            selected = st.selectbox("Select block", options=options)
            idx = options.index(selected)
            st.json(sorted_blocks[idx])
    else:
        st.info("No blocks in the ledger yet. Add the first batch event below.")

    st.divider()

    # ── Add new batch event ───────────────────────────────────────────────
    st.subheader("Add New Batch Event")
    st.caption(
        "Each submission appends a new SHA-256 block linked to the previous one. "
        "Tampering with any prior block invalidates the chain."
    )

    hint_batch_id = st.selectbox(
        "Check next expected stage for",
        options=["(new batch)"] + batch_ids,
        help="Pick an existing batch to see what stage it expects next, or choose (new batch) for a fresh one.",
    )
    if hint_batch_id != "(new batch)":
        hint = next_stage(hint_batch_id)
        st.caption(f"Next expected stage for **{hint_batch_id}**: "
                   f"{hint if hint else 'complete — already Exported'}")
    else:
        st.caption(f"A new batch must start at **{STAGE_ORDER[0]}**.")

    with st.form("add_block_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_batch_id = st.text_input(
                "Batch ID",
                placeholder="e.g. TEA004",
                help="Use an existing batch ID to extend its chain, or a new ID for a fresh batch.",
            )
            new_stage = st.selectbox("Stage", STAGE_ORDER)
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
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            try:
                blk = add_block(new_batch_id, new_stage, new_location, new_details)
                st.success(
                    f"Block #{blk['seq']} added for batch **{blk['batch_id']}** "
                    f"({blk['stage']}).  \n"
                    f"Hash: `{blk['current_hash'][:32]}…`"
                )
                st.session_state.setdefault("ledger_log", []).append(
                    f"{ts} — Block added: {blk['batch_id']} / {blk['stage']}"
                )
                st.rerun()
            except InvalidStageError as exc:
                st.error(str(exc))
                st.session_state.setdefault("ledger_log", []).append(
                    f"{ts} — Add block failed: {exc}"
                )
        else:
            st.error("Please fill in Batch ID, Location, and Details.")

    # ── Batch QR codes ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Batch QR Codes")
    st.caption(
        "Generate a scannable QR code encoding a batch's full recorded journey "
        "(FR10) — anyone scanning it sees every stage without needing this app."
    )

    if batch_ids:
        qr_batch_id = st.selectbox("Batch", batch_ids, key="qr_batch_select")
        if st.button("Generate QR"):
            qr_blocks = get_batch(qr_batch_id)
            qr_png = generate_qr_png_bytes(format_batch_trace(qr_batch_id, qr_blocks))
            st.image(qr_png, width=280)
            st.download_button(
                "Download QR",
                data=qr_png,
                file_name=f"{qr_batch_id}_qr.png",
                mime="image/png",
            )
    else:
        st.info("No batches in the ledger yet.")

    # ── Tamper detection demo ────────────────────────────────────────────────
    st.divider()
    st.subheader("Tamper Detection Demo")
    st.caption(
        "Demonstrates that any edit to a block invalidates its batch's chain. "
        "Operates on an in-memory copy only — the saved ledger is never modified."
    )

    if batch_ids:
        demo_batch_id = st.selectbox("Batch to demo", batch_ids, key="tamper_demo_batch")
        if st.button("Run Tamper Demo"):
            original = get_batch(demo_batch_id)
            before_valid = verify_chain(original)
            tampered = copy.deepcopy(original)
            tampered[0]["location"] = "HACKED — " + tampered[0]["location"]
            after_valid = verify_chain(tampered)

            c1, c2 = st.columns(2)
            with c1:
                metric_card("Before tampering", "VALID ✓" if before_valid else "TAMPERED ✗",
                            positive=before_valid)
            with c2:
                metric_card("After tampering block #1", "VALID ✓" if after_valid else "TAMPERED ✗",
                            positive=after_valid)
            st.info("In-memory demo only — data/blockchain_ledger.json was not modified.")
    else:
        st.info("No batches in the ledger yet.")

    # ── Action log ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Action Log")
    if "ledger_log" not in st.session_state:
        st.session_state.ledger_log = []
    if st.session_state.ledger_log:
        for entry in reversed(st.session_state.ledger_log[-5:]):
            st.markdown(f"- {entry}")
    else:
        st.info("No actions recorded this session.")

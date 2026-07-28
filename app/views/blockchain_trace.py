"""
Blockchain Traceability view — user-facing batch search and chain verification.
"""

from __future__ import annotations

import html

import streamlit as st

from blockchain.ledger import get_batch, load_ledger, verify_chain

_STAGE_ORDER = ["Harvested", "Processed", "Blended", "Packaged", "Exported"]


def render() -> None:
    st.header("Blockchain Traceability")
    st.caption(
        "Verify the provenance and integrity of any tea batch. "
        "Each event is recorded as an immutable SHA-256 linked block."
    )

    # ── Search ───────────────────────────────────────────────────────────────
    with st.form("batch_search"):
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            batch_id = st.text_input(
                "Batch ID",
                placeholder="e.g. TEA001",
                label_visibility="collapsed",
            )
        with col_btn:
            search = st.form_submit_button("Search", use_container_width=True)

    st.caption("Available demo batches: **TEA001** (exported to UK) · **TEA002** (awaiting export) · **TEA003** (exported to UAE)")

    if not search and not batch_id:
        st.info("Enter a Batch ID above and click Search to trace a tea batch.")
        return

    if not batch_id:
        st.warning("Please enter a Batch ID.")
        return

    # ── Lookup ───────────────────────────────────────────────────────────────
    batch_blocks = get_batch(batch_id.strip())

    if not batch_blocks:
        st.error(
            f"No records found for batch **{batch_id.upper()}**. "
            "Try TEA001, TEA002, or TEA003."
        )
        return

    # Full-chain verification
    all_blocks = load_ledger()
    chain_ok = verify_chain(all_blocks)
    validity_html = (
        '<span class="chain-valid">VALID ✓</span>'
        if chain_ok
        else '<span class="chain-invalid">TAMPERED ✗</span>'
    )

    st.divider()

    # ── Batch header ─────────────────────────────────────────────────────────
    hcol1, hcol2 = st.columns([3, 2])
    with hcol1:
        st.subheader(f"Batch: {batch_id.upper()}")
        st.markdown(
            f"Blockchain Status: {validity_html}",
            unsafe_allow_html=True,
        )
    with hcol2:
        st.metric("Recorded Events", len(batch_blocks))
        last_ts = batch_blocks[-1]["timestamp"].split("T")[0]
        st.metric("Last Updated", last_ts)

    st.divider()

    # ── Stage timeline ────────────────────────────────────────────────────────
    completed_stages = {b["stage"] for b in batch_blocks}

    for i, blk in enumerate(batch_blocks):
        t_col, c_col, h_col = st.columns([1, 6, 3])

        with t_col:
            st.markdown(
                '<div class="step-check">✓</div>',
                unsafe_allow_html=True,
            )

        with c_col:
            ts_display = blk["timestamp"].replace("T", " ")
            st.markdown(
                f"**{blk['stage']}**  \n"
                f"<span style='color:#444'>{html.escape(blk['location'])}</span>  \n"
                f"<small style='color:#888'>{ts_display}</small>",
                unsafe_allow_html=True,
            )
            st.caption(blk["details"])

        with h_col:
            st.markdown(
                f"<div style='text-align:right;font-size:12px;color:#888'>"
                f"Block #{blk['block_num']}<br>"
                f"<code style='font-size:11px'>{blk['current_hash'][:16]}…</code>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # connector between stages
        if i < len(batch_blocks) - 1:
            st.markdown(
                '<div class="step-connector"></div>',
                unsafe_allow_html=True,
            )

    # Show pending stages (not yet recorded)
    pending = [s for s in _STAGE_ORDER if s not in completed_stages]
    if pending:
        st.markdown("")
        st.markdown(
            f"<div style='color:#BDBDBD;font-size:14px;margin-left:6px'>"
            f"Pending: {' → '.join(pending)}</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Chain validity summary ────────────────────────────────────────────────
    st.markdown(
        f"**Blockchain Status:** {validity_html}  \n"
        "<small style='color:#666'>All block hashes verified via SHA-256 "
        "back-linking. Any tampering with a previous block would invalidate "
        "every subsequent hash.</small>",
        unsafe_allow_html=True,
    )

    # ── Raw block data ────────────────────────────────────────────────────────
    with st.expander("View raw block data"):
        for blk in batch_blocks:
            st.json(blk)

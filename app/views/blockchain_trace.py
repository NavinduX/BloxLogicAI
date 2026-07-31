"""
Blockchain Traceability view — user-facing batch search and chain verification.
"""

from __future__ import annotations

import html

import streamlit as st

from blockchain.ledger import STAGE_ORDER, get_batch, verify_chain
from blockchain.qr_generator import (
    decode_qr_image,
    extract_batch_id,
    format_batch_trace,
    generate_qr_png_bytes,
)


def _render_qr_scanner() -> None:
    """Camera-based QR scanner panel, shown when the user clicks the scan icon."""
    with st.container(border=True):
        st.markdown("**Scan a batch's QR code**")
        st.caption("Point your camera at a batch's QR code, then take the photo.")

        cam_key = f"qr_scanner_camera_{st.session_state.get('qr_scan_session', 0)}"
        photo = st.camera_input("Scan QR", label_visibility="collapsed", key=cam_key)

        if photo is not None:
            decoded_text = decode_qr_image(photo.getvalue())
            scanned_id = extract_batch_id(decoded_text) if decoded_text else None
            if scanned_id:
                st.session_state["scanned_batch_id"] = scanned_id
                st.session_state["show_scanner"] = False
                st.rerun()
            elif decoded_text:
                st.error("That doesn't look like a BloxLogicAI batch QR code.")
            else:
                st.error("No QR code detected in the photo — try again with better lighting or focus.")

        if st.button("Cancel", key="cancel_scan_btn"):
            st.session_state["show_scanner"] = False
            st.rerun()


def render() -> None:
    st.header("Blockchain Traceability")
    st.caption(
        "Verify the provenance and integrity of any tea batch. "
        "Each event is recorded as an immutable SHA-256 linked block."
    )

    # ── Search ───────────────────────────────────────────────────────────────
    with st.form("batch_search"):
        col_input, col_btn, col_scan = st.columns([4, 1, 1])
        with col_input:
            batch_id_typed = st.text_input(
                "Batch ID",
                placeholder="e.g. TEA001",
                label_visibility="collapsed",
            )
        with col_btn:
            search = st.form_submit_button("Search", use_container_width=True)
        with col_scan:
            scan = st.form_submit_button("📷", help="Scan a batch's QR code with your camera", use_container_width=True)

    if scan:
        opening = not st.session_state.get("show_scanner", False)
        st.session_state["show_scanner"] = opening
        if opening:
            st.session_state["qr_scan_session"] = st.session_state.get("qr_scan_session", 0) + 1

    if st.session_state.get("show_scanner"):
        _render_qr_scanner()

    # A typed Batch ID always wins; otherwise fall back to the last QR scan.
    if batch_id_typed:
        batch_id = batch_id_typed.strip()
        st.session_state.pop("scanned_batch_id", None)
    else:
        batch_id = st.session_state.get("scanned_batch_id")

    if not batch_id:
        if search:
            st.warning("Please enter a Batch ID.")
        else:
            st.info("Enter a Batch ID above, click Search, or scan a batch's QR code to trace a tea batch.")
        return

    # ── Lookup ───────────────────────────────────────────────────────────────
    batch_blocks = get_batch(batch_id.strip())

    if not batch_blocks:
        st.error(
            f"No records found for batch **{batch_id.upper()}**. "
            "Try TEA001, TEA002, or TEA003."
        )
        return

    # Verify this batch's own chain (independent of any other batch's chain)
    chain_ok = verify_chain(batch_blocks)
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

    # ── QR code ──────────────────────────────────────────────────────────────
    qcol1, qcol2 = st.columns([1, 4])
    with qcol1:
        qr_png = generate_qr_png_bytes(format_batch_trace(batch_id, batch_blocks))
        st.image(qr_png, width=280, caption="Scan for full batch history")
        st.download_button(
            "Download QR",
            data=qr_png,
            file_name=f"{batch_id.upper()}_qr.png",
            mime="image/png",
        )
    with qcol2:
        st.markdown(
            "<div style='color:#666;font-size:13px;padding-top:8px'>"
            "Scan this code with any phone camera or QR app to read this "
            "batch's full journey — every stage, location, and detail — "
            "directly, with no need to open this app or connect to a "
            "network. To additionally verify the SHA-256 chain's integrity, "
            "search this batch's ID in the app.</div>",
            unsafe_allow_html=True,
        )

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
                f"Block #{blk['seq']}<br>"
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
    pending = [s for s in STAGE_ORDER if s not in completed_stages]
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

"""
BloxLogicAI — Green Tea design system.

inject_theme()  injects badge + timeline CSS that config.toml cannot express.
metric_card()   renders a styled KPI card with inline CSS (always works).
section_card()  wraps content in a styled bordered panel (plain HTML).
badge()         returns an inline severity badge HTML string.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# CSS — only elements that config.toml cannot handle
# ---------------------------------------------------------------------------
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');

/* ── Typography & Global Theme ────────────────────────────────────────── */
.block-container {
    padding-top: 1.5rem !important;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, .stHeadingContainer h1 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
}

h2, h3, .stHeadingContainer h2, .stHeadingContainer h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
}

h4, h5, h6, .stHeadingContainer h4, .stHeadingContainer h5, .stHeadingContainer h6 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 500 !important;
}

p, span, div {
    font-family: 'Inter', sans-serif;
}

label, .stButton button, th, .stMetricValue, .stMetricDelta {
    font-weight: 500 !important;
}

/* ── Custom Landing Page Components ───────────────────────────────────── */
.feature-card {
    background: #FFFFFF;
    border: 1px solid #E8F5E9;
    border-left: 5px solid #2E7D32;
    border-radius: 12px;
    padding: 24px;
    height: 100%;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 15px rgba(0,0,0,0.06);
    border-color: #81C784;
    border-left-color: #1B5E20;
}
.feature-card-icon {
    font-size: 32px;
    color: #2E7D32;
    margin-bottom: 16px;
}
.feature-card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 20px;
    color: #1A1A1A;
    margin-bottom: 12px;
}
.feature-card-text {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 15px;
    color: #555555;
    line-height: 1.5;
}

.hero-container {
    position: relative;
    width: 100%;
    border-radius: 16px;
    overflow: hidden;
    min-height: 640px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 60px 20px;
    margin-bottom: 30px;
    background-size: cover;
    background-position: center;
}
.hero-overlay {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.7));
    z-index: 1;
}
.hero-content {
    position: relative;
    z-index: 2;
    color: #FFFFFF;
    max-width: 800px;
    padding: 20px;
}
.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 3.2rem;
    margin-bottom: 16px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    line-height: 1.1;
    color: #ffffff;
}
.hero-subtitle {
    font-family: 'Inter', sans-serif;
    font-weight: 400;
    font-size: 1.25rem;
    margin-bottom: 32px;
    color: #E8F5E9;
    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
}

.footer-container {
    text-align: center;
    padding: 40px 20px 20px;
    margin-top: 40px;
    border-top: 1px solid #E8F5E9;
}
.footer-text {
    font-size: 14px;
    color: #888;
    margin-bottom: 8px;
}
.footer-links {
    font-size: 14px;
    color: #2E7D32;
    text-decoration: none;
    margin: 0 10px;
}

/* ── Severity badges ──────────────────────────────────────────────────── */
.badge-high {
    background: #FFEBEE; color: #C62828;
    padding: 3px 10px; border-radius: 4px;
    font-size: 12px; font-weight: 700;
    display: inline-block; letter-spacing: 0.4px;
}
.badge-medium {
    background: #FFF3E0; color: #E65100;
    padding: 3px 10px; border-radius: 4px;
    font-size: 12px; font-weight: 700;
    display: inline-block; letter-spacing: 0.4px;
}
.badge-low {
    background: #F1F8E9; color: #33691E;
    padding: 3px 10px; border-radius: 4px;
    font-size: 12px; font-weight: 700;
    display: inline-block; letter-spacing: 0.4px;
}

/* ── Blockchain chain status ──────────────────────────────────────────── */
.chain-valid   { color: #1B5E20; font-weight: 700; font-size: 16px; }
.chain-invalid { color: #C62828; font-weight: 700; font-size: 16px; }

/* ── Blockchain timeline connector ───────────────────────────────────── */
.step-connector {
    border-left: 2px solid #C8E6C9;
    height: 20px;
    margin-left: 10px;
    margin-top: 2px;
    margin-bottom: 2px;
}

/* ── Table row stripes inside panels ─────────────────────────────────── */
.status-row {
    display: flex;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #F0F7F0;
    font-size: 14px;
}
.status-label { color: #888; width: 140px; flex-shrink: 0; }
.status-value { color: #1A1A1A; font-weight: 600; flex: 1; }
.status-ok    { color: #2E7D32; font-weight: 700; }
.status-na    { color: #BDBDBD; font-weight: 700; }
.status-err   { color: #C62828; font-weight: 700; }
</style>
"""


def inject_theme() -> None:
    """Inject supplemental CSS. Call once per page load in main.py."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HTML component helpers
# ---------------------------------------------------------------------------

def badge(severity: str) -> str:
    """Return an inline HTML severity badge. severity = HIGH | MEDIUM | LOW."""
    cls = {
        "HIGH":   "badge-high",
        "MEDIUM": "badge-medium",
        "LOW":    "badge-low",
    }.get(severity.upper(), "badge-low")
    return f'<span class="{cls}">{severity}</span>'


def metric_card(
    label: str,
    value: str,
    delta: str = "",
    positive: bool = True,
    note: str = "",
) -> None:
    """
    Render a styled KPI card using inline CSS (guaranteed to render regardless
    of Streamlit's CSS specificity rules).

    Args:
        label:    Card label (small muted text above value).
        value:    Primary metric value (large bold).
        delta:    Optional change indicator text (e.g. "+3.2% vs last month").
        positive: True → green delta arrow, False → red.
        note:     Optional extra caption line below delta.
    """
    delta_color = "#2E7D32" if positive else "#C62828"
    delta_arrow = "▲" if positive else "▼"
    delta_html = (
        f'<div style="color:{delta_color};font-size:12px;margin-top:6px">'
        f'{delta_arrow}&nbsp;{delta}</div>'
    ) if delta else ""
    note_html = (
        f'<div style="color:#AAAAAA;font-size:11px;margin-top:3px">{note}</div>'
    ) if note else ""
    st.markdown(
        f"""
<div style="
    background:#FFFFFF;
    border:1px solid #C8E6C9;
    border-left:5px solid #2E7D32;
    border-radius:8px;
    padding:16px 20px;
    margin-bottom:8px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
">
  <div style="color:#777;font-size:13px;font-weight:500;margin-bottom:4px">{label}</div>
  <div style="color:#1A1A1A;font-size:26px;font-weight:700;line-height:1.2">{value}</div>
  {delta_html}{note_html}
</div>""",
        unsafe_allow_html=True,
    )


def rec_box(label: str, value: str) -> None:
    """Amber-highlighted recommendation box."""
    st.markdown(
        f"""
<div style="
    background:#FFFDE7;
    border-left:5px solid #F9A825;
    border-radius:6px;
    padding:14px 18px;
    margin-top:10px;
">
  <div style="color:#888;font-size:12px">{label}</div>
  <div style="color:#1A1A1A;font-size:28px;font-weight:700">{value}</div>
</div>""",
        unsafe_allow_html=True,
    )


def panel(title: str = "") -> None:
    """Render a section panel heading with a subtle green underline."""
    if title:
        st.markdown(
            f'<div style="font-size:16px;font-weight:600;color:#1A1A1A;'
            f'border-bottom:2px solid #C8E6C9;padding-bottom:6px;margin-bottom:12px">'
            f'{title}</div>',
            unsafe_allow_html=True,
        )

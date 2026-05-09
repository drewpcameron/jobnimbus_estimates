import streamlit as st
import pandas as pd
from measurement_engine import measure
from estimator import build_estimate


def _azimuth_label(az: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(az / 45) % 8]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Roof Estimator — JobNimbus",
    page_icon="https://content.partnerpage.io/eyJidWNrZXQiOiJwYXJ0bmVycGFnZS5wcm9kIiwia2V5IjoibWVkaWEvY29udGFjdF9pbWFnZXMvOGY5NTQyN2MtMTdkYS00ZGVhLWFmNDEtOGU4MTM1NGYxYTU3L2U3ZjhmNTE5LTExYjgtNGVjNC04NjQ3LTg3YjJhMDgyZDA0MC5qcGVnIiwiZWRpdHMiOnsidG9Gb3JtYXQiOiJ3ZWJwIiwicmVzaXplIjp7ImZpdCI6ImNvbnRhaW4iLCJiYWNrZ3JvdW5kIjp7InIiOjI1NSwiZyI6MjU1LCJiIjoyNTUsImFscGhhIjowfX19fQ==",
    layout="centered",
)

# ── Brand styles ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* JobNimbus brand colors */
    :root {
        --jn-blue:   #0066CC;
        --jn-navy:   #1a1a1a;
        --jn-gray:   #f5f5f5;
        --jn-border: #e0e0e0;
    }

    /* Hide default streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* Page background */
    .stApp { background-color: #ffffff; }

    /* Header bar */
    .jn-header {
        background-color: #0066CC;
        color: white;
        padding: 18px 24px;
        border-radius: 8px;
        margin-bottom: 24px;
    }
    .jn-header h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        color: white;
    }
    .jn-header p {
        margin: 4px 0 0;
        font-size: 0.9rem;
        color: rgba(255,255,255,0.85);
    }

    /* Metric cards */
    .jn-card {
        background: #f5f5f5;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: center;
    }
    .jn-card .label {
        font-size: 0.78rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .jn-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a1a1a;
    }
    .jn-card .sub {
        font-size: 0.82rem;
        color: #888;
        margin-top: 2px;
    }

    /* Section headers */
    .jn-section {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #0066CC;
        margin: 28px 0 10px;
        border-bottom: 2px solid #0066CC;
        padding-bottom: 4px;
    }

    /* Total row */
    .jn-total {
        background: #0066CC;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 16px;
    }
    .jn-total .label { font-size: 1rem; font-weight: 600; }
    .jn-total .amount { font-size: 1.6rem; font-weight: 700; }

    /* Button override */
    .stButton > button {
        background-color: #0066CC;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 28px;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #0052a3;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="jn-header">
    <h1>Roof Estimator</h1>
    <p>Powered by Google Solar API — aerial measurements in seconds</p>
</div>
""", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
address = st.text_input(
    "Property Address",
    placeholder="123 Main St, Houston, TX 77001",
    label_visibility="collapsed",
)
run = st.button("Get Estimate")

# ── Results ───────────────────────────────────────────────────────────────────
if run and address.strip():
    with st.spinner("Pulling aerial measurements..."):
        try:
            measurements = measure(address.strip())
            est = build_estimate(measurements)
        except ValueError as e:
            st.error(f"Could not retrieve data: {e}")
            st.stop()

    # ── Measurement summary cards ─────────────────────────────────────────────
    st.markdown('<div class="jn-section">Roof Measurements</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="jn-card">
            <div class="label">Total Area</div>
            <div class="value">{measurements['total_sqft']:,}</div>
            <div class="sub">sq ft</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="jn-card">
            <div class="label">Squares</div>
            <div class="value">{measurements['squares_with_waste']}</div>
            <div class="sub">incl. waste</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="jn-card">
            <div class="label">Dominant Pitch</div>
            <div class="value">{measurements['dominant_pitch_rise']}</div>
            <div class="sub">{measurements['dominant_pitch_deg']}°</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="jn-card">
            <div class="label">Complexity</div>
            <div class="value">{measurements['complexity'].title()}</div>
            <div class="sub">{measurements['segment_count']} segments</div>
        </div>""", unsafe_allow_html=True)

    # ── Segment breakdown ─────────────────────────────────────────────────────
    st.markdown('<div class="jn-section">Roof Segments</div>', unsafe_allow_html=True)
    seg_df = pd.DataFrame([
        {
            "Segment":   f"Plane {i+1}",
            "Pitch":     f"{s['pitch_rise']} ({s['pitch_degrees']:.1f}°)",
            "Area (sqft)": f"{s['area_sqft']:,.0f}",
            "Facing":    _azimuth_label(s['azimuth']),
        }
        for i, s in enumerate(measurements['segments'])
    ])
    st.dataframe(seg_df, use_container_width=True, hide_index=True)

    # ── Line-item estimate ────────────────────────────────────────────────────
    st.markdown('<div class="jn-section">Estimate</div>', unsafe_allow_html=True)
    est_df = pd.DataFrame([
        {
            "Line Item": item["item"],
            "Qty":       f"{item['qty']:.1f} {item['unit']}",
            "Rate":      f"${item['rate']:,.2f}",
            "Subtotal":  f"${item['subtotal']:,.2f}",
        }
        for item in est["line_items"]
    ])
    st.dataframe(est_df, use_container_width=True, hide_index=True)

    st.markdown(f"""
    <div style="text-align:right; color:#555; font-size:0.9rem; margin-top:8px;">
        Subtotal: <strong>${est['subtotal']:,.2f}</strong> &nbsp;|&nbsp;
        Overhead & Profit (20%): <strong>${est['overhead_profit']:,.2f}</strong>
    </div>
    <div class="jn-total">
        <span class="label">Total Estimate</span>
        <span class="amount">${est['total']:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

elif run and not address.strip():
    st.warning("Please enter a property address.")



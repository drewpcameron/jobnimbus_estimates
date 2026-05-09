import io
import os
import requests
import streamlit as st
import pandas as pd
from measurement_engine import geocode, measure_from_coords
from estimator import build_estimate


def _azimuth_label(az: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(az / 45) % 8]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Roof Estimator — JobNimbus",
    page_icon="https://content.partnerpage.io/eyJidWNrZXQiOiJwYXJ0bmVycGFnZS5wcm9kIiwia2V5IjoibWVkaWEvY29udGFjdF9pbWFnZXMvOGY5NTQyN2MtMTdkYS00ZGVhLWFmNDEtOGU4MTM1NGYxYTU3L2U3ZjhmNTE5LTExYjgtNGVjNC04NjQ3LTg3YjJhMDgyZDA0MC5qcGVnIiwiZWRpdHMiOnsidG9Gb3JtYXQiOiJ3ZWJwIiwicmVzaXplIjp7ImZpdCI6ImNvbnRhaW4iLCJiYWNrZ3JvdW5kIjp7InIiOjI1NSwiZyI6MjU1LCJiIjoyNTUsImFscGhhIjowfX19fQ==",
    layout="wide",
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

    /* Sans-serif everywhere */
    html, body, [class*="css"], .stApp, input, button, table, th, td {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }

    /* Hide default streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* Page background */
    .stApp {
        background-image: url("app/static/background.png");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Header — no background, just bold white text */
    .jn-header {
        background: none;
        border: none;
        padding: 18px 0 24px;
        margin-bottom: 8px;
    }
    .jn-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 800;
        color: #ffffff;
    }
    .jn-header p {
        margin: 4px 0 0;
        font-size: 0.95rem;
        font-weight: 600;
        color: rgba(255,255,255,0.85);
    }

    /* Metric cards */
    .jn-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px 20px;
        text-align: center;
    }
    .jn-card .label {
        font-size: 0.78rem;
        color: #0066CC;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .jn-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0066CC;
    }
    .jn-card .sub {
        font-size: 0.82rem;
        color: #0066CC;
        opacity: 0.65;
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

    /* Input field */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
    }
    .stTextInput > div > div > input::placeholder {
        color: #b0b0b0;
    }

    /* Slide-in animations */
    @keyframes slideFromCenter {
        from { opacity: 0; transform: translateX(25%); }
        to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideFromRight {
        from { opacity: 0; transform: translateX(60%); }
        to   { opacity: 1; transform: translateX(0); }
    }

    .slide-left {
        animation: slideFromCenter 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
    }
    .slide-right {
        animation: slideFromRight 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
    }

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

# ── Session state ─────────────────────────────────────────────────────────────
if "stage" not in st.session_state:
    st.session_state.stage = "input"
    st.session_state.address = ""
    st.session_state.lat = None
    st.session_state.lng = None
    st.session_state.measurements = None
    st.session_state.est = None

# ── Stage: input — centered ───────────────────────────────────────────────────
if st.session_state.stage == "input":
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("""
        <div class="jn-header">
            <h1>Roof Estimator</h1>
            <p>Powered by Google Solar API — aerial measurements in seconds</p>
        </div>
        """, unsafe_allow_html=True)
        address = st.text_input(
            "Property Address",
            placeholder="123 Main St, Houston, TX 77001",
            label_visibility="collapsed",
        )
        if st.button("Get Estimate"):
            if address.strip():
                with st.spinner("Looking up address..."):
                    try:
                        lat, lng = geocode(address.strip())
                        st.session_state.address = address.strip()
                        st.session_state.lat = lat
                        st.session_state.lng = lng
                        st.session_state.stage = "confirm"
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Could not find address: {e}")
            else:
                st.warning("Please enter a property address.")

# ── Stages: confirm + results — two-column ────────────────────────────────────
else:
    left, right = st.columns([1, 1])

    with left:
        st.markdown("""
        <div class="jn-header slide-left">
            <h1>Roof Estimator</h1>
            <p>Powered by Google Solar API — aerial measurements in seconds</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Stage: confirm ────────────────────────────────────────────────────
        if st.session_state.stage == "confirm":
            st.markdown(f"""
            <div class="slide-left" style="margin-bottom: 16px;">
                <div style="font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
                            letter-spacing: 0.08em; color: #ffffff; opacity: 0.75; margin-bottom: 4px;">
                    Address
                </div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">
                    {st.session_state.address}
                </div>
            </div>
            <div class="slide-left" style="font-size: 1rem; font-weight: 600; color: #ffffff; margin-bottom: 20px;">
                Is this the correct property?
            </div>
            """, unsafe_allow_html=True)

            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button("Yes, run estimate"):
                    with st.spinner("Pulling aerial measurements..."):
                        try:
                            measurements = measure_from_coords(
                                st.session_state.lat,
                                st.session_state.lng,
                                st.session_state.address,
                            )
                            est = build_estimate(measurements)
                            st.session_state.measurements = measurements
                            st.session_state.est = est
                            st.session_state.stage = "results"
                            st.rerun()
                        except ValueError as e:
                            st.error(f"Could not retrieve data: {e}")
            with no_col:
                if st.button("No, re-enter"):
                    st.session_state.stage = "input"
                    st.rerun()

        # ── Stage: results ────────────────────────────────────────────────────
        elif st.session_state.stage == "results":
            measurements = st.session_state.measurements
            est = st.session_state.est

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

            st.markdown('<div class="jn-section">Roof Segments</div>', unsafe_allow_html=True)
            seg_df = pd.DataFrame([
                {
                    "Segment":     f"Plane {i+1}",
                    "Pitch":       f"{s['pitch_rise']} ({s['pitch_degrees']:.1f}°)",
                    "Area (sqft)": f"{s['area_sqft']:,.0f}",
                    "Facing":      _azimuth_label(s['azimuth']),
                }
                for i, s in enumerate(measurements['segments'])
            ])
            st.dataframe(seg_df, use_container_width=True, hide_index=True)

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
            <div style="text-align:right; color:#ffffff; font-size:0.9rem; margin-top:8px; opacity:0.8;">
                Subtotal: <strong>${est['subtotal']:,.2f}</strong> &nbsp;|&nbsp;
                Overhead & Profit (20%): <strong>${est['overhead_profit']:,.2f}</strong>
            </div>
            <div class="jn-total">
                <span class="label">Total Estimate</span>
                <span class="amount">${est['total']:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
            if st.button("Start Over"):
                st.session_state.stage = "input"
                st.rerun()

    with right:
        api_key = os.getenv("GOOGLE_SOLAR_API_KEY")
        street_view_url = (
            f"https://maps.googleapis.com/maps/api/streetview"
            f"?size=640x480"
            f"&location={st.session_state.lat},{st.session_state.lng}"
            f"&fov=90&pitch=0&key={api_key}"
        )
        resp = requests.get(street_view_url, timeout=10)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            st.markdown('<div class="slide-right">', unsafe_allow_html=True)
            st.image(io.BytesIO(resp.content), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Street view not available for this address.")



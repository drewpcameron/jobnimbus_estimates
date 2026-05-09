import base64
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

    @keyframes shrinkIn {
        from { opacity: 0; transform: scale(1.5); transform-origin: top right; }
        to   { opacity: 1; transform: scale(1);   transform-origin: top right; }
    }
    .shrink-in { animation: shrinkIn 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both; }

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
    st.session_state.stage         = "input"
    st.session_state.address       = ""
    st.session_state.lat           = None
    st.session_state.lng           = None
    st.session_state.street_b64    = None
    st.session_state.measurements  = None
    st.session_state.est           = None


def _fetch_street_view_b64(lat, lng, api_key):
    url = (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=640x480&location={lat},{lng}&fov=90&pitch=0&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            return base64.b64encode(resp.content).decode()
    except Exception:
        pass
    return None


import base64

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
                        api_key = os.getenv("GOOGLE_SOLAR_API_KEY")
                        st.session_state.address    = address.strip()
                        st.session_state.lat        = lat
                        st.session_state.lng        = lng
                        st.session_state.street_b64 = _fetch_street_view_b64(lat, lng, api_key)
                        st.session_state.stage      = "confirm"
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Could not find address: {e}")
            else:
                st.warning("Please enter a property address.")

# ── Stage: confirm — two-column ───────────────────────────────────────────────
elif st.session_state.stage == "confirm":
    left, right = st.columns([1, 1])
    api_key = os.getenv("GOOGLE_SOLAR_API_KEY")

    with left:
        st.markdown("""
        <div class="jn-header slide-left">
            <h1>Roof Estimator</h1>
            <p>Powered by Google Solar API — aerial measurements in seconds</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="slide-left" style="margin-bottom:16px;">
            <div style="font-size:0.78rem; font-weight:700; text-transform:uppercase;
                        letter-spacing:0.08em; color:#ffffff; opacity:0.75; margin-bottom:4px;">
                Address
            </div>
            <div style="font-size:1.1rem; font-weight:700; color:#ffffff;">
                {st.session_state.address}
            </div>
        </div>
        <div class="slide-left" style="font-size:1rem; font-weight:600; color:#ffffff; margin-bottom:20px;">
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

    with right:
        if st.session_state.street_b64:
            st.markdown('<div class="slide-right">', unsafe_allow_html=True)
            st.image(io.BytesIO(base64.b64decode(st.session_state.street_b64)), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            b64 = _fetch_street_view_b64(st.session_state.lat, st.session_state.lng, api_key)
            if b64:
                st.session_state.street_b64 = b64
                st.markdown('<div class="slide-right">', unsafe_allow_html=True)
                st.image(io.BytesIO(base64.b64decode(b64)), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Street view not available for this address.")

# ── Stage: results — full width ───────────────────────────────────────────────
elif st.session_state.stage == "results":
    api_key      = os.getenv("GOOGLE_SOLAR_API_KEY")
    measurements = st.session_state.measurements
    est          = st.session_state.est

    # ── Property header ───────────────────────────────────────────────────────
    hdr_left, hdr_right = st.columns([2, 1])
    with hdr_left:
        st.markdown(f"""
        <div style="padding:4px 0 6px;">
            <div style="font-size:0.9rem; font-weight:700; text-transform:uppercase;
                        letter-spacing:0.08em; color:rgba(255,255,255,0.7); margin-bottom:6px;">
                Roofing Estimate
            </div>
            <div style="font-size:1.8rem; font-weight:800; color:#ffffff; line-height:1.2; margin-bottom:8px;">
                {st.session_state.address}
            </div>
            <div style="font-size:2.8rem; font-weight:800; color:#ffffff;">${est['total']:,.2f}</div>
            <div style="font-size:0.9rem; font-weight:600; text-transform:uppercase;
                        letter-spacing:0.06em; color:rgba(255,255,255,0.6); margin-top:2px;">
                Total Estimate (incl. 20% O&amp;P)
            </div>
        </div>
        """, unsafe_allow_html=True)
    with hdr_right:
        if st.session_state.street_b64:
            st.markdown('<div class="shrink-in">', unsafe_allow_html=True)
            st.image(
                io.BytesIO(base64.b64decode(st.session_state.street_b64)),
                width=350,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Measurement cards ─────────────────────────────────────────────────────
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

    # ── Linear footage bar ────────────────────────────────────────────────────
    lf = est["linear_footage"]
    st.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e0e0e0; border-radius:8px;
                padding:14px 20px; margin:16px 0;">
        <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase;
                    letter-spacing:0.08em; color:#0066CC; margin-bottom:10px;">
            Linear Footage
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:6px 0;">
            <div style="flex:1; min-width:80px; text-align:center; border-right:1px solid #e0e0e0; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['ridge_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Ridge</div>
            </div>
            <div style="flex:1; min-width:80px; text-align:center; border-right:1px solid #e0e0e0; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['hip_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Hip</div>
            </div>
            <div style="flex:1; min-width:80px; text-align:center; border-right:1px solid #e0e0e0; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['valley_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Valley</div>
            </div>
            <div style="flex:1; min-width:80px; text-align:center; border-right:1px solid #e0e0e0; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['rake_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Rake</div>
            </div>
            <div style="flex:1; min-width:80px; text-align:center; border-right:1px solid #e0e0e0; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['eave_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Eave</div>
            </div>
            <div style="flex:1; min-width:80px; text-align:center; border-right:1px solid #e0e0e0; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['flashing_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Flashing</div>
            </div>
            <div style="flex:1; min-width:80px; text-align:center; padding:0 8px;">
                <div style="font-size:1.1rem; font-weight:700; color:#0066CC;">{lf['step_flashing_lf']}</div>
                <div style="font-size:0.7rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Step Flash</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Segment breakdown ─────────────────────────────────────────────────────
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

    # ── Estimate table ────────────────────────────────────────────────────────
    st.markdown('<div class="jn-section">Estimate</div>', unsafe_allow_html=True)
    st.caption("Click any Rate cell to update your price — totals recalculate automatically.")

    est_df = pd.DataFrame([
        {
            "Line Item": item["item"],
            "Qty":       item["qty"],
            "Unit":      item["unit"],
            "Rate ($)":  item["rate"],
            "Subtotal":  item["subtotal"],
        }
        for item in est["line_items"]
    ])

    edited_df = st.data_editor(
        est_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Line Item": st.column_config.TextColumn(disabled=True),
            "Qty":       st.column_config.NumberColumn(disabled=True, format="%.2f"),
            "Unit":      st.column_config.TextColumn(disabled=True),
            "Rate ($)":  st.column_config.NumberColumn(min_value=0.0, format="$%.2f"),
            "Subtotal":  st.column_config.NumberColumn(disabled=True, format="$%.2f"),
        },
    )

    edited_df["Subtotal"] = (edited_df["Qty"] * edited_df["Rate ($)"]).round(2)
    subtotal = edited_df["Subtotal"].sum()

    op_pct = st.number_input(
        "Overhead & Profit %",
        min_value=0.0, max_value=100.0, value=20.0, step=1.0, format="%.1f",
    )

    overhead = round(subtotal * (op_pct / 100), 2)
    total    = round(subtotal + overhead, 2)

    st.markdown(f"""
    <div style="text-align:right; color:#ffffff; font-size:0.9rem; margin-top:8px; opacity:0.8;">
        Subtotal: <strong>${subtotal:,.2f}</strong> &nbsp;|&nbsp;
        Overhead & Profit ({op_pct:.0f}%): <strong>${overhead:,.2f}</strong>
    </div>
    <div class="jn-total">
        <span class="label">Total Estimate</span>
        <span class="amount">${total:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    if st.button("Start Over"):
        st.session_state.stage = "input"
        st.rerun()



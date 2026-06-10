import streamlit as st
import gc
import json
import pandas as pd
from scraper import run_scraper
from excel_builder import build_excel

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GMAT Club Scraper",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #F0F4FA; }

.hero {
    background: linear-gradient(135deg, #1B3A6B 0%, #2E5FA3 60%, #4A80C4 100%);
    border-radius: 16px; padding: 32px 36px 24px; margin-bottom: 24px; color: white;
}
.hero h1 { font-size: 1.9rem; font-weight: 700; margin: 0 0 6px; }
.hero p  { font-size: 0.95rem; opacity: 0.85; margin: 0; }

.card {
    background: white; border-radius: 12px; padding: 22px;
    box-shadow: 0 2px 12px rgba(27,58,107,0.08); margin-bottom: 18px;
}
.card-title {
    font-size: 0.82rem; font-weight: 700; color: #2E5FA3;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px;
}

.step-badge {
    display: inline-block; background: #1B3A6B; color: white;
    border-radius: 50%; width: 24px; height: 24px; text-align: center;
    line-height: 24px; font-size: 0.8rem; font-weight: 700;
    margin-right: 8px;
}
.step-row { display: flex; align-items: flex-start; margin-bottom: 10px; font-size: 0.9rem; }
.step-text { flex: 1; padding-top: 2px; }

.status-box {
    background: #F0F7FF; border-left: 4px solid #2E5FA3;
    border-radius: 0 8px 8px 0; padding: 9px 14px;
    font-size: 0.86rem; color: #1B3A6B; margin: 4px 0;
}
.warn {
    background: #FFF4E5; border-left: 4px solid #F4A300;
    border-radius: 0 8px 8px 0; padding: 9px 14px;
    font-size: 0.86rem; color: #7A4F00;
}
.err {
    background: #FFF0F0; border-left: 4px solid #D93025;
    border-radius: 0 8px 8px 0; padding: 9px 14px;
    font-size: 0.86rem; color: #7A0000;
}
.success {
    background: #F0FFF4; border-left: 4px solid #0A7C42;
    border-radius: 0 8px 8px 0; padding: 9px 14px;
    font-size: 0.86rem; color: #0A4A28;
}

.stat-block { text-align: center; padding: 14px; background: #F0F4FA; border-radius: 10px; }
.stat-num   { font-size: 1.9rem; font-weight: 700; color: #1B3A6B; }
.stat-label { font-size: 0.78rem; color: #666; margin-top: 2px; }

.stDownloadButton > button {
    background: linear-gradient(135deg, #1B3A6B, #2E5FA3) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; padding: 12px 28px !important;
    font-size: 1rem !important; font-weight: 600 !important; width: 100%;
}
.stButton > button { border-radius: 10px !important; font-weight: 600 !important; }
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    for k, v in {
        "scraped_data": None,
        "excel_bytes":  None,
        "log_messages": [],
        "scraping":     False,
        "done":         False,
        "error":        None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def reset_all():
    st.session_state.scraped_data = None
    st.session_state.excel_bytes  = None
    st.session_state.log_messages = []
    st.session_state.scraping     = False
    st.session_state.done         = False
    st.session_state.error        = None
    gc.collect()

def log(msg):
    st.session_state.log_messages.append(msg)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>📚 GMAT Club Question Scraper</h1>
    <p>Collect PS · CR · RC questions and export to structured Excel — runs on Streamlit Cloud</p>
</div>
""", unsafe_allow_html=True)

# ── Layout ────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.5], gap="large")

with left:

    # ── Step-by-step cookie instructions ──
    st.markdown("""
    <div class="card">
        <div class="card-title">🍪 How to Get Your Cookies (One-Time Setup)</div>
        <div class="step-row">
            <span class="step-badge">1</span>
            <span class="step-text">Install the <b>EditThisCookie</b> or <b>Cookie-Editor</b> Chrome extension</span>
        </div>
        <div class="step-row">
            <span class="step-badge">2</span>
            <span class="step-text">Go to <b>gmatclub.com</b> and <b>log in</b> with your account</span>
        </div>
        <div class="step-row">
            <span class="step-badge">3</span>
            <span class="step-text">Click the extension icon → click <b>Export</b> → <b>Export JSON</b> → saves a .json file</span>
        </div>
        <div class="step-row">
            <span class="step-badge">4</span>
            <span class="step-text">Upload that .json file below using the <b>Upload JSON File</b> tab</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Cookie input ──
    st.markdown('<div class="card"><div class="card-title">🔐 Upload or Paste Cookies</div>', unsafe_allow_html=True)

    # Upload tab vs paste tab
    cookie_tab1, cookie_tab2 = st.tabs(["📁 Upload JSON File", "📋 Paste JSON Text"])

    cookie_input = ""
    with cookie_tab1:
        uploaded_file = st.file_uploader(
            "Upload your exported cookie JSON file",
            type=["json", "txt"],
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            cookie_input = uploaded_file.read().decode("utf-8")
            st.markdown('<div class="success">✅ File loaded successfully!</div>', unsafe_allow_html=True)

    with cookie_tab2:
        pasted = st.text_area(
            "Paste cookie JSON here",
            height=130,
            placeholder='[{"name": "phpbb3_...", "value": "...", ...}, ...]',
            label_visibility="collapsed",
        )
        if pasted.strip():
            cookie_input = pasted

    cookie_format = st.radio(
        "Cookie format",
        ["JSON Array (Cookie-Editor)", "Simple key=value pairs"],
        horizontal=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Sections ──
    st.markdown('<div class="card"><div class="card-title">📂 Sections to Scrape</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    do_ps = c1.checkbox("PS", value=True)
    do_cr = c2.checkbox("CR", value=True)
    do_rc = c3.checkbox("RC", value=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Settings ──
    st.markdown('<div class="card"><div class="card-title">⚙️ Settings</div>', unsafe_allow_html=True)
    max_pages = st.slider("Pages per section", 1, 10, 2,
        help="1 page ≈ 25 questions. More pages = more time.")
    st.markdown(f"""
    <div class="warn">⏱ Est. time: ~{max_pages * 4}–{max_pages * 6} min per section</div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    sections_selected = [s for s, f in [("PS", do_ps), ("CR", do_cr), ("RC", do_rc)] if f]

    run_btn   = st.button("🚀 Start Scraping", use_container_width=True, type="primary",
                          disabled=st.session_state.scraping)
    clear_btn = st.button("🗑️ Clear & Reset", use_container_width=True,
                          disabled=st.session_state.scraping)

    if clear_btn:
        reset_all()
        st.rerun()


with right:
    # ── Log ──
    st.markdown('<div class="card"><div class="card-title">📋 Activity Log</div>', unsafe_allow_html=True)
    log_placeholder = st.empty()

    def render_log():
        if st.session_state.log_messages:
            html = "".join(f'<div class="status-box">{m}</div>'
                           for m in st.session_state.log_messages[-12:])
            log_placeholder.markdown(html, unsafe_allow_html=True)
        else:
            log_placeholder.markdown(
                '<div class="status-box" style="opacity:0.5">Waiting to start...</div>',
                unsafe_allow_html=True)

    render_log()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Results ──
    if st.session_state.done and st.session_state.scraped_data:
        data = st.session_state.scraped_data
        ps_n = len(data.get("PS", []))
        cr_n = len(data.get("CR", []))
        rc_n = len(data.get("RC", []))
        total = ps_n + cr_n + rc_n

        st.markdown('<div class="card"><div class="card-title">📊 Results</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        for col, label, val in zip([c1,c2,c3,c4], ["Total","PS","CR","RC"], [total,ps_n,cr_n,rc_n]):
            col.markdown(f"""
            <div class="stat-block">
                <div class="stat-num">{val}</div>
                <div class="stat-label">{label}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Preview
        st.markdown('<div class="card"><div class="card-title">👀 Preview</div>', unsafe_allow_html=True)
        tab_labels = [f"{s} ({len(data[s])})" for s in ["PS","CR","RC"] if data.get(s)]
        if tab_labels:
            tabs = st.tabs(tab_labels)
            idx = 0
            for sec in ["PS","CR","RC"]:
                if data.get(sec):
                    with tabs[idx]:
                        df = pd.DataFrame(data[sec])[["Title","Answer","Difficulty","Type"]].head(10)
                        st.dataframe(df, use_container_width=True)
                    idx += 1
        st.markdown('</div>', unsafe_allow_html=True)

        # Download
        if st.session_state.excel_bytes:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.download_button(
                label="⬇️ Download Excel (Quantitative + Verbal sheets)",
                data=st.session_state.excel_bytes,
                file_name="GMAT_Club_Questions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.error:
        st.markdown(f'<div class="err">❌ {st.session_state.error}</div>', unsafe_allow_html=True)


# ── Parse cookies helper ──────────────────────────────────────────────────────
def parse_cookies(raw: str, fmt: str) -> dict:
    raw = raw.strip()
    cookies = {}

    if fmt == "JSON Array (Cookie-Editor)":
        # Handle both array [...] and object {...} formats
        data = json.loads(raw)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies[item["name"]] = item["value"]
        elif isinstance(data, dict):
            cookies = data
    else:
        # Simple key=value; key=value or key=value\nkey=value
        for part in re.split(r'[;\n]', raw):
            if '=' in part:
                k, _, v = part.strip().partition('=')
                cookies[k.strip()] = v.strip()

    return cookies


# ── Run ───────────────────────────────────────────────────────────────────────
if run_btn:
    if not cookie_input.strip():
        st.warning("Please paste your cookies first.")
    elif not sections_selected:
        st.warning("Select at least one section.")
    else:
        reset_all()

        # Parse cookies
        try:
            cookies_dict = parse_cookies(cookie_input.strip(), cookie_format)
            if not cookies_dict:
                st.error("Could not parse cookies. Make sure you copied the full JSON.")
                st.stop()
        except Exception as e:
            st.error(f"Cookie parse error: {e}. Try the 'Simple key=value' format instead.")
            st.stop()

        st.session_state.scraping = True

        with st.spinner("Scraping in progress..."):
            try:
                data = run_scraper(
                    cookies_dict=cookies_dict,
                    sections=sections_selected,
                    max_pages=max_pages,
                    progress_callback=log,
                )
                st.session_state.scraped_data = data
                log("📊 Building Excel...")
                st.session_state.excel_bytes = build_excel(data)
                log("✅ Done! Download your Excel below.")
                st.session_state.done     = True
                st.session_state.scraping = False
            except Exception as e:
                st.session_state.error    = str(e)
                st.session_state.scraping = False
                log(f"❌ {e}")
            finally:
                gc.collect()

        st.rerun()

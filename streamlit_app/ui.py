import streamlit as st

_LOGO_SVG = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 3.2 1.5 8.4 12 13.6l8.5-4.25V15.9h1.5V8.4L12 3.2Z" fill="white"/>
  <path d="M5.25 10.7v4.15c0 2.06 3.02 3.7 6.75 3.7s6.75-1.64 6.75-3.7V10.7L12 15.15 5.25 10.7Z" fill="white" fill-opacity="0.82"/>
</svg>
"""


def apply_theme(page_title: str, page_icon: str = "🎓"):
    st.set_page_config(page_title=f"{page_title} · Study Genie", page_icon=page_icon, layout="wide")
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --sg-bg: #F6F5F2;
            --sg-canvas: radial-gradient(circle at 8% -10%, rgba(79, 70, 229, 0.08), transparent 32%),
                         radial-gradient(circle at 96% 0%, rgba(245, 158, 11, 0.10), transparent 34%),
                         linear-gradient(180deg, #FBFAF8 0%, #F6F5F2 55%, #F3F1EC 100%);
            --sg-surface: #FFFFFF;
            --sg-surface-soft: #FBFAF8;
            --sg-ink: #16181D;
            --sg-ink-soft: #454955;
            --sg-muted: #80838D;
            --sg-border: rgba(22, 24, 29, 0.09);
            --sg-border-strong: rgba(22, 24, 29, 0.14);
            --sg-primary: #4F46E5;
            --sg-primary-strong: #4338CA;
            --sg-primary-soft: rgba(79, 70, 229, 0.10);
            --sg-amber: #D97706;
            --sg-amber-soft: rgba(217, 119, 6, 0.12);
            --sg-teal: #0D9488;
            --sg-teal-soft: rgba(13, 148, 136, 0.12);
            --sg-danger: #DC4C4C;
            --sg-success: #15803D;
            --sg-shadow-sm: 0 1px 2px rgba(22, 24, 29, 0.04), 0 1px 1px rgba(22, 24, 29, 0.03);
            --sg-shadow-md: 0 8px 24px rgba(22, 24, 29, 0.06), 0 2px 6px rgba(22, 24, 29, 0.04);
            --sg-shadow-lg: 0 18px 44px rgba(22, 24, 29, 0.10), 0 4px 12px rgba(22, 24, 29, 0.05);
            --sg-radius-sm: 12px;
            --sg-radius-md: 16px;
            --sg-radius-lg: 22px;
            --sg-font-display: 'Plus Jakarta Sans', 'Inter', sans-serif;
            --sg-font-body: 'Inter', sans-serif;
        }

        html, body, [class*="css"] {
            font-family: var(--sg-font-body);
        }

        .stApp {
            background: var(--sg-canvas);
            background-attachment: fixed;
            color: var(--sg-ink);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1180px;
        }

        h1, h2, h3, h4 {
            font-family: var(--sg-font-display);
            color: var(--sg-ink);
            letter-spacing: -0.02em;
            font-weight: 700;
        }

        p, span, div, label {
            color: var(--sg-ink-soft);
        }

        a { color: var(--sg-primary); }

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {
            background: var(--sg-surface);
            border-right: 1px solid var(--sg-border);
        }
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem;
        }
        .sg-sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            padding: 1.05rem 1rem 1.15rem 1rem;
            margin-bottom: 0.2rem;
            border-bottom: 1px solid var(--sg-border);
        }
        .sg-sidebar-brand-mark {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            background: linear-gradient(135deg, var(--sg-primary), #7C6CF0);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 14px rgba(79, 70, 229, 0.28);
            flex-shrink: 0;
        }
        .sg-sidebar-brand-mark svg { width: 21px; height: 21px; }
        .sg-sidebar-brand-text .sg-sidebar-title {
            font-family: var(--sg-font-display);
            font-weight: 800;
            font-size: 1.08rem;
            color: var(--sg-ink);
            line-height: 1.15;
            letter-spacing: -0.01em;
        }
        .sg-sidebar-brand-text .sg-sidebar-tagline {
            font-size: 0.73rem;
            color: var(--sg-muted);
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        [data-testid="stSidebarNav"] { padding-top: 0.2rem; }
        [data-testid="stSidebarNavItems"] { padding: 0 0.35rem; }

        header[data-testid="stNavSectionHeader"] {
            padding: 1rem 0.65rem 0.35rem 0.65rem !important;
        }
        header[data-testid="stNavSectionHeader"] span {
            font-family: var(--sg-font-display);
            font-size: 0.7rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: var(--sg-muted) !important;
        }

        [data-testid="stSidebarNavLinkContainer"] { padding: 0.05rem 0; }
        a[data-testid="stSidebarNavLink"] {
            border-radius: 10px !important;
            margin: 0 0.35rem !important;
            padding: 0.5rem 0.65rem !important;
            font-weight: 500;
            transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease;
        }
        a[data-testid="stSidebarNavLink"]:hover {
            background: var(--sg-primary-soft) !important;
            transform: translateX(1px);
        }
        a[data-testid="stSidebarNavLink"][aria-current="page"] {
            background: var(--sg-primary-soft) !important;
            font-weight: 700;
            box-shadow: inset 2px 0 0 var(--sg-primary);
        }
        a[data-testid="stSidebarNavLink"][aria-current="page"] span {
            color: var(--sg-primary-strong) !important;
        }
        [data-testid="stSidebarNavSeparator"],
        [data-testid="stSidebarHeader"] { border-color: var(--sg-border); }

        /* ---------- Generic surfaces ---------- */
        div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
            border-radius: var(--sg-radius-md);
            border-color: var(--sg-border) !important;
            background: var(--sg-surface);
            box-shadow: var(--sg-shadow-sm);
        }

        div[data-testid="stMetric"] {
            background: var(--sg-surface);
            border: 1px solid var(--sg-border);
            border-top: 3px solid var(--sg-primary);
            border-radius: var(--sg-radius-sm);
            padding: 0.95rem 1.05rem;
            box-shadow: var(--sg-shadow-sm);
        }
        div[data-testid="stMetricLabel"] {
            color: var(--sg-muted);
            font-weight: 600;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        div[data-testid="stMetricValue"] {
            color: var(--sg-ink);
            font-family: var(--sg-font-display);
            font-weight: 700;
        }

        /* ---------- Hero ---------- */
        .sg-hero {
            position: relative;
            padding: 2.1rem 2.3rem;
            border: 1px solid var(--sg-border);
            border-radius: var(--sg-radius-lg);
            background:
                radial-gradient(circle at 100% 0%, rgba(79, 70, 229, 0.10), transparent 45%),
                radial-gradient(circle at 0% 100%, rgba(217, 119, 6, 0.08), transparent 40%),
                var(--sg-surface);
            box-shadow: var(--sg-shadow-lg);
            margin-bottom: 1.6rem;
            overflow: hidden;
        }
        .sg-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.32rem 0.7rem 0.32rem 0.55rem;
            border-radius: 999px;
            background: var(--sg-primary-soft);
            color: var(--sg-primary-strong);
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-bottom: 0.9rem;
        }
        .sg-eyebrow::before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--sg-primary);
            display: inline-block;
        }
        .sg-hero h1 {
            margin: 0 0 0.55rem 0;
            font-size: 2.35rem;
            line-height: 1.08;
        }
        .sg-hero p {
            margin: 0;
            color: var(--sg-ink-soft);
            font-size: 1.03rem;
            line-height: 1.65;
            max-width: 62ch;
        }

        /* ---------- Two-column hero (home page) ---------- */
        .sg-hero-grid {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2.5rem;
        }
        .sg-hero-text { flex: 1 1 56%; min-width: 280px; }
        .sg-hero-text p { max-width: 54ch; }
        .sg-hero-visual {
            flex: 0 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.15rem;
        }
        .sg-hero-badge {
            width: 104px;
            height: 104px;
            border-radius: 28px;
            background: linear-gradient(135deg, var(--sg-primary), #7C6CF0);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 16px 34px rgba(79, 70, 229, 0.30);
        }
        .sg-hero-badge svg { width: 50px; height: 50px; }
        .sg-hero-pillars {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            width: 226px;
        }
        .sg-pillar {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.55rem 0.75rem;
            border-radius: 12px;
            background: var(--sg-surface-soft);
            border: 1px solid var(--sg-border);
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--sg-ink-soft);
        }
        .sg-pillar-icon {
            width: 26px;
            height: 26px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
            flex-shrink: 0;
        }
        @media (max-width: 920px) {
            .sg-hero-grid { flex-direction: column; align-items: flex-start; }
            .sg-hero-visual { flex-direction: row; align-items: center; width: 100%; }
            .sg-hero-pillars { width: auto; flex: 1; }
        }

        .sg-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 1.1rem 0 0.1rem 0;
        }
        .sg-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.36rem 0.78rem;
            border-radius: 999px;
            background: var(--sg-surface-soft);
            border: 1px solid var(--sg-border);
            color: var(--sg-ink-soft);
            font-size: 0.83rem;
            font-weight: 600;
        }
        .sg-chip.sg-chip-primary { background: var(--sg-primary-soft); color: var(--sg-primary-strong); border-color: transparent; }
        .sg-chip.sg-chip-amber { background: var(--sg-amber-soft); color: var(--sg-amber); border-color: transparent; }
        .sg-chip.sg-chip-teal { background: var(--sg-teal-soft); color: var(--sg-teal); border-color: transparent; }

        /* ---------- Section headers ---------- */
        .sg-section {
            margin-top: 0.3rem;
            margin-bottom: 0.6rem;
            padding-left: 0.85rem;
            border-left: 3px solid var(--sg-primary);
        }
        .sg-section h2 {
            font-size: 1.32rem;
            margin: 0 0 0.15rem 0;
        }
        .sg-section small {
            color: var(--sg-muted);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        /* ---------- Cards ---------- */
        .sg-card {
            padding: 1.15rem 1.25rem;
            border-radius: var(--sg-radius-md);
            border: 1px solid var(--sg-border);
            background: var(--sg-surface);
            box-shadow: var(--sg-shadow-sm);
            transition: box-shadow 0.18s ease, transform 0.18s ease;
        }
        .sg-card:hover { box-shadow: var(--sg-shadow-md); transform: translateY(-1px); }
        .sg-card strong { color: var(--sg-ink); }
        .sg-label {
            color: var(--sg-muted);
            text-transform: uppercase;
            letter-spacing: 0.07em;
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        /* ---------- Feature grid (home page) ---------- */
        div[data-testid="stElementContainer"]:has(.sg-feature-card) {
            display: flex;
            flex-direction: column;
            flex: 1 1 auto;
        }
        div[data-testid="stElementContainer"]:has(.sg-feature-card) .stMarkdown,
        div[data-testid="stElementContainer"]:has(.sg-feature-card) [data-testid="stMarkdownContainer"],
        div[data-testid="stElementContainer"]:has(.sg-feature-card) [data-testid="stMarkdownContainer"] > div {
            display: flex;
            flex-direction: column;
            flex: 1;
        }
        .sg-feature-card {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 272px;
            box-sizing: border-box;
            padding: 1.3rem 1.35rem;
            border-radius: var(--sg-radius-md);
            border: 1px solid var(--sg-border);
            background: var(--sg-surface);
            box-shadow: var(--sg-shadow-sm);
            transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
            text-decoration: none !important;
            cursor: pointer;
        }
        .sg-feature-card:hover {
            box-shadow: var(--sg-shadow-md);
            transform: translateY(-2px);
            border-color: var(--sg-primary);
        }
        .sg-feature-card:active { transform: translateY(0); }
        .sg-feature-icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
            margin-bottom: 0.85rem;
            flex-shrink: 0;
        }
        .sg-feature-title {
            font-family: var(--sg-font-display);
            font-weight: 700;
            font-size: 1.05rem;
            color: var(--sg-ink);
            margin-bottom: 0.3rem;
        }
        .sg-feature-body {
            font-size: 0.88rem;
            color: var(--sg-muted);
            line-height: 1.55;
            flex: 1;
        }

        /* ---------- Status pill ---------- */
        .sg-status-row { display: flex; flex-wrap: wrap; gap: 0.6rem; margin: 0.2rem 0 1.6rem 0; }
        .sg-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.4rem 0.85rem;
            border-radius: 999px;
            background: var(--sg-surface);
            border: 1px solid var(--sg-border);
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--sg-ink-soft);
            box-shadow: var(--sg-shadow-sm);
        }
        .sg-status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .sg-status-dot.on { background: var(--sg-success); box-shadow: 0 0 0 3px rgba(21, 128, 61, 0.15); }
        .sg-status-dot.off { background: var(--sg-danger); box-shadow: 0 0 0 3px rgba(220, 76, 76, 0.15); }
        .sg-status-dot.warn { background: var(--sg-amber); box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.15); }

        /* ---------- Chat bubbles ---------- */
        .sg-chat-user, .sg-chat-assistant {
            padding: 0.9rem 1.05rem;
            border-radius: 18px;
            margin-bottom: 0.75rem;
            max-width: 92%;
        }
        .sg-chat-user {
            border-radius: 18px 18px 6px 18px;
            background: linear-gradient(135deg, var(--sg-primary), #6D5DFB);
            color: #fff;
            margin-left: auto;
            box-shadow: var(--sg-shadow-sm);
        }
        .sg-chat-user .sg-label, .sg-chat-user div { color: rgba(255,255,255,0.92); }
        .sg-chat-assistant {
            border-radius: 18px 18px 18px 6px;
            background: var(--sg-surface);
            border: 1px solid var(--sg-border);
        }

        /* ---------- Buttons ---------- */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
            border-radius: 11px !important;
            font-weight: 600 !important;
            border: 1px solid var(--sg-border-strong) !important;
            transition: transform 0.12s ease, box-shadow 0.12s ease !important;
            box-shadow: var(--sg-shadow-sm);
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: var(--sg-shadow-md);
        }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--sg-primary), var(--sg-primary-strong)) !important;
            border: none !important;
            color: #FFFFFF !important;
        }
        .stButton > button[kind="primary"] *, .stFormSubmitButton > button[kind="primary"] * {
            color: #FFFFFF !important;
        }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.3rem;
            background: var(--sg-surface-soft);
            padding: 0.3rem;
            border-radius: 999px;
            border: 1px solid var(--sg-border);
            width: fit-content;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 0.45rem 1.1rem;
            font-weight: 600;
            color: var(--sg-ink-soft);
        }
        .stTabs [aria-selected="true"] {
            background: var(--sg-surface) !important;
            color: var(--sg-primary-strong) !important;
            box-shadow: var(--sg-shadow-sm);
        }

        /* ---------- Inputs & misc widgets ---------- */
        div[data-baseweb="base-input"],
        div[data-baseweb="input"],
        div[data-baseweb="textarea"],
        div[data-baseweb="select"] > div {
            border-radius: 10px !important;
            border: 1px solid var(--sg-border-strong) !important;
            background: var(--sg-surface) !important;
        }
        div[data-baseweb="base-input"]:focus-within,
        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="textarea"]:focus-within {
            border-color: var(--sg-primary) !important;
            box-shadow: 0 0 0 1px var(--sg-primary) !important;
        }
        .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input {
            background: transparent !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            border-radius: var(--sg-radius-sm) !important;
            background: var(--sg-surface-soft) !important;
            border: 1.5px dashed var(--sg-border-strong) !important;
        }
        .stDataFrame, [data-testid="stDataFrame"] {
            border-radius: var(--sg-radius-sm) !important;
            overflow: hidden;
            border: 1px solid var(--sg-border);
        }
        .stAlert {
            border-radius: var(--sg-radius-sm) !important;
            border: 1px solid var(--sg-border);
        }

        .sg-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--sg-border-strong), transparent);
            margin: 1.4rem 0 1.5rem 0;
        }

        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="sg-sidebar-brand">
            <div class="sg-sidebar-brand-mark">{_LOGO_SVG}</div>
            <div class="sg-sidebar-brand-text">
                <div class="sg-sidebar-title">Study Genie</div>
                <div class="sg-sidebar-tagline">Classroom Intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    auth_header()


def _initials(name: str) -> str:
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def auth_header():
    """Top-right account control shown on every page: login button, or a profile popover once signed in."""
    user = st.session_state.get("auth_user")
    _, right_col = st.columns([6, 1])
    with right_col:
        if user:
            with st.popover(_initials(user["name"]), use_container_width=True):
                st.markdown(f"**{user['name']}**")
                st.caption(user["email"])
                st.caption(f"Demo profile: `{user['demo_student_id']}`")
                st.markdown('<div class="sg-divider"></div>', unsafe_allow_html=True)
                if st.button("View Full Profile", use_container_width=True, key="auth_view_profile"):
                    st.switch_page("pages/15_Profile.py")
                if st.button("Log Out", use_container_width=True, key="auth_logout"):
                    st.session_state.pop("auth_user", None)
                    st.switch_page("home_page.py")
        else:
            if st.button("Log In", use_container_width=True, key="auth_login_btn"):
                st.switch_page("pages/14_Login.py")


def require_login(feature_name: str) -> dict:
    """Blocks the rest of the page with a login wall unless the user is signed in.
    Returns the logged-in user dict when authenticated; otherwise stops the script."""
    user = st.session_state.get("auth_user")
    if user:
        return user

    with st.container(border=True):
        st.markdown(f"### Log in to view {feature_name}")
        st.caption("This page is personalized to your account, so it's only available once you're signed in.")
        if st.button("Log In / Sign Up", type="primary", key=f"gate_login_{feature_name}"):
            st.switch_page("pages/14_Login.py")
    st.stop()


def hero(title: str, subtitle: str, eyebrow: str = "Study Genie", chips: list[str] | None = None):
    chips_html = ""
    if chips:
        palette = ["sg-chip-primary", "sg-chip-amber", "sg-chip-teal"]
        chips_html = '<div class="sg-chip-row">' + "".join(
            f'<span class="sg-chip {palette[i % len(palette)]}">{chip}</span>' for i, chip in enumerate(chips)
        ) + "</div>"
    st.markdown(
        f"""
        <section class="sg-hero">
            <div class="sg-eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
            {chips_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def hero_home(title: str, subtitle: str, eyebrow: str, chips: list[str] | None = None):
    """Two-column landing hero: text + chips on the left, a visual panel on the right."""
    chips_html = ""
    if chips:
        palette = ["sg-chip-primary", "sg-chip-amber", "sg-chip-teal"]
        chips_html = '<div class="sg-chip-row">' + "".join(
            f'<span class="sg-chip {palette[i % len(palette)]}">{chip}</span>' for i, chip in enumerate(chips)
        ) + "</div>"

    pillars = [
        ("📖", "Learn from lectures & PDFs"),
        ("✍️", "Practice with flashcards & quizzes"),
        ("📈", "Understand risk & performance"),
    ]
    pillars_html = "".join(
        f"""<div class="sg-pillar"><span class="sg-pillar-icon">{icon}</span>{label}</div>"""
        for icon, label in pillars
    )

    st.markdown(
        f"""
        <section class="sg-hero">
            <div class="sg-hero-grid">
                <div class="sg-hero-text">
                    <div class="sg-eyebrow">{eyebrow}</div>
                    <h1>{title}</h1>
                    <p>{subtitle}</p>
                    {chips_html}
                </div>
                <div class="sg-hero-visual">
                    <div class="sg-hero-badge">{_LOGO_SVG}</div>
                    <div class="sg-hero-pillars">{pillars_html}</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str | None = None):
    subtitle_html = f"<small>{subtitle}</small>" if subtitle else ""
    st.markdown(
        f"""
        <div class="sg-section">
            <h2>{title}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def chip_row(items: list[str]):
    if not items:
        return
    palette = ["sg-chip-primary", "sg-chip-amber", "sg-chip-teal"]
    st.markdown(
        '<div class="sg-chip-row">' + "".join(
            f'<span class="sg-chip {palette[i % len(palette)]}">{item}</span>' for i, item in enumerate(items)
        ) + "</div>",
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str):
    st.markdown(
        f"""
        <div class="sg-card">
            <div class="sg-label">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(icon: str, title: str, body: str, href: str, accent: str = "primary"):
    """Renders the whole card as a single clickable link to `href` (an app page path, e.g. '/Doubt_Solver_API')."""
    soft = {"primary": "var(--sg-primary-soft)", "amber": "var(--sg-amber-soft)", "teal": "var(--sg-teal-soft)"}[accent]
    color = {"primary": "var(--sg-primary-strong)", "amber": "var(--sg-amber)", "teal": "var(--sg-teal)"}[accent]
    st.markdown(
        f"""
        <a class="sg-feature-card" href="{href}" target="_self">
            <div class="sg-feature-icon" style="background:{soft};color:{color};">{icon}</div>
            <div class="sg-feature-title">{title}</div>
            <div class="sg-feature-body">{body}</div>
        </a>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label: str, state: str = "on"):
    """state: 'on' | 'off' | 'warn'"""
    st.markdown(
        f"""
        <span class="sg-status-pill"><span class="sg-status-dot {state}"></span>{label}</span>
        """,
        unsafe_allow_html=True,
    )


def status_row(pills: list[tuple[str, str]]):
    html = '<div class="sg-status-row">' + "".join(
        f'<span class="sg-status-pill"><span class="sg-status-dot {state}"></span>{label}</span>'
        for label, state in pills
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def chat_bubble(role: str, content: str, sources: list | None = None):
    css_class = "sg-chat-user" if role == "user" else "sg-chat-assistant"
    label = "You" if role == "user" else "Study Genie"
    sources_html = ""
    if sources:
        formatted_sources = []
        for source in sources:
            if isinstance(source, dict):
                formatted_sources.append(f"{source.get('pdf_name', 'PDF')} • p.{source.get('page', '?')}")
            else:
                formatted_sources.append(f"Page {source}")
        sources_html = f"<div class='sg-label'>Sources: {', '.join(formatted_sources)}</div>"
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="sg-label">{label}</div>
            <div>{content}</div>
            {sources_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

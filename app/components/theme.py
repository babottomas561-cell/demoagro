from __future__ import annotations

import streamlit as st


def apply_page_theme(page_title: str) -> None:
    st.set_page_config(
        page_title=f"Demoagro | {page_title}",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(138, 160, 98, 0.14), transparent 28%),
                radial-gradient(circle at bottom left, rgba(201, 109, 74, 0.12), transparent 22%),
                linear-gradient(180deg, #f7f4ed 0%, #f3efe6 100%);
        }

        html, body, [class*="css"] {
            font-family: "IBM Plex Sans", sans-serif;
            color: #203126;
        }

        h1, h2, h3, h4 {
            font-family: "Bricolage Grotesque", sans-serif !important;
            letter-spacing: -0.02em;
        }

        .hero-card {
            background: linear-gradient(135deg, #203126 0%, #43553f 100%);
            border: 1px solid rgba(32, 49, 38, 0.08);
            border-radius: 20px;
            padding: 1.4rem 1.5rem;
            color: #f4efe3;
            box-shadow: 0 14px 34px rgba(32, 49, 38, 0.12);
            margin-bottom: 1rem;
        }

        .hero-overline {
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.72rem;
            color: rgba(244, 239, 227, 0.72);
        }

        .hero-title {
            font-size: 2rem;
            line-height: 1.05;
            margin: 0.35rem 0 0.35rem 0;
        }

        .hero-subtitle {
            color: rgba(244, 239, 227, 0.84);
            max-width: 56rem;
            margin: 0;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
            color: #203126;
        }

        .section-caption {
            color: #68756c;
            margin-bottom: 0.9rem;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(32, 49, 38, 0.08);
            border-radius: 16px;
            padding: 1rem 1rem 0.95rem 1rem;
            box-shadow: 0 12px 28px rgba(32, 49, 38, 0.06);
            min-height: 132px;
        }

        .metric-card.success { border-left: 6px solid #5e7b42; }
        .metric-card.warning { border-left: 6px solid #b07a26; }
        .metric-card.danger { border-left: 6px solid #b34f36; }
        .metric-card.neutral { border-left: 6px solid #66795d; }

        .metric-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6d7b71;
            margin-bottom: 0.45rem;
        }

        .metric-value {
            font-family: "Bricolage Grotesque", sans-serif;
            font-size: 1.55rem;
            color: #1f2d24;
            line-height: 1.05;
        }

        .metric-detail {
            color: #65746a;
            margin-top: 0.5rem;
            font-size: 0.88rem;
        }

        .insight-panel {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(32, 49, 38, 0.08);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            min-height: 142px;
            box-shadow: 0 10px 24px rgba(32, 49, 38, 0.05);
            margin-bottom: 0.8rem;
        }

        .insight-panel.success { border-top: 5px solid #5e7b42; }
        .insight-panel.warning { border-top: 5px solid #b07a26; }
        .insight-panel.danger { border-top: 5px solid #b34f36; }
        .insight-panel.neutral { border-top: 5px solid #66795d; }

        .insight-title {
            font-size: 0.79rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6b786f;
            margin-bottom: 0.5rem;
        }

        .insight-headline {
            font-family: "Bricolage Grotesque", sans-serif;
            font-size: 1.3rem;
            line-height: 1.05;
            color: #1f2d24;
            margin-bottom: 0.45rem;
        }

        .insight-body {
            color: #56665d;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .alert-card {
            border-radius: 16px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.7rem;
            border: 1px solid transparent;
        }

        .alert-card.warning {
            background: rgba(230, 183, 85, 0.14);
            border-color: rgba(176, 122, 38, 0.18);
        }

        .alert-card.danger {
            background: rgba(204, 113, 84, 0.12);
            border-color: rgba(179, 79, 54, 0.18);
        }

        .alert-card.info {
            background: rgba(96, 125, 98, 0.12);
            border-color: rgba(66, 94, 69, 0.18);
        }

        .alert-card.success {
            background: rgba(94, 123, 66, 0.12);
            border-color: rgba(94, 123, 66, 0.18);
        }

        .alert-title {
            font-weight: 700;
            color: #203126;
            margin-bottom: 0.25rem;
        }

        .alert-body {
            color: #53645b;
            margin: 0;
        }

        div[data-testid="stSidebar"] {
            background: rgba(243, 239, 230, 0.94);
            border-right: 1px solid rgba(32, 49, 38, 0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <section class="hero-card">
            <div class="hero-overline">Demoagro ERP Analytics</div>
            <h1 class="hero-title">{title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="section-title">{title}</div>
        <div class="section-caption">{caption}</div>
        """,
        unsafe_allow_html=True,
    )

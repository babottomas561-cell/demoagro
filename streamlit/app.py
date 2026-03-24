"""
Lemon BI · Dashboard de inteligencia operativa para el negocio limonero.
"""

import streamlit as st
from datetime import datetime
from api.client import fetch_synagro_filters

st.set_page_config(
    page_title="Lemon BI",
    page_icon="🍋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&display=swap');

  :root {
    --bg: #f6f1e8;
    --paper: rgba(255, 252, 245, 0.94);
    --paper-strong: #fffdf8;
    --text: #1b241d;
    --muted: #776b5a;
    --line: #e3d8c8;
    --line-strong: #d7c9b3;
    --green: #2f8b56;
    --green-deep: #1e3a2a;
    --gold: #c7a800;
    --danger: #cf6e63;
    --shadow: 0 10px 30px rgba(28, 33, 24, 0.06);
  }

  /* ── Fondo general ───────────────────────────────── */
  .stApp {
    background:
      radial-gradient(circle at 12% 12%, rgba(201, 168, 0, 0.12), transparent 0 24rem),
      radial-gradient(circle at 90% 8%, rgba(47, 139, 86, 0.10), transparent 0 18rem),
      linear-gradient(180deg, #fbf7f0 0%, var(--bg) 58%, #efe6d7 100%);
    color: var(--text);
    font-family: 'Manrope', system-ui, sans-serif;
  }

  .main .block-container {
    max-width: 1440px;
    padding-top: 1.4rem;
    padding-bottom: 3rem;
  }

  /* ── Sidebar ─────────────────────────────────────── */
  section[data-testid="stSidebar"] {
    background:
      radial-gradient(circle at top, rgba(200, 168, 0, 0.14), transparent 0 14rem),
      linear-gradient(180deg, #173122 0%, #21412d 48%, #1b3526 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
  }
  section[data-testid="stSidebar"] * { color: #d4e8d0 !important; }
  section[data-testid="stSidebar"] hr { border-color: #2d5040 !important; }
  section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-family: 'Manrope', system-ui, sans-serif;
  }
  section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
  }

  /* ── Sidebar nav ────────────────────────────────── */
  .sidebar-brand {
    display: flex;
    align-items: center;
    gap: .85rem;
    padding: .25rem 0 .9rem 0;
  }
  .sidebar-brand-badge {
    width: 46px;
    height: 46px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(199,168,0,0.18) 100%);
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 10px 24px rgba(0,0,0,0.12);
    font-size: 1.35rem;
  }
  .sidebar-brand-copy strong {
    display: block;
    color: #f4f7ee;
    font-size: 1.05rem;
    letter-spacing: -0.02em;
  }
  .sidebar-brand-copy span {
    display: block;
    margin-top: .12rem;
    color: #a7c4ae;
    font-size: .72rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-weight: 800;
  }
  .sidebar-section-label {
    margin: .35rem 0 .55rem 0;
    color: #98baa1 !important;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .14em;
    text-transform: uppercase;
  }
  .sidebar-nav-group {
    margin-bottom: .95rem;
  }
  .sidebar-nav-group-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: .15rem 0 .45rem 0;
  }
  .sidebar-nav-group-title {
    color: #e9f4e4 !important;
    font-size: .8rem;
    font-weight: 800;
    letter-spacing: -.02em;
  }
  .sidebar-nav-group-chip {
    padding: .18rem .48rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.08);
    color: #a8c1ac !important;
    font-size: .62rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
  }
  .sidebar-nav {
    display: grid;
    gap: .55rem;
    margin-bottom: .8rem;
  }
  .sidebar-nav-item {
    position: relative;
    display: grid;
    grid-template-columns: 42px 1fr 18px;
    align-items: center;
    gap: .75rem;
    padding: .82rem .85rem;
    border-radius: 18px;
    text-decoration: none;
    background: linear-gradient(180deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.032) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    transition: transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease;
  }
  .sidebar-nav-item:hover {
    transform: translateY(-1px) translateX(2px);
    border-color: color-mix(in srgb, var(--panel-accent, #c7a800) 42%, rgba(255,255,255,0.12));
    background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.045) 100%);
    box-shadow: 0 14px 28px rgba(0,0,0,0.16);
  }
  .sidebar-nav-item.is-active {
    background: linear-gradient(135deg, color-mix(in srgb, var(--panel-accent, #c7a800) 18%, rgba(255,255,255,0.04)) 0%, rgba(47,139,86,0.14) 100%);
    border-color: color-mix(in srgb, var(--panel-accent, #c7a800) 42%, rgba(255,255,255,0.14));
    box-shadow: 0 16px 30px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.08);
  }
  .sidebar-nav-item.is-active::before {
    content: "";
    position: absolute;
    left: 0;
    top: 10px;
    bottom: 10px;
    width: 4px;
    border-radius: 999px;
    background: linear-gradient(180deg, color-mix(in srgb, var(--panel-accent, #c7a800) 82%, white) 0%, var(--panel-accent, #c7a800) 100%);
  }
  .sidebar-nav-icon {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    background: rgba(255,255,255,0.085);
    border: 1px solid rgba(255,255,255,0.08);
    font-size: 1.08rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    transition: transform .18s ease, background .18s ease, border-color .18s ease, box-shadow .18s ease;
  }
  .sidebar-nav-item:hover .sidebar-nav-icon {
    transform: scale(1.05);
    background: color-mix(in srgb, var(--panel-accent, #c7a800) 16%, rgba(255,255,255,0.08));
    border-color: color-mix(in srgb, var(--panel-accent, #c7a800) 35%, rgba(255,255,255,0.1));
    box-shadow: 0 0 0 6px rgba(255,255,255,0.02);
  }
  .sidebar-nav-item.is-active .sidebar-nav-icon {
    background: color-mix(in srgb, var(--panel-accent, #c7a800) 22%, rgba(255,255,255,0.08));
    border-color: color-mix(in srgb, var(--panel-accent, #c7a800) 34%, rgba(255,255,255,0.14));
    box-shadow: 0 0 0 8px rgba(255,255,255,0.02);
  }
  .sidebar-nav-copy {
    min-width: 0;
  }
  .sidebar-nav-copy strong {
    display: block;
    color: #f5f8f1;
    font-size: .93rem;
    line-height: 1.15;
    letter-spacing: -0.02em;
    margin-bottom: .18rem;
  }
  .sidebar-nav-copy span {
    display: block;
    color: #9fb8a6;
    font-size: .68rem;
    line-height: 1.25;
    letter-spacing: .08em;
    text-transform: uppercase;
    font-weight: 700;
  }
  .sidebar-nav-arrow {
    color: #d7e7d8 !important;
    font-size: 1rem;
    opacity: .72;
    transition: transform .18s ease, opacity .18s ease, color .18s ease;
  }
  .sidebar-nav-item:hover .sidebar-nav-arrow {
    transform: translateX(2px);
    opacity: .96;
  }
  .sidebar-nav-item.is-active .sidebar-nav-arrow {
    opacity: 1;
    color: color-mix(in srgb, var(--panel-accent, #c7a800) 82%, white) !important;
  }

  /* ── Sidebar filters / buttons ──────────────────── */
  .sidebar-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.03) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: .85rem .85rem .5rem .85rem;
    margin: .65rem 0 .85rem 0;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  }
  .sidebar-card-title {
    color: #eef5e9 !important;
    font-size: .9rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-bottom: .15rem;
  }
  .sidebar-card-subtitle {
    color: #9eb6a3 !important;
    font-size: .73rem;
    line-height: 1.4;
    margin-bottom: .55rem;
  }

  /* ── Inputs ──────────────────────────────────────── */
  [data-testid="stSelectbox"] label,
  [data-testid="stTextInput"] label,
  [data-testid="stNumberInput"] label {
    color: var(--muted) !important;
    font-size: 10px !important;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-weight: 800 !important;
  }
  [data-testid="stSelectbox"] > div > div,
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input {
    background: rgba(255, 253, 248, 0.88) !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
  }
  section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    min-height: 44px;
  }
  section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg { fill: #d9e8d8 !important; }
  section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    color: #eef5e9 !important;
  }

  /* ── Métricas ─────────────────────────────────────── */
  [data-testid="stMetric"] {
    position: relative;
    overflow: hidden;
    background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(255,249,240,0.96) 100%);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 16px 18px 14px 18px;
    box-shadow: var(--shadow);
  }
  [data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    inset: 0 auto auto 0;
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, var(--green) 0%, rgba(47, 139, 86, 0.18) 72%, transparent 100%);
  }
  [data-testid="stMetricLabel"] {
    font-size: 10px !important;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted) !important;
  }
  [data-testid="stMetricValue"] {
    font-size: 1.48rem !important;
    font-weight: 800;
    color: var(--text) !important;
    letter-spacing: -0.02em;
  }
  [data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 600; }

  /* ── Títulos ─────────────────────────────────────── */
  h1, h2, h3, h4, h5 {
    color: var(--text) !important;
    letter-spacing: -0.03em !important;
  }
  h1 {
    font-family: 'Fraunces', Georgia, serif !important;
    font-weight: 700 !important;
  }
  h2, h3 {
    font-weight: 800 !important;
  }

  p, li, label, span, div {
    font-family: 'Manrope', system-ui, sans-serif;
  }

  /* ── Dividers ────────────────────────────────────── */
  hr { border-color: var(--line) !important; margin: 1.15rem 0 !important; }

  /* ── Progress bar ────────────────────────────────── */
  .stProgress > div > div { background-color: var(--green) !important; }
  .stProgress > div > div > div {
    background: linear-gradient(90deg, var(--green) 0%, #69b67f 100%) !important;
  }

  /* ── Alerts ──────────────────────────────────────── */
  .stAlert {
    border-radius: 14px !important;
    border: 1px solid var(--line) !important;
    box-shadow: 0 8px 20px rgba(28,33,24,0.05);
  }

  /* ── Plotly charts ───────────────────────────────── */
  [data-testid="stPlotlyChart"] {
    background: var(--paper);
    backdrop-filter: blur(6px);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 8px 10px 2px 10px;
    box-shadow: var(--shadow);
  }
  [data-testid="stPlotlyChart"] .modebar {
    background: rgba(255, 253, 248, 0.92) !important;
    border: 1px solid var(--line) !important;
    border-radius: 999px !important;
    padding: 2px 4px !important;
    top: 10px !important;
    right: 10px !important;
    box-shadow: 0 6px 14px rgba(28, 33, 24, 0.06);
  }
  [data-testid="stPlotlyChart"] .modebar-btn svg {
    fill: #756755 !important;
  }

  /* ── Dataframes ──────────────────────────────────── */
  [data-testid="stDataFrame"] {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: var(--shadow);
  }

  /* ── Buttons / expanders ─────────────────────────── */
  .stButton > button {
    border-radius: 999px !important;
    border: 1px solid var(--line-strong) !important;
    background: linear-gradient(180deg, #fffdf8 0%, #f4ead9 100%) !important;
    color: var(--text) !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 16px rgba(28,33,24,0.05);
  }
  .stButton > button:hover {
    border-color: var(--green) !important;
    color: var(--green) !important;
  }
  section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    min-height: 46px;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background: linear-gradient(180deg, rgba(255,255,255,0.11) 0%, rgba(255,255,255,0.045) 100%) !important;
    color: #eef5e9 !important;
    box-shadow: 0 10px 22px rgba(0,0,0,0.12);
  }
  section[data-testid="stSidebar"] .stButton > button:hover {
    color: #fff7c9 !important;
    border-color: rgba(199,168,0,0.4) !important;
    background: linear-gradient(180deg, rgba(199,168,0,0.15) 0%, rgba(255,255,255,0.05) 100%) !important;
  }
  [data-testid="stExpander"] {
    border-radius: 16px !important;
    border: 1px solid var(--line) !important;
    background: rgba(255, 253, 248, 0.72) !important;
  }
  section[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.08) !important;
  }
  section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    color: #eef5e9 !important;
    font-weight: 700 !important;
  }

  /* ── Hero ────────────────────────────────────────── */
  .hero-shell {
    position: relative;
    overflow: hidden;
    background:
      radial-gradient(circle at 78% 16%, rgba(199, 168, 0, 0.12), transparent 0 16rem),
      linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(247,240,228,0.98) 100%);
    border: 1px solid var(--line);
    border-radius: 24px;
    padding: 1.2rem 1.35rem 1rem 1.35rem;
    box-shadow: 0 18px 40px rgba(28,33,24,0.07);
    margin-bottom: 1rem;
  }
  .hero-kicker {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    padding: .35rem .65rem;
    border-radius: 999px;
    background: rgba(47, 139, 86, 0.10);
    color: var(--green);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
  }
  .hero-title {
    margin: .75rem 0 .25rem 0;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 2.35rem;
    line-height: 1.02;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.04em;
  }
  .hero-subtitle {
    margin: 0 0 .8rem 0;
    max-width: 70rem;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.55;
  }
  .hero-chips {
    display: flex;
    flex-wrap: wrap;
    gap: .45rem;
  }
  .hero-chip {
    padding: .42rem .7rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.75);
    border: 1px solid var(--line);
    color: var(--text);
    font-size: 12px;
    font-weight: 700;
  }
</style>
""", unsafe_allow_html=True)

ERP_PANEL = {
    "label": "ERP Synagro",
    "icon": "🧾",
    "eyebrow": "Sistema",
    "subtitle": "Lectura estratégica, táctica y operativa sobre Synagro simulado: resultado, causas y avance diario sobre lotes, cosechas, labores, contratos, ventas y caja.",
    "render": lambda: __import__("panels.erp_synagro", fromlist=["render"]).render(),
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
          <div class="sidebar-brand-badge">🍋</div>
          <div class="sidebar-brand-copy">
            <strong>Synagro API</strong>
            <span>Consulta simulada</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='margin:0 0 12px 0'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="
            margin:0 0 12px 0;
            padding:12px 14px;
            border-radius:16px;
            background:rgba(255,255,255,0.07);
            border:1px solid rgba(255,255,255,0.10);
            color:#eef5e9;
        ">
          <div style="font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#fff7cf;">Modo único</div>
          <div style="font-size:1rem;font-weight:800;margin-top:4px;">🧾 ERP Synagro</div>
          <div style="font-size:.74rem;line-height:1.45;color:#c7dac8;margin-top:6px;">
            Streamlit consulta solo la API Synagro simulada y ordena la lectura en tres niveles: estratégico, táctico y operativo.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='margin:12px 0'>", unsafe_allow_html=True)

    catalogs = fetch_synagro_filters()
    empresas = catalogs.get("empresas", [])
    campanias = catalogs.get("campanias", [])
    establecimientos = catalogs.get("establecimientos", [])
    clientes = catalogs.get("clientes", [])
    tipos_labor = catalogs.get("tipos_labor", [])
    estados_contrato = catalogs.get("estados_contrato", [])

    active_campaign = next((item for item in campanias if item.get("activa")), campanias[0] if campanias else None)

    st.markdown(
        """
        <div class="sidebar-card">
          <div class="sidebar-card-title">Filtros globales</div>
          <div class="sidebar-card-subtitle">Definí el alcance del panel antes de leer los KPI y los gráficos.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "gf_empresa_id" not in st.session_state and empresas:
        st.session_state.gf_empresa_id = empresas[0]["id"]
    if "gf_campania_id" not in st.session_state and active_campaign:
        st.session_state.gf_campania_id = active_campaign.get("id")

    empresa_options = {item["nombre"]: item["id"] for item in empresas}
    if empresa_options:
        current_empresa_label = next(
            (label for label, value in empresa_options.items() if value == st.session_state.get("gf_empresa_id")),
            next(iter(empresa_options)),
        )
        selected_empresa_label = st.selectbox("Empresa", list(empresa_options.keys()), index=list(empresa_options.keys()).index(current_empresa_label))
        st.session_state.gf_empresa_id = empresa_options[selected_empresa_label]
        st.session_state.gf_empresa_nombre = selected_empresa_label

    campania_options = {item["nombre"]: item["id"] for item in campanias}
    if campania_options:
        current_campaign_label = next(
            (label for label, value in campania_options.items() if value == st.session_state.get("gf_campania_id")),
            next(iter(campania_options)),
        )
        selected_campaign_label = st.selectbox("Campaña", list(campania_options.keys()), index=list(campania_options.keys()).index(current_campaign_label))
        if st.session_state.get("gf_campania_id") != campania_options[selected_campaign_label]:
            st.session_state.gf_campania_id = campania_options[selected_campaign_label]
        st.session_state.gf_campania_nombre = selected_campaign_label

    establecimiento_map = {"Todos": None, **{item["nombre"]: item["id"] for item in establecimientos}}
    current_est_label = next(
        (label for label, value in establecimiento_map.items() if value == st.session_state.get("gf_establecimiento_id")),
        "Todos",
    )
    selected_est_label = st.selectbox("Establecimiento", list(establecimiento_map.keys()), index=list(establecimiento_map.keys()).index(current_est_label))
    st.session_state.gf_establecimiento_id = establecimiento_map[selected_est_label]
    st.session_state.gf_establecimiento_nombre = None if selected_est_label == "Todos" else selected_est_label

    cliente_map = {"Todos": None, **{item["nombre"]: item["id"] for item in clientes}}
    current_client_label = next(
        (label for label, value in cliente_map.items() if value == st.session_state.get("gf_cliente_id")),
        "Todos",
    )
    selected_client_label = st.selectbox("Cliente", list(cliente_map.keys()), index=list(cliente_map.keys()).index(current_client_label))
    st.session_state.gf_cliente_id = cliente_map[selected_client_label]
    st.session_state.gf_cliente_nombre = None if selected_client_label == "Todos" else selected_client_label

    today = datetime.now().date()
    default_from = st.session_state.get("gf_desde") or (today.replace(day=1).isoformat())
    default_to = st.session_state.get("gf_hasta") or today.isoformat()
    st.session_state.gf_desde = st.date_input("Desde", value=datetime.fromisoformat(default_from).date()).isoformat()
    st.session_state.gf_hasta = st.date_input("Hasta", value=datetime.fromisoformat(default_to).date()).isoformat()

    with st.expander("Más filtros ERP"):
        labor_map = {"Todas": None, **{item: item for item in tipos_labor}}
        current_labor_label = next(
            (label for label, value in labor_map.items() if value == st.session_state.get("gf_tipo_labor")),
            "Todas",
        )
        selected_labor_label = st.selectbox("Tipo de labor", list(labor_map.keys()), index=list(labor_map.keys()).index(current_labor_label))
        st.session_state.gf_tipo_labor = labor_map[selected_labor_label]

        contrato_map = {"Todos": None, **{item: item for item in estados_contrato}}
        current_estado_label = next(
            (label for label, value in contrato_map.items() if value == st.session_state.get("gf_estado_contrato")),
            "Todos",
        )
        selected_estado_label = st.selectbox("Estado contrato", list(contrato_map.keys()), index=list(contrato_map.keys()).index(current_estado_label))
        st.session_state.gf_estado_contrato = contrato_map[selected_estado_label]

        categoria_flujo_map = {"Todas": None, "cobranzas": "cobranzas", "riego": "riego", "packhouse": "packhouse", "administracion": "administracion"}
        current_categoria_label = next(
            (label for label, value in categoria_flujo_map.items() if value == st.session_state.get("gf_categoria_flujo")),
            "Todas",
        )
        selected_categoria_label = st.selectbox("Categoría flujo", list(categoria_flujo_map.keys()), index=list(categoria_flujo_map.keys()).index(current_categoria_label))
        st.session_state.gf_categoria_flujo = categoria_flujo_map[selected_categoria_label]

    if st.button("Limpiar filtros", use_container_width=True):
        st.session_state.gf_empresa_id = empresas[0]["id"] if empresas else None
        st.session_state.gf_cliente_id = None
        st.session_state.gf_cliente_nombre = None
        st.session_state.gf_establecimiento_id = None
        st.session_state.gf_establecimiento_nombre = None
        if active_campaign:
            st.session_state.gf_campania_id = active_campaign.get("id")
            st.session_state.gf_campania_nombre = active_campaign.get("nombre")
        st.session_state.gf_desde = None
        st.session_state.gf_hasta = None
        st.session_state.gf_tipo_labor = None
        st.session_state.gf_estado_contrato = None
        st.session_state.gf_categoria_flujo = None
        st.cache_data.clear()
        st.rerun()

    # Live indicator
    now = datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;font-size:11px;color:#8ab89a;padding:4px 0'>"
        f"<span style='width:7px;height:7px;border-radius:50%;background:#4ade80;display:inline-block;"
        f"box-shadow:0 0 6px #4ade80;animation:pulse 2s infinite'></span>"
        f"<span>En vivo · {now}</span>"
        f"</div>"
        f"<style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.35}}}}</style>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    if st.button("🔄  Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        "<div style='margin-top:auto;padding-top:24px;font-size:10px;color:#4a6e50;text-align:center'>"
        "Consulta directa · API Synagro simulada"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Contenido ─────────────────────────────────────────────────────────────────
scope_bits = []
if st.session_state.get("gf_empresa_nombre"):
    scope_bits.append(st.session_state["gf_empresa_nombre"])
if st.session_state.get("gf_campania_nombre"):
    scope_bits.append(st.session_state["gf_campania_nombre"])
if st.session_state.get("gf_establecimiento_id"):
    scope_bits.append(st.session_state.get("gf_establecimiento_nombre"))
if st.session_state.get("gf_cliente_id"):
    scope_bits.append(st.session_state.get("gf_cliente_nombre"))
if st.session_state.get("gf_desde") or st.session_state.get("gf_hasta"):
    scope_bits.append(f"{st.session_state.get('gf_desde') or '...'} → {st.session_state.get('gf_hasta') or '...'}")
chips_html = "".join([f"<span class='hero-chip'>{bit}</span>" for bit in scope_bits])
st.markdown(
    f"""
    <div class="hero-shell">
      <div class="hero-kicker">Consulta API · Estrategia / Táctica / Operación</div>
      <div class="hero-title">{ERP_PANEL['icon']} {ERP_PANEL['label']}</div>
      <div class="hero-subtitle">{ERP_PANEL['subtitle']}</div>
      <div class="hero-chips">{chips_html}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
ERP_PANEL["render"]()

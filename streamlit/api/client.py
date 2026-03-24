"""API client para Streamlit consultando la API Synagro simulada."""

import requests
import streamlit as st

# ── Configuración ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api"

# Cuando la API real requiera auth, descomentá:
# HEADERS = {"Authorization": f"Bearer {st.secrets.get('API_TOKEN', '')}"}
HEADERS: dict = {}

TIMEOUT = 15  # segundos


def _clean_params(params: dict | None) -> dict:
    if not params:
        return {}
    return {key: value for key, value in params.items() if value not in (None, "", "Todos", "Todas")}


def get_global_filter_params() -> dict:
    return _clean_params(
        {
            "empresa_id": st.session_state.get("gf_empresa_id"),
            "campania_id": st.session_state.get("gf_campania_id"),
            "establecimiento_id": st.session_state.get("gf_establecimiento_id"),
            "cliente_id": st.session_state.get("gf_cliente_id"),
            "desde": st.session_state.get("gf_desde"),
            "hasta": st.session_state.get("gf_hasta"),
        }
    )


# ── Fetcher con caché de 15 segundos ─────────────────────────────────────────
@st.cache_data(ttl=15, show_spinner=False)
def _fetch_cached(endpoint: str, params: dict) -> dict:
    """
    Llama a BASE_URL/{endpoint} y devuelve el JSON.
    Si falla, devuelve {} y muestra un warning en la UI.
    """
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.warning(f"⚠️ No se pudo conectar al backend ({url}). Verificá que esté corriendo.")
        return {}
    except requests.exceptions.HTTPError as e:
        st.warning(f"⚠️ Error HTTP {e.response.status_code} en {endpoint}")
        return {}
    except Exception as e:
        st.warning(f"⚠️ Error inesperado: {e}")
        return {}


def fetch(endpoint: str, params: dict | None = None) -> dict:
    merged_params = _clean_params({**get_global_filter_params(), **_clean_params(params)})
    return _fetch_cached(endpoint, merged_params)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_synagro_filters() -> dict:
    return _fetch_cached("synagro/filtros", {})


def fetch_synagro_lotes(params: dict | None = None) -> dict:
    return fetch("synagro/lotes", params)


def fetch_synagro_siembras(params: dict | None = None) -> dict:
    return fetch("synagro/siembras", params)


def fetch_synagro_cosechas(params: dict | None = None) -> dict:
    return fetch("synagro/cosechas", params)


def fetch_synagro_labores(params: dict | None = None) -> dict:
    return fetch("synagro/labores", params)


def fetch_synagro_contratos(params: dict | None = None) -> dict:
    return fetch("synagro/contratos", params)


def fetch_synagro_ventas(params: dict | None = None) -> dict:
    return fetch("synagro/ventas", params)


def fetch_synagro_flujo_caja(params: dict | None = None) -> dict:
    return fetch("synagro/flujo-caja", params)

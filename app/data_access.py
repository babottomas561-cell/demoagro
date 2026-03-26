from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if not (_APP_DIR / "_bootstrap.py").exists():
    _APP_DIR = _APP_DIR.parent

_app_dir_str = str(_APP_DIR)
if _app_dir_str not in sys.path:
    sys.path.insert(0, _app_dir_str)

from _bootstrap import bootstrap_project_path

bootstrap_project_path()

import streamlit as st

from demoagro.services.dashboard_data import get_filter_options, get_snapshot_metadata, load_dashboard_bundle


@st.cache_data(show_spinner=False)
def get_dashboard_bundle() -> dict:
    return load_dashboard_bundle()


def get_dashboard_filter_options() -> dict[str, list[str]]:
    return get_filter_options(get_dashboard_bundle())


def get_dashboard_snapshot_metadata(filters: dict[str, object] | None = None) -> dict[str, object]:
    return get_snapshot_metadata(get_dashboard_bundle(), filters)

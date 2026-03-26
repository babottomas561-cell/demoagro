from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "relative_path",
    [
        "app/Home.py",
        "app/pages/06_Contabilidad_e_Impuestos.py",
        "app/pages/07_RRHH_Mantenimiento_Logistica.py",
        "app/pages/08_Calidad_y_Abastecimiento.py",
    ],
)
def test_streamlit_pages_render_without_exceptions(relative_path: str) -> None:
    app_path = PROJECT_ROOT / relative_path
    app_test = AppTest.from_file(str(app_path))
    app_test.run(timeout=30)
    assert not app_test.exception, f"Se detectaron excepciones en {relative_path}: {app_test.exception}"

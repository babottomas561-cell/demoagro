from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_project_path() -> Path:
    app_dir = Path(__file__).resolve().parent
    project_root = app_dir.parent
    src_dir = project_root / "src"

    for candidate in (project_root, src_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
    return project_root

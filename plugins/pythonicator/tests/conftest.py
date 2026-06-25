"""Make the plugin's modules importable no matter where pytest is invoked.

pytest's ``pythonpath`` option is resolved against the rootdir, so it only
works when the suite runs from the plugin directory; from the repo root the
src/ modules go missing. Insert the paths relative to this file instead, the
way the entry points resolve their own siblings at runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

for _name in ("src", "tests"):
    _path = str(_PLUGIN_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

"""Make the hook module importable no matter where pytest is invoked.

pytest's `pythonpath` option is resolved against the rootdir, so it only
works when the suite runs from the plugin directory. Insert the src path
relative to this file instead, so imports resolve from the repo root too.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

for _name in ("src", "tests"):
    _path = str(_PLUGIN_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

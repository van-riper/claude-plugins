"""SessionStart hook: refresh the generated canon once per session.

Rebuilds the canon from the vault styleguide when it has fallen behind, so the
reviewer agent can trust it as current without a per-dispatch freshness check.
Fails open: a missing vault or any I/O error leaves the committed canon in
place and never blocks the session.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync_canon


def main() -> int:
    """Rebuild the canon when stale, leaving it untouched on any I/O error.

    Returns:
        Always 0; the hook fails open so it never blocks session start.
    """
    try:
        if sync_canon.is_stale():
            sync_canon.build()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

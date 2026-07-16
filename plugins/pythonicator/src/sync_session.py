"""SessionStart hook: keep the global ruff config in step.

It runs once per session and never blocks it. First it notes when the
interpreter is below the supported Python floor or when ruff or ty cannot
run, then keeps the global ruff config linked:

- Wherever an installed copy exists, snapshot its ruff.pythonicator.toml
  into the user config dir and make sure ~/.config/ruff/ruff.toml extends that
  snapshot. The snapshot lives in the user's own dir, so global lint keeps
  working from it even after the plugin is uninstalled.

Canon rebuilds from the vault styleguide are no longer part of this hook;
run `python3 src/sync_canon.py [--check]` directly when the canon needs to
catch up.

Any step failing leaves things as they were and never blocks the session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import toolrunner

INSTALLED_ROOT = Path.home() / ".claude" / "plugins"
MARKETPLACES = INSTALLED_ROOT / "marketplaces"
RUFF_DIR = Path.home() / ".config" / "ruff"
RUFF_USER_CONFIG = RUFF_DIR / "ruff.toml"
SNAPSHOT = RUFF_DIR / "ruff.pythonicator.toml"
EXTEND_MARKER = "# pythonicator: extend the installed canon ruff config"
SNAPSHOT_BANNER = (
    "# GENERATED snapshot of the pythonicator canon ruff config.\n"
    "# Do not edit; edit the plugin's ruff.pythonicator.toml and re-release.\n"
    "# Your ~/.config/ruff/ruff.toml extends this; put overrides there.\n\n"
)


def _python_note() -> str | None:
    """Return a note when the interpreter is below the floor, else None.

    Returns:
        The advisory text, or None when the running Python is supported.
    """
    if not toolrunner.python_below_min():
        return None
    want = ".".join(str(part) for part in toolrunner.MIN_PYTHON)
    have = f"{sys.version_info.major}.{sys.version_info.minor}"
    return (
        f"pythonicator targets Python >= {want}; this session runs {have}. "
        "The hooks still run, but you are below the supported floor."
    )


def _tools_note() -> str | None:
    """Return a note when a required tool cannot run, else None.

    tool_command yields None only when the tool is off PATH and uv is not
    installed to run it through uvx, so a None here is the hard case: the
    user must install the tool itself or install uv as the fallback.

    Returns:
        The advisory text naming the unavailable tools, or None when both
        ruff and ty can run.
    """
    missing = [
        name for name in ("ruff", "ty") if toolrunner.tool_command(name) is None
    ]
    if not missing:
        return None
    names = " and ".join(missing)
    verb = "is" if len(missing) == 1 else "are"
    return (
        f"pythonicator: {names} {verb} unavailable, not on PATH and with "
        "no uv to run it through uvx. The edit hook and audit skip their "
        f"mechanical checks until you install {names}, or install uv as a "
        "fallback."
    )


def _emit_session_notes(notes: list[str]) -> None:
    """Write collected notices as one SessionStart additionalContext block.

    Args:
        notes: Advisory messages to surface, already filtered of None.
    """
    if not notes:
        return
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(notes),
        }
    }
    sys.stdout.write(json.dumps(output))


def _installed_base() -> Path | None:
    """Return the installed ruff.pythonicator.toml, or None if not installed."""
    pattern = "*/plugins/pythonicator/ruff.pythonicator.toml"
    matches = sorted(MARKETPLACES.glob(pattern))
    return matches[0] if matches else None


def _refresh_snapshot(base: Path) -> None:
    """Copy the installed base into the user config dir when it has changed."""
    content = SNAPSHOT_BANNER + base.read_text(encoding="utf-8")
    if SNAPSHOT.exists() and SNAPSHOT.read_text(encoding="utf-8") == content:
        return
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(content, encoding="utf-8")


def _ensure_extend() -> None:
    """Prepend the extend line to the user ruff config, once.

    A ruff.toml that is already a symlink is left untouched: the user has
    chosen to point it at the snapshot themselves, and writing through the
    link would clobber its target.
    """
    if RUFF_USER_CONFIG.is_symlink():
        return
    line = f'{EXTEND_MARKER}\nextend = "{SNAPSHOT.name}"\n\n'
    existing = (
        RUFF_USER_CONFIG.read_text(encoding="utf-8")
        if RUFF_USER_CONFIG.exists()
        else ""
    )
    if EXTEND_MARKER in existing or SNAPSHOT.name in existing:
        return
    RUFF_USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    RUFF_USER_CONFIG.write_text(line + existing, encoding="utf-8")


def _link_ruff_config() -> None:
    """Snapshot the installed base and extend it from the user ruff config."""
    base = _installed_base()
    if base is None:
        return
    try:
        _refresh_snapshot(base)
        _ensure_extend()
    except OSError:
        pass


def main() -> int:
    """Surface session notes, then run the ruff-config upkeep step.

    Returns:
        Always 0; the hook never blocks session start.
    """
    notes = [note for note in (_python_note(), _tools_note()) if note]
    _emit_session_notes(notes)
    _link_ruff_config()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

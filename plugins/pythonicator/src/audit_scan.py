"""Static conformance scanner for the pythonic-audit skill.

Walks a Python tree, runs high-precision AST/regex checks for the canon
rules a linter would catch, and prints one aggregate JSON blob to stdout.
The judgment layer is handled separately by pythonic-reviewer; this tier
covers only the mechanically decidable rules so the audit has whole-repo
metrics even on a repo where ruff and ty never ran.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import operator
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import toolrunner


class TyStatus(TypedDict, total=False):
    """Advisory ty result for a scanned target.

    Attributes:
        ran: Whether ty executed at all.
        clean: Whether ty reported no diagnostics (present when it ran).
        error: Why ty could not run (present when it did not run).
    """

    ran: bool
    clean: bool
    error: str


class FileEntry(TypedDict):
    """Scan result for one Python file.

    Attributes:
        path: File path relative to the scanned root.
        count: Number of findings in the file.
        findings: The findings, each a rule/severity/line mapping.
    """

    path: str
    count: int
    findings: list[dict[str, object]]


class Aggregate(TypedDict):
    """Whole-tree conformance metrics.

    Attributes:
        total_files: Count of Python files scanned.
        files_clean: Count of files with no findings.
        files_clean_pct: Percentage of files with no findings.
        by_rule: Finding counts keyed by rule.
        by_severity: Finding counts keyed by severity.
        worst_offenders: Up to ten file paths with the most findings.
    """

    total_files: int
    files_clean: int
    files_clean_pct: float
    by_rule: dict[str, int]
    by_severity: dict[str, int]
    worst_offenders: list[str]


class ScanResult(TypedDict):
    """The full scan report emitted as JSON.

    Attributes:
        files: Per-file results.
        aggregate: Whole-tree metrics.
        ty: Advisory ty status.
    """

    files: list[FileEntry]
    aggregate: Aggregate
    ty: TyStatus


SKIP_DIRS = frozenset({
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
})
EXEMPT_SHORT_NAMES = frozenset({"i", "j", "k", "e", "f", "_"})
TY_TIMEOUT_SECONDS = 60
# Canon: nesting should stay at depth 3 and must not exceed 4 (a statement
# directly in the function body is depth 1; each nested block adds one).
NEST_LIMIT = 4

# (rule, severity); severity mirrors the canon's keyword mapping.
SEVERITY = {
    "unparseable": "blocker",
    "legacy-typing": "blocker",
    "missing-annotation": "blocker",
    "mutable-default": "blocker",
    "broad-except": "blocker",
    "over-nested": "blocker",
    "sphinx-markup": "blocker",
    "missing-public-docstring": "warning",
    "missing-module-docstring": "warning",
    "cryptic-identifier": "warning",
}

_BLANK_TOKENS = {tokenize.STRING, tokenize.COMMENT}
if hasattr(tokenize, "FSTRING_MIDDLE"):
    _BLANK_TOKENS.add(tokenize.FSTRING_MIDDLE)

# Sphinx/reST markup the canon bans in docstrings: double-backtick inline
# literals, field lists (:param:/:returns:/...), and :role:`x` references.
_SPHINX_MARKUP = re.compile(
    r"``"
    r"|:(?:func|param|type|raises?|yields?|ivar|cvar|vartype|keyword|kwtype)\s"
    r"|:(?:returns?|rtype):"
    r"|:[a-zA-Z]+:`",
)


@dataclass
class Finding:
    """One static finding.

    Attributes:
        rule: The rule key (a key of SEVERITY).
        severity: "blocker" or "warning".
        line: 1-based line number the finding points at.
    """

    rule: str
    severity: str
    line: int


def _make(rule: str, line: int) -> Finding:
    """Build a finding, taking its severity from the SEVERITY table.

    Args:
        rule: The rule key (a key of SEVERITY).
        line: 1-based line number the finding points at.

    Returns:
        A Finding whose severity is the one SEVERITY assigns the rule.
    """
    return Finding(rule, SEVERITY[rule], line)


# --- lifted from grade_all.py, then conformed to the canon (nesting
# --- depth, docstring markup): code_only, public_defs, annotation_gaps,
# --- has_mutable_default, broad_except.


def _blank_span(grid: list[list[str]], tok: tokenize.TokenInfo) -> None:
    """Overwrite one token's characters with spaces, in place.

    Args:
        grid: The source as a per-line list of characters.
        tok: The token whose span to blank, preserving newlines.
    """
    (start_row, start_col), (end_row, end_col) = tok.start, tok.end
    for row in range(start_row, end_row + 1):
        line = grid[row - 1]
        first = start_col if row == start_row else 0
        last = end_col if row == end_row else len(line)
        line[first:last] = [
            char if char == "\n" else " " for char in line[first:last]
        ]


def code_only(src: str) -> str:
    """Blank string and comment characters, preserving code layout.

    Args:
        src: Original Python source text.

    Returns:
        Source where every string/comment/f-string character is replaced
        by a space in place, so code structure (and substrings like
        "with self._lock") survives but docstring prose cannot match.
    """
    grid = [list(line) for line in src.splitlines(keepends=True)]
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return src
    for tok in tokens:
        if tok.type in _BLANK_TOKENS:
            _blank_span(grid, tok)
    return "".join("".join(line) for line in grid)


def public_defs(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Collect public function and method definitions.

    Args:
        tree: Parsed module.

    Returns:
        Definitions whose name is public, plus `__init__`.
    """
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and (not node.name.startswith("_") or node.name == "__init__")
    ]


def annotation_gaps(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """List unannotated args and return on a public function.

    Args:
        func: Function or method definition.

    Returns:
        Names of arguments (and "return") missing an annotation.
    """
    args = func.args
    gaps = [
        arg.arg
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]
        if arg.arg not in {"self", "cls"} and arg.annotation is None
    ]
    if func.returns is None and func.name != "__init__":
        gaps.append("return")
    return gaps


def has_mutable_default(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Report whether a default argument is a mutable literal.

    Args:
        func: Function or method definition.

    Returns:
        True if any default is a list/dict/set literal or constructor.
    """
    for default in [*func.args.defaults, *func.args.kw_defaults]:
        if isinstance(default, ast.List | ast.Dict | ast.Set):
            return True
        builtin_call = (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id in {"list", "dict", "set"}
        )
        if builtin_call:
            return True
    return False


def broad_except(tree: ast.Module) -> bool:
    """Report whether any except clause is bare or catches Exception.

    Args:
        tree: Parsed module.

    Returns:
        True if a handler is bare or names Exception/BaseException.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                return True
            named_broad = isinstance(node.type, ast.Name) and node.type.id in {
                "Exception",
                "BaseException",
            }
            if named_broad:
                return True
    return False


def _cryptic_names(tree: ast.Module) -> list[int]:
    """Return line numbers of cryptic (<=2 char, non-exempt) identifiers.

    Args:
        tree: Parsed module.

    Returns:
        Line numbers of offending function arguments.
    """
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        args = node.args
        all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        lines.extend(
            arg.lineno
            for arg in all_args
            if len(arg.arg) <= 2 and arg.arg not in EXEMPT_SHORT_NAMES
        )
    return lines


def _all_functions(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Collect every function and method definition, public or not.

    Args:
        tree: Parsed module.

    Returns:
        All function and method definitions in the module.
    """
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def _child_blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    """Return the nested statement bodies one level below a statement.

    Elif branches are flattened to the depth of their opening if, so a
    long if/elif chain does not read as deepening nesting.

    Args:
        stmt: A statement that may open nested blocks.

    Returns:
        Each sub-body one indentation level deeper than stmt.
    """
    if isinstance(stmt, ast.If):
        bodies = [stmt.body]
        orelse = stmt.orelse
        while len(orelse) == 1 and isinstance(orelse[0], ast.If):
            bodies.append(orelse[0].body)
            orelse = orelse[0].orelse
        if orelse:
            bodies.append(orelse)
        return bodies
    if isinstance(stmt, ast.For | ast.AsyncFor | ast.While):
        return [stmt.body, stmt.orelse] if stmt.orelse else [stmt.body]
    if isinstance(stmt, ast.With | ast.AsyncWith):
        return [stmt.body]
    if isinstance(stmt, ast.Try | ast.TryStar):
        bodies = [stmt.body, *(handler.body for handler in stmt.handlers)]
        if stmt.orelse:
            bodies.append(stmt.orelse)
        if stmt.finalbody:
            bodies.append(stmt.finalbody)
        return bodies
    if isinstance(stmt, ast.Match):
        return [case.body for case in stmt.cases]
    return []


def _block_depth(body: list[ast.stmt], depth: int) -> int:
    """Return the deepest statement nesting reachable from a body.

    Nested function and class definitions are not descended into; each is
    audited as its own unit.

    Args:
        body: Statements at the current nesting level.
        depth: Nesting level of those statements (a function body is 1).

    Returns:
        The maximum nesting level any statement reaches.
    """
    reached = depth
    for stmt in body:
        if isinstance(
            stmt, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            continue
        for block in _child_blocks(stmt):
            reached = max(reached, _block_depth(block, depth + 1))
    return reached


def _sphinx_docstrings(tree: ast.Module) -> list[int]:
    """Return line numbers of docstrings carrying sphinx/reST markup.

    Args:
        tree: Parsed module.

    Returns:
        The line of each module, class, or function docstring that uses
        markup the canon bans (double-backticks, field lists, roles).
    """
    holders: list[
        ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    ] = [tree]
    holders.extend(
        node
        for node in ast.walk(tree)
        if isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
    )
    lines: list[int] = []
    for holder in holders:
        if not holder.body:
            continue
        first = holder.body[0]
        if not isinstance(first, ast.Expr):
            continue
        literal = first.value
        if not isinstance(literal, ast.Constant):
            continue
        text = literal.value
        if isinstance(text, str) and _SPHINX_MARKUP.search(text):
            lines.append(literal.lineno)
    return lines


def _public_def_findings(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[Finding]:
    """Run the public-definition checks for one function or method.

    Args:
        func: A public function or method definition.

    Returns:
        Findings for a missing docstring, annotation gaps, or a mutable
        default argument.
    """
    findings: list[Finding] = []
    if ast.get_docstring(func) is None:
        findings.append(_make("missing-public-docstring", func.lineno))
    if annotation_gaps(func):
        findings.append(_make("missing-annotation", func.lineno))
    if has_mutable_default(func):
        findings.append(_make("mutable-default", func.lineno))
    return findings


def _over_nested(tree: ast.Module) -> list[int]:
    """Return line numbers of functions nested past the canon limit.

    Args:
        tree: Parsed module.

    Returns:
        The def line of each function whose body nests deeper than four.
    """
    return [
        func.lineno
        for func in _all_functions(tree)
        if _block_depth(func.body, 1) > NEST_LIMIT
    ]


def scan_source(src: str) -> list[Finding]:
    """Run the per-file checks against one module's source.

    Args:
        src: The file's text.

    Returns:
        All findings, or a single "unparseable" blocker on SyntaxError.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError as error:
        return [_make("unparseable", error.lineno or 1)]
    code = code_only(src)
    findings: list[Finding] = []
    legacy = re.search(
        r"\b(Optional|Union)\b|typing\.(List|Dict|Tuple|Set)", code
    )

    if legacy is not None:
        findings.append(_make("legacy-typing", 1))
    if ast.get_docstring(tree) is None:
        findings.append(_make("missing-module-docstring", 1))
    if broad_except(tree):
        findings.append(_make("broad-except", 1))

    for func in public_defs(tree):
        findings.extend(_public_def_findings(func))
    findings.extend(_make("over-nested", line) for line in _over_nested(tree))
    findings.extend(
        _make("sphinx-markup", line) for line in _sphinx_docstrings(tree)
    )
    findings.extend(
        _make("cryptic-identifier", line) for line in _cryptic_names(tree)
    )
    return findings


def iter_python_files(root: Path) -> list[Path]:
    """List .py files under root, skipping vendored and cache directories.

    Args:
        root: Directory to walk (or a single file).

    Returns:
        Sorted list of Python file paths.
    """
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    found = [
        path
        for path in root.rglob("*.py")
        if not any(part in SKIP_DIRS for part in path.parts)
    ]
    return sorted(found)


def run_ty(root: Path) -> TyStatus:
    """Run ty once for an advisory status; never raises.

    Args:
        root: Directory or file to check.

    Returns:
        A dict with "ran" and either "clean" or an "error" note.
    """
    ty = toolrunner.tool_command("ty")
    if ty is None:
        return {"ran": False, "error": "ty not found on PATH or via uvx"}
    try:
        completed = subprocess.run(
            [*ty, "check", str(root)],
            capture_output=True,
            text=True,
            timeout=TY_TIMEOUT_SECONDS,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return {"ran": False, "error": str(error)}
    return {"ran": True, "clean": completed.returncode == 0}


def scan_tree(root: Path) -> ScanResult:
    """Scan every Python file under root and aggregate the findings.

    Args:
        root: Directory or single file to audit.

    Returns:
        The scan result: per-file entries, aggregate metrics, ty status.
    """
    files: list[FileEntry] = []
    counts: list[int] = []
    by_rule: dict[str, int] = {}
    by_severity: dict[str, int] = {"blocker": 0, "warning": 0}

    for path in iter_python_files(root):
        findings = scan_source(path.read_text(encoding="utf-8"))
        relative_path = path.relative_to(root) if root.is_dir() else path.name
        count = len(findings)
        counts.append(count)
        files.append({
            "path": str(relative_path),
            "count": count,
            "findings": [
                {"rule": f.rule, "severity": f.severity, "line": f.line}
                for f in findings
            ],
        })
        for finding in findings:
            by_rule[finding.rule] = by_rule.get(finding.rule, 0) + 1
            by_severity[finding.severity] = (
                by_severity.get(finding.severity, 0) + 1
            )

    clean = counts.count(0)
    ranked = sorted(
        zip(counts, files, strict=True),
        key=operator.itemgetter(0),
        reverse=True,
    )

    aggregate: Aggregate = {
        "total_files": len(files),
        "files_clean": clean,
        "files_clean_pct": round(100 * clean / len(files), 1)
        if files
        else 100.0,
        "by_rule": by_rule,
        "by_severity": by_severity,
        "worst_offenders": [
            entry["path"] for count, entry in ranked if count > 0
        ][:10],
    }

    return {"files": files, "aggregate": aggregate, "ty": run_ty(root)}


def main() -> int:
    """Parse args, scan the target, and print the JSON report.

    Returns:
        Process exit code (0 on success, 2 on a missing target).
    """
    parser = argparse.ArgumentParser(description="Static conformance scan.")
    parser.add_argument("target", type=Path, help="File or directory to audit.")
    args = parser.parse_args()
    if not args.target.exists():
        sys.stderr.write(f"target not found: {args.target}\n")
        return 2
    sys.stdout.write(json.dumps(scan_tree(args.target), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

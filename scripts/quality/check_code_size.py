#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_EXCLUDED_PARTS = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
    }
)
DEFAULT_EXCLUDED_PATH_FRAGMENTS = ("src/interface/rest/generated/",)


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    kind: str
    symbol: str
    line_count: int
    max_lines: int

    def render(self) -> str:
        return (
            f"{self.path}:{self.line}: "
            f"{self.kind} '{self.symbol}' has {self.line_count} lines (max {self.max_lines})"
        )

    def fingerprint(self) -> str:
        return f"{self.path.as_posix()}::{self.kind}::{self.symbol}::{self.max_lines}"


class CodeSizeVisitor(ast.NodeVisitor):
    def __init__(self, path: Path, max_method_lines: int, max_class_lines: int) -> None:
        self.path = path
        self.max_method_lines = max_method_lines
        self.max_class_lines = max_class_lines
        self.violations: list[Violation] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_line_count = _node_line_count(node)
        if class_line_count > self.max_class_lines:
            self.violations.append(
                Violation(
                    path=self.path,
                    line=node.lineno,
                    kind="class",
                    symbol=node.name,
                    line_count=class_line_count,
                    max_lines=self.max_class_lines,
                )
            )

        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        method_line_count = _node_line_count(node)
        if method_line_count > self.max_method_lines:
            symbol = node.name
            kind = "function"
            if self._class_stack:
                symbol = f"{'.'.join(self._class_stack)}.{node.name}"
                kind = "method"

            self.violations.append(
                Violation(
                    path=self.path,
                    line=node.lineno,
                    kind=kind,
                    symbol=symbol,
                    line_count=method_line_count,
                    max_lines=self.max_method_lines,
                )
            )

        self.generic_visit(node)


def _node_line_count(node: ast.AST) -> int:
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    if lineno is None or end_lineno is None:
        return 0
    total_lines = end_lineno - lineno + 1
    docstring_lines = _docstring_line_count(node)
    return max(total_lines - docstring_lines, 0)


def _docstring_line_count(node: ast.AST) -> int:
    if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    if not node.body:
        return 0

    first_statement = node.body[0]
    if not isinstance(first_statement, ast.Expr):
        return 0

    docstring_value = first_statement.value
    if not isinstance(docstring_value, ast.Constant) or not isinstance(docstring_value.value, str):
        return 0

    docstring_start = getattr(first_statement, "lineno", None)
    docstring_end = getattr(first_statement, "end_lineno", None)
    if docstring_start is None or docstring_end is None:
        return 0

    return docstring_end - docstring_start + 1


def _is_excluded(path: Path, excluded_parts: frozenset[str], excluded_fragments: Sequence[str]) -> bool:
    path_text = path.as_posix()
    if any(fragment in path_text for fragment in excluded_fragments):
        return True
    return any(path_part in excluded_parts for path_part in path.parts)


def _iter_python_files(
    targets: Sequence[Path],
    excluded_parts: frozenset[str],
    excluded_fragments: Sequence[str],
) -> list[Path]:
    discovered_files: set[Path] = set()
    missing_targets: list[Path] = []

    for target in targets:
        if not target.exists():
            missing_targets.append(target)
            continue

        if target.is_file():
            if target.suffix == ".py" and not _is_excluded(target, excluded_parts, excluded_fragments):
                discovered_files.add(target)
            continue

        for python_file in target.rglob("*.py"):
            if not _is_excluded(python_file, excluded_parts, excluded_fragments):
                discovered_files.add(python_file)

    if missing_targets:
        missing_text = ", ".join(str(target) for target in missing_targets)
        raise ValueError(f"Target paths do not exist: {missing_text}")

    return sorted(discovered_files)


def _collect_violations(python_files: Iterable[Path], max_method_lines: int, max_class_lines: int) -> list[Violation]:
    violations: list[Violation] = []
    for python_file in python_files:
        source_text = python_file.read_text(encoding="utf-8")
        try:
            syntax_tree = ast.parse(source_text, filename=str(python_file))
        except SyntaxError as syntax_error:
            raise ValueError(f"Failed to parse {python_file}: {syntax_error.msg}") from syntax_error

        visitor = CodeSizeVisitor(
            path=python_file,
            max_method_lines=max_method_lines,
            max_class_lines=max_class_lines,
        )
        visitor.visit(syntax_tree)
        violations.extend(visitor.violations)

    return sorted(violations, key=lambda violation: (str(violation.path), violation.line, violation.symbol))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail if any class or method exceeds configured line thresholds.",
    )
    parser.add_argument(
        "targets",
        nargs="+",
        type=Path,
        help="Files or directories to analyze.",
    )
    parser.add_argument(
        "--max-method-lines",
        type=int,
        default=50,
        help="Maximum number of lines allowed for functions and methods.",
    )
    parser.add_argument(
        "--max-class-lines",
        type=int,
        default=300,
        help="Maximum number of lines allowed for classes.",
    )
    parser.add_argument(
        "--baseline-file",
        type=Path,
        default=None,
        help="Path to a baseline file with known violation fingerprints.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write current violation fingerprints to --baseline-file and exit successfully.",
    )
    return parser


def _load_baseline(baseline_file: Path) -> set[str]:
    if not baseline_file.exists():
        raise ValueError(f"Baseline file does not exist: {baseline_file}")

    baseline_entries: set[str] = set()
    for raw_line in baseline_file.read_text(encoding="utf-8").splitlines():
        normalized_line = raw_line.strip()
        if not normalized_line or normalized_line.startswith("#"):
            continue
        baseline_entries.add(normalized_line)
    return baseline_entries


def _write_baseline(baseline_file: Path, violations: Iterable[Violation]) -> None:
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = sorted({violation.fingerprint() for violation in violations})
    output = "\n".join(fingerprints)
    if output:
        output = f"{output}\n"
    baseline_file.write_text(output, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.max_method_lines <= 0:
        parser.error("--max-method-lines must be greater than zero.")
    if args.max_class_lines <= 0:
        parser.error("--max-class-lines must be greater than zero.")
    if args.write_baseline and args.baseline_file is None:
        parser.error("--write-baseline requires --baseline-file.")

    try:
        python_files = _iter_python_files(args.targets, DEFAULT_EXCLUDED_PARTS, DEFAULT_EXCLUDED_PATH_FRAGMENTS)
        violations = _collect_violations(
            python_files=python_files,
            max_method_lines=args.max_method_lines,
            max_class_lines=args.max_class_lines,
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    if args.write_baseline:
        _write_baseline(args.baseline_file, violations)
        print(f"Wrote {len(violations)} baseline violation fingerprint(s) to {args.baseline_file.as_posix()}.")
        return 0

    baseline_entries: set[str] = set()
    if args.baseline_file is not None:
        try:
            baseline_entries = _load_baseline(args.baseline_file)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2

    effective_violations = [violation for violation in violations if violation.fingerprint() not in baseline_entries]

    if effective_violations:
        for violation in effective_violations:
            print(violation.render())
        print(f"Found {len(effective_violations)} code size violation(s).")
        return 1

    print("No code size violations found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

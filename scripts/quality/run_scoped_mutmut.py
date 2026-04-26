#!/usr/bin/env python3
"""Run mutmut locally with the same changed-file scoping used in CI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
PYPROJECT_BACKUP_PATH = PROJECT_ROOT / ".pyproject.mutmut.bak"
MUTANTS_DIR = PROJECT_ROOT / "mutants"
MUTMUT_CACHE_DIR = PROJECT_ROOT / ".mutmut-cache"
MUTMUT_STATS_PATH = MUTANTS_DIR / "mutmut-cicd-stats.json"


@dataclass(frozen=True)
class MutationStats:
    killed: int
    survived: int
    timeout: int
    suspicious: int

    @property
    def total(self) -> int:
        return self.killed + self.survived + self.timeout + self.suspicious

    @property
    def score(self) -> float:
        if self.total == 0:
            return 100.0
        return ((self.killed + self.timeout) * 100) / self.total


def _run_command(
    command: list[str],
    *,
    capture_output: bool = True,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=capture_output,
        check=check,
    )


def _resolve_base_ref(base_ref: str | None) -> str:
    if base_ref:
        _run_command(["git", "rev-parse", "--verify", base_ref])
        return base_ref

    try:
        resolved = _run_command(
            ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"]
        ).stdout.strip()
        if resolved:
            return resolved
    except subprocess.CalledProcessError:
        pass

    for candidate in ("origin/develop", "origin/main", "origin/master"):
        try:
            _run_command(["git", "rev-parse", "--verify", candidate])
            return candidate
        except subprocess.CalledProcessError:
            continue

    raise RuntimeError("Could not resolve a base ref automatically. Pass one explicitly with --base-ref.")


def _normalize_repo_path(path: str | Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(PROJECT_ROOT)
        except ValueError:
            return candidate.as_posix()
    return candidate.as_posix()


def _find_changed_source_files(base_ref: str) -> list[str]:
    diff = _run_command(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            base_ref,
            "HEAD",
            "--",
            "src/",
        ]
    ).stdout.splitlines()
    return [_normalize_repo_path(path) for path in diff if path.endswith(".py")]


def _clean_mutmut_workspace() -> None:
    for path in (MUTANTS_DIR, MUTMUT_CACHE_DIR):
        if path.exists():
            shutil.rmtree(path)


def _restore_stale_pyproject_backup_if_present() -> None:
    if not PYPROJECT_BACKUP_PATH.exists():
        return

    PYPROJECT_PATH.write_text(PYPROJECT_BACKUP_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    PYPROJECT_BACKUP_PATH.unlink()


def _patch_mutmut_for_src_package_layout() -> None:
    import mutmut  # pylint: disable=import-outside-toplevel

    mutmut_package = Path(mutmut.__file__).resolve().parent
    main_path = mutmut_package / "__main__.py"
    trampoline_path = mutmut_package / "trampoline_templates.py"

    main_text = main_path.read_text(encoding="utf-8")
    old_main = "    assert not name.startswith('src.'), name\n"
    new_main = "    if name.startswith('src.'):\n        name = name[len('src.'):]\n"
    if old_main in main_text:
        main_path.write_text(main_text.replace(old_main, new_main), encoding="utf-8")

    trampoline_text = trampoline_path.read_text(encoding="utf-8")
    old_trampoline = "orig.__module__"
    new_trampoline = "orig.__module__.removeprefix('src.')"
    if old_trampoline in trampoline_text and new_trampoline not in trampoline_text:
        trampoline_path.write_text(
            trampoline_text.replace(old_trampoline, new_trampoline),
            encoding="utf-8",
        )


def _serialize_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        serialized_items = ", ".join(_serialize_toml_value(item) for item in value)
        return f"[{serialized_items}]"
    if isinstance(value, int | float):
        return str(value)
    raise TypeError(f"Unsupported mutmut config value: {value!r}")


@contextmanager
def _scoped_mutmut_config(changed_files: list[str]):
    original_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    try:
        pyproject_data = tomllib.loads(original_text)
        mutmut_config = pyproject_data.get("tool", {}).get("mutmut", {})
        all_source_files = sorted(_normalize_repo_path(path) for path in (PROJECT_ROOT / "src").rglob("*.py"))
        changed_set = {_normalize_repo_path(path) for path in changed_files}
        unchanged_files = [path for path in all_source_files if path not in changed_set]
        preserved_config = {
            key: value for key, value in mutmut_config.items() if key not in {"paths_to_mutate", "do_not_mutate"}
        }
        do_not_mutate = list(mutmut_config.get("do_not_mutate", []))
        do_not_mutate.extend(path for path in unchanged_files if path not in do_not_mutate)

        replacement_lines = ["[tool.mutmut]"]
        replacement_lines.append(
            f"paths_to_mutate = {_serialize_toml_value(mutmut_config.get('paths_to_mutate', ['src/']))}"
        )
        replacement_lines.append(f"do_not_mutate = {_serialize_toml_value(do_not_mutate)}")
        for key, value in preserved_config.items():
            replacement_lines.append(f"{key} = {_serialize_toml_value(value)}")
        replacement = "\n".join(replacement_lines)

        tool_section = "[tool.mutmut]"
        section_start = original_text.find(tool_section)
        if section_start == -1:
            raise RuntimeError("[tool.mutmut] section not found in pyproject.toml")

        next_section = original_text.find("\n[", section_start + len(tool_section))
        if next_section == -1:
            scoped_text = original_text[:section_start].rstrip() + "\n\n" + replacement + "\n"
        else:
            scoped_text = original_text[:section_start].rstrip() + "\n\n" + replacement + original_text[next_section:]

        PYPROJECT_BACKUP_PATH.write_text(original_text, encoding="utf-8")
        PYPROJECT_PATH.write_text(scoped_text, encoding="utf-8")
        print(f"Scoped changed source files: {len(changed_set)}")
        print(f"Ignored unchanged source files: {len(unchanged_files)}")
        yield
    finally:
        PYPROJECT_PATH.write_text(original_text, encoding="utf-8")
        if PYPROJECT_BACKUP_PATH.exists():
            PYPROJECT_BACKUP_PATH.unlink()


def _build_mutmut_command(*args: str) -> list[str]:
    mutmut_executable = shutil.which("mutmut")
    if mutmut_executable:
        return [mutmut_executable, *args]
    return [sys.executable, "-m", "mutmut", *args]


def _run_mutmut(max_children: int) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = "src"

    run_result = _run_command(
        _build_mutmut_command("run", "--max-children", str(max_children)),
        capture_output=False,
        check=False,
        env=env,
    )
    if run_result.returncode != 0:
        raise RuntimeError("mutmut run failed before exporting CI/CD stats")

    _run_command(_build_mutmut_command("export-cicd-stats"), capture_output=False, env=env)


def _read_mutation_stats() -> MutationStats:
    if not MUTMUT_STATS_PATH.exists():
        raise RuntimeError(f"Expected mutmut stats file was not created: {MUTMUT_STATS_PATH}")
    stats_data = json.loads(MUTMUT_STATS_PATH.read_text(encoding="utf-8"))
    return MutationStats(
        killed=stats_data.get("killed", 0),
        survived=stats_data.get("survived", 0),
        timeout=stats_data.get("timeout", 0),
        suspicious=stats_data.get("suspicious", 0),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run mutmut scoped to changed src files, using the same strategy as CI."
    )
    parser.add_argument(
        "--base-ref",
        help="Git ref to diff against. Defaults to origin/HEAD, origin/develop, origin/main, or origin/master.",
    )
    parser.add_argument("--max-children", type=int, default=4, help="Number of worker processes to use.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=80.0,
        help="Minimum mutation score required for a successful exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _restore_stale_pyproject_backup_if_present()
    base_ref = _resolve_base_ref(args.base_ref)
    changed_files = _find_changed_source_files(base_ref)

    if not changed_files:
        print(f"No changed Python files under src/ relative to {base_ref}.")
        return 0

    print(f"Base ref: {base_ref}")
    print("Changed source files:")
    for path in changed_files:
        print(f"  {path}")

    _clean_mutmut_workspace()
    _patch_mutmut_for_src_package_layout()

    with _scoped_mutmut_config(changed_files):
        _run_mutmut(args.max_children)

    stats = _read_mutation_stats()
    print(f"Mutation score: {stats.score:.2f}%")
    print(
        f"Killed: {stats.killed}, Survived: {stats.survived}, Timeout: {stats.timeout}, Suspicious: {stats.suspicious}"
    )

    if stats.score < args.min_score:
        print(f"ERROR: Mutation coverage {stats.score:.2f}% is below {args.min_score:.0f}%")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

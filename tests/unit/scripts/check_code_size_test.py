from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _find_checker_script() -> Path:
    for candidate in Path(__file__).resolve().parents:
        script = candidate / "scripts" / "quality" / "check_code_size.py"
        if script.exists():
            return script
    raise FileNotFoundError("scripts/quality/check_code_size.py not found in any ancestor directory")


CHECKER_SCRIPT = _find_checker_script()


def _run_checker(
    target: Path,
    max_method_lines: int = 50,
    max_class_lines: int = 300,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(CHECKER_SCRIPT),
        "--max-method-lines",
        str(max_method_lines),
        "--max-class-lines",
        str(max_class_lines),
        str(target),
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _run_checker_with_baseline(
    target: Path,
    baseline_file: Path,
    max_method_lines: int = 50,
    max_class_lines: int = 300,
    write_baseline: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(CHECKER_SCRIPT),
        "--max-method-lines",
        str(max_method_lines),
        "--max-class-lines",
        str(max_class_lines),
        "--baseline-file",
        str(baseline_file),
    ]
    if write_baseline:
        command.append("--write-baseline")
    command.append(str(target))
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_given_function_over_threshold_when_checker_runs_then_returns_failure(
    tmp_path: Path,
) -> None:
    given_python_file = tmp_path / "function_size_case.py"
    given_python_file.write_text(
        "\n".join(
            [
                "def too_long_function():",
                "    value = 0",
                "    value += 1",
                "    value += 2",
                "    value += 3",
                "    value += 4",
                "    return value",
                "",
            ]
        ),
        encoding="utf-8",
    )

    when_result = _run_checker(tmp_path, max_method_lines=5, max_class_lines=100)

    assert when_result.returncode == 1
    assert "function 'too_long_function' has 7 lines (max 5)" in when_result.stdout
    assert "Found 1 code size violation(s)." in when_result.stdout


def test_given_class_over_threshold_when_checker_runs_then_returns_failure(
    tmp_path: Path,
) -> None:
    given_python_file = tmp_path / "class_size_case.py"
    given_python_file.write_text(
        "\n".join(
            [
                "class HugeClass:",
                "    def m1(self):",
                "        return 1",
                "",
                "    def m2(self):",
                "        return 2",
                "",
                "    def m3(self):",
                "        return 3",
                "",
                "    def m4(self):",
                "        return 4",
                "",
                "    def m5(self):",
                "        return 5",
                "",
            ]
        ),
        encoding="utf-8",
    )

    when_result = _run_checker(tmp_path, max_method_lines=50, max_class_lines=10)

    assert when_result.returncode == 1
    assert "class 'HugeClass' has 15 lines (max 10)" in when_result.stdout
    assert "Found 1 code size violation(s)." in when_result.stdout


def test_given_code_within_thresholds_when_checker_runs_then_returns_success(
    tmp_path: Path,
) -> None:
    given_python_file = tmp_path / "valid_size_case.py"
    given_python_file.write_text(
        "\n".join(
            [
                "class TeamService:",
                "    def calculate(self):",
                "        value = 0",
                "        value += 1",
                "        return value",
                "",
                "def tiny_function():",
                "    return 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    when_result = _run_checker(tmp_path, max_method_lines=10, max_class_lines=20)

    assert when_result.returncode == 0
    assert "No code size violations found." in when_result.stdout


def test_given_existing_violation_in_baseline_when_checker_runs_then_ignores_it(
    tmp_path: Path,
) -> None:
    given_python_file = tmp_path / "baseline_case.py"
    given_python_file.write_text(
        "\n".join(
            [
                "def baseline_violation():",
                "    value = 0",
                "    value += 1",
                "    value += 2",
                "    value += 3",
                "    value += 4",
                "    return value",
                "",
            ]
        ),
        encoding="utf-8",
    )
    given_baseline_file = tmp_path / "code_size_baseline.txt"
    given_write_result = _run_checker_with_baseline(
        tmp_path,
        baseline_file=given_baseline_file,
        max_method_lines=5,
        max_class_lines=300,
        write_baseline=True,
    )
    assert given_write_result.returncode == 0

    when_result = _run_checker_with_baseline(
        tmp_path,
        baseline_file=given_baseline_file,
        max_method_lines=5,
        max_class_lines=300,
    )

    assert when_result.returncode == 0
    assert "No code size violations found." in when_result.stdout


def test_given_long_docstring_when_checker_runs_then_docstring_is_not_counted(
    tmp_path: Path,
) -> None:
    given_python_file = tmp_path / "docstring_method_size_case.py"
    given_python_file.write_text(
        "\n".join(
            [
                "def function_with_docstring():",
                '    """',
                "    This is a multi-line docstring.",
                "    It should not count against code size limits.",
                '    """',
                "    value = 0",
                "    value += 1",
                "    value += 2",
                "    value += 3",
                "    return value",
                "",
            ]
        ),
        encoding="utf-8",
    )

    when_result = _run_checker(tmp_path, max_method_lines=6, max_class_lines=300)

    assert when_result.returncode == 0
    assert "No code size violations found." in when_result.stdout


def test_given_class_with_docstring_when_checker_runs_then_docstring_is_not_counted(
    tmp_path: Path,
) -> None:
    given_python_file = tmp_path / "docstring_class_size_case.py"
    given_python_file.write_text(
        "\n".join(
            [
                "class CompactClass:",
                '    """',
                "    Class docstring.",
                "    Should be ignored by size checker.",
                '    """',
                "",
                "    def method(self):",
                "        return 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    when_result = _run_checker(tmp_path, max_method_lines=50, max_class_lines=5)

    assert when_result.returncode == 0
    assert "No code size violations found." in when_result.stdout

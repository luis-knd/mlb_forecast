# Quality Gates: pre-commit + GitHub Actions

## Goal

Split local and CI verifications by responsibility:

- `pre-commit`: lightweight checks for fast feedback.
- GitHub Actions: heavier and slower checks, isolated by SRP.

## Local Gate (`.pre-commit-config.yaml`)

Local hooks are focused on quick checks:

- formatting and hygiene: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `pretty-format-json`
- security and safety: `detect-private-key`, `detect-aws-credentials`, `detect-secrets`
- Python formatting/imports: `black`, `isort`
- static quick lint: `ruff` (`E,W,F,ERA,UP,BLE,B,C4,SIM`, with `--fix`)
  - formatter compatibility ignore: `E203`
- static design smell check: local `pylint` hook with `R6301` (`method-may-be-static`) for DB repositories
- OpenAPI consistency: `openapi-spec-validator`

Generated OpenAPI code is out of scope for quality gates:

- excluded path: `src/interface/rest/generated`
- rationale: generated artifacts are not manually maintained

Heavy checks were removed from pre-commit:

- `mypy`
- unit/integration test execution

## PR Workflows (SRP)

Each workflow has one primary concern:

1. `.github/workflows/pr-lint-and-types.yml`
   - `ruff`, `flake8`, `mypy`, OpenAPI validation
2. `.github/workflows/pr-static-quality.yml`
   - dead code (`vulture`)
   - duplicated code (`pylint` duplicate-code)
   - max method/class size (`scripts/quality/check_code_size.py`)
3. `.github/workflows/pr-unit-tests.yml`
   - `pytest -q tests/unit`
4. `.github/workflows/pr-integration-tests.yml`
   - `pytest -q tests/integration`
5. `.github/workflows/pr-performance-smoke.yml`
   - performance anti-patterns (`ruff --select PERF`)
   - profiling report (`pyinstrument`)

## Method and Class Size Guardrails

This repository enforces:

- methods/functions: maximum `50` lines
- classes: maximum `300` lines

The guardrail is implemented in:

- `scripts/quality/check_code_size.py`
- baseline: `scripts/quality/baselines/code_size_baseline.txt`

The baseline avoids blocking legacy debt and only fails the workflow on new violations.

## Local Verification Commands

Run from host:

```bash
pre-commit run --all-files
```

Run inside app container:

```bash
APP_CTN=${APP_CTN:-mlb_forecast_backend-app-1}
docker exec -i "$APP_CTN" pytest -q tests/unit
docker exec -i "$APP_CTN" pytest -q tests/integration
docker exec -i "$APP_CTN" openapi-spec-validator openapi/openapi.yml
docker exec -i "$APP_CTN" python scripts/quality/check_code_size.py --max-method-lines 50 --max-class-lines 300 src
docker exec -i "$APP_CTN" vulture src --min-confidence 80 --exclude "src/interface/rest/generated/"
docker exec -i "$APP_CTN" pylint --disable=all --enable=duplicate-code --min-similarity-lines=8 --ignore-paths='src/interface/rest/generated/.*' src
docker exec -i "$APP_CTN" ruff check src --select PERF
```

## Operational Notes

- Keep `requirements-dev.txt` aligned with hook minimum versions.
- Keep generated code excluded where required (`src/interface/rest/generated`).
- `vulture` and duplication checks run in advisory mode at this stage (`continue-on-error`) while debt is triaged.
- If static-quality false positives appear, tune thresholds with explicit evidence before relaxing defaults.

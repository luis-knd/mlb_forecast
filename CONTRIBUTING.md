# Contributing to MLB Forecast Backend

Thanks for contributing. This repository is public, but it enforces a few project-specific workflow rules that are worth reading before you open a pull request.

## Before you start

- For non-trivial changes, open an issue first to align scope and avoid rework.
- Keep each contribution focused. Avoid bundling contract changes, refactors, documentation changes, and behavior changes unless they are part of the same problem.
- Never include secrets, personal credentials, or private infrastructure details in commits, examples, or docs.

## Development setup

Recommended setup uses Docker:

```bash
git clone https://github.com/luis-knd/mlb_forecast.git mlb_forecast_backend
cd mlb_forecast_backend
cp .env.example .env
docker compose up --build -d
export APP_CTN=${APP_CTN:-mlb_forecast_backend-app-1}
```

Useful local references:

- API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/api/v1/health`

## Branch naming

This repository enforces the following branch naming rule through `pre-commit`:

```text
feature|bugfix|hotfix|release/MLB-<id>-short-description
```

Examples:

- `feature/MLB-54-openapi-tag-structure`
- `bugfix/MLB-77-fix-player-stats-cache`

For public contributions that do not come from the internal board workflow, use `MLB-00` as the external default.

Examples:

- `feature/MLB-00-fix-readme-links`
- `bugfix/MLB-00-correct-openapi-tags`

## API and contract changes

If your change affects public API behavior:

- update `openapi/openapi.yml`
- keep the OpenAPI served by FastAPI aligned with the static contract when descriptions or tag metadata change
- review generated artifacts under `src/interface/rest/generated` only through the supported generation flow
- run the OpenAPI-focused tests under `tests/unit/interface/rest/*openapi*_test.py`

## Testing and validation

Before opening a PR, run at least:

```bash
pre-commit run --all-files
docker exec -i "$APP_CTN" pytest -q tests/unit
docker exec -i "$APP_CTN" pytest -q tests/integration
```

If your change touches business logic or behavior with meaningful branching, also run:

```bash
make test-mutation-scoped ARGS="--base-ref origin/develop --min-score 80"
```

Additional repository rules to remember:

- tests must follow the `*_test.py` naming convention
- generated code under `src/interface/rest/generated` is excluded from some checks and should not be edited casually
- if you change persistence models, keep Alembic migrations and OpenAPI DTOs aligned where applicable

## Pull requests

When you open a PR:

- explain the problem being solved
- describe any contract, persistence, or documentation impact
- keep the PR scoped and easy to review
- include verification commands or evidence when the change is not obvious

## Questions

If anything in the workflow is unclear, open an issue before implementing. That is cheaper than discovering at review time that the change conflicts with the expected contract or branching model.

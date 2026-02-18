# Player Statistics API

## Summary
This document explains how player ingestion and player statistics work in the MLB Forecast backend using an API-first contract.

## API Base
Examples assume local API base:

```bash
API_BASE_URL=${API_BASE_URL:-http://localhost:8000}
```

## Endpoints
- `POST /api/v1/data/ingest/players`
- `GET /api/v1/players`
- `GET /api/v1/players/{player_id}`
- `GET /api/v1/players/{player_id}/stats`

`player_id` in player endpoints is the MLB `personId`.

## Ingestion Modes (`source`)
`POST /api/v1/data/ingest/players` supports these values:

- `team_roster`
  - Ingest players from one MLB team roster.
  - Requires `teamId` (MLB team ID).
  - Optional: `season`, `rosterType`.
- `sport_players`
  - Ingest players from a sport pool.
  - Default MLB uses `sportId=1`.
  - Optional: `season`.
- `search`
  - Ingest players found by text query.
  - Requires `q`.

### Parameter meanings for ingestion
- `season`: target season (YYYY).
- `teamId`: MLB team id (for example Yankees `147`).
- `rosterType`: roster subset (`active` by default).
- `sportId`: sport identifier (`1` for MLB).
- `q`: search text (name or partial text).

## cURL: Ingestion Examples

### Ingest all players for a team roster

```bash
curl -X POST \
  "$API_BASE_URL/api/v1/data/ingest/players?source=team_roster&teamId=147&season=2025&rosterType=active"
```

### Ingest MLB players for a season (sport pool)

```bash
curl -X POST \
  "$API_BASE_URL/api/v1/data/ingest/players?source=sport_players&sportId=1&season=2025"
```

### Ingest players by search text (name)

```bash
curl -X POST \
  "$API_BASE_URL/api/v1/data/ingest/players?source=search&q=Shohei%20Ohtani"
```

### Ingest a single player
There is no dedicated `ingest by personId` endpoint in this iteration.
Use `source=search&q=<name>` and then fetch the specific player by `player_id`.

## Querying Players

### List players (paged)

```bash
curl "$API_BASE_URL/api/v1/players?limit=20&offset=0"
```

### Filter by name

```bash
curl "$API_BASE_URL/api/v1/players?name=ohtani"
```

### Filter by position and active

```bash
curl "$API_BASE_URL/api/v1/players?position=DH&active=true"
```

### Filter by internal team id

```bash
curl "$API_BASE_URL/api/v1/players?team_id=1"
```

Note: `team_id` is the internal DB team id, not MLB `teamId`.

### Get one player by MLB personId

```bash
curl "$API_BASE_URL/api/v1/players/660271"
```

## Querying Player Stats
`GET /api/v1/players/{player_id}/stats` requires:
- `stats`
- `group`

Optional:
- `season`
- `gameType`
- `daysBack`

### cURL: season hitting stats

```bash
curl "$API_BASE_URL/api/v1/players/660271/stats?stats=season&group=hitting&season=2025"
```

### cURL: career pitching postseason stats

```bash
curl "$API_BASE_URL/api/v1/players/434378/stats?stats=career&group=pitching&gameType=P"
```

### cURL: game log hitting stats

```bash
curl "$API_BASE_URL/api/v1/players/660271/stats?stats=gameLog&group=hitting&season=2024"
```

## Allowed Values

### `stats`
- `season`: season totals
- `career`: career totals
- `yearByYear`: season-by-season stats
- `gameLog`: game-by-game stats
- `statSplits`: situational splits
- `seasonAdvanced`: advanced season stats

### `group`
- `hitting`
- `pitching`
- `fielding`
- `catching`
- `running`

### `gameType`
- `R`: Regular season
- `S`: Spring training
- `P`: Playoffs/Postseason
- `W`: World Series
- `A`: All-Star

## Can I search players by name or other data?
Yes.

- By name in app data: `GET /api/v1/players?name=<text>`.
- By position: `GET /api/v1/players?position=<abbr>`.
- By active flag: `GET /api/v1/players?active=true|false`.
- By internal team id: `GET /api/v1/players?team_id=<id>`.
- By external search ingestion: `POST /api/v1/data/ingest/players?source=search&q=<text>`.

In this iteration, there is no direct `GET /players/by-name` endpoint. The list endpoint with filters covers that use case.

## StatsAPI Mapping
The implementation calls these MLB StatsAPI resources:
- `/api/v1/people/{personId}`
- `/api/v1/people/{personId}/stats`
- `/api/v1/sports/{sportId}/players`
- `/api/v1/teams/{teamId}/roster`
- `/api/v1/people/search`

## Cache Strategy
- Player reads:
  - `players:mlb_id:{player_id}`
  - `players:list:...`
- Player stats:
  - `player_stats:player={id}:stats={stats}:group={group}:...`
- Invalidation after ingestion:
  - `players:*`
  - `player_stats:*`

## Reliability and Timeouts
External MLB requests use configurable timeout/retry/backoff:
- `MLB_API_TIMEOUT`
- `MLB_API_MAX_RETRIES`
- `MLB_API_BACKOFF_FACTOR`

## Verification Commands
Use container alias:

```bash
APP_CTN=${APP_CTN:-mlb_forecast_backend-app-1}
```

Validate OpenAPI:

```bash
docker exec "$APP_CTN" openapi-spec-validator openapi/openapi.yml
```

Run focused tests:

```bash
docker exec "$APP_CTN" pytest -q tests/unit/use_cases/player_use_cases_test.py tests/unit/use_cases/player_feature_use_cases_test.py tests/integration/player_routes_test.py
```

Run full unit suite:

```bash
docker exec "$APP_CTN" pytest -q tests/unit
```

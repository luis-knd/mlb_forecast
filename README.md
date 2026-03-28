# MLB Forecast Backend

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1-6BA539?logo=openapiinitiative&logoColor=white)](https://www.openapis.org/)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis 7](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

Backend hexagonal para pronósticos MLB e ingestión de estadísticas. El proyecto expone una API FastAPI, persiste datos
en PostgreSQL, usa Redis como caché e incluye adaptadores relacionados con ML y jobs programados. El contrato OpenAPI
en `openapi/openapi.yml` es la fuente de verdad para los endpoints públicos.

## Indice

- [Que contiene este repositorio](#que-contiene-este-repositorio)
- [Mapa del repositorio](#mapa-del-repositorio)
- [Prerrequisitos](#prerrequisitos)
- [Arranque rapido con Docker](#arranque-rapido-con-docker)
- [Desarrollo local](#desarrollo-local)
- [Uso rapido](#uso-rapido)
- [Configuración](#configuración)
- [Flujos de trabajo habituales](#flujos-de-trabajo-habituales)
- [Contrato OpenAPI y código generado](#contrato-openapi-y-código-generado)
- [Base de datos y migraciones](#base-de-datos-y-migraciones)
- [Resumen de arquitectura](#resumen-de-arquitectura)
- [Notas importantes](#notas-importantes)
- [Tests y quality gates](#tests-y-quality-gates)
- [Contribución](#contribución)
- [Licencia](#licencia)
- [Referencias del proyecto](#referencias-del-proyecto)

## Que contiene este repositorio

- Aplicación FastAPI en `src/interface/rest` con dominios de equipos, juegos, jugadores, predicciones, endpoints de
  sistema e ingestión de datos.
- Núcleo hexagonal en `src/domain` y `src/application`.
- Adaptadores de infraestructura para PostgreSQL, Redis, MLB StatsAPI, carga de modelos ML y jobs programados en
  `src/infrastructure`.
- Flujo API-first basado en `openapi/openapi.yml` y modelos generados en `src/interface/rest/generated`.
- Documentación de apoyo en `docs/`, incluidas referencias de MLB StatsAPI y quality gates.

Si solo necesitas la ruta más corta para levantar el entorno, ve directamente a
[Arranque rapido con Docker](#arranque-rapido-con-docker).

## Mapa del repositorio

```text
.
├── src/
│   ├── domain/                    # Entidades y value objects
│   ├── application/               # Puertos, DTOs y casos de uso
│   ├── infrastructure/            # Adaptadores de DB, caché, MLB API, ML y jobs
│   └── interface/
│       ├── rest/                  # Entry point FastAPI, rutas y manejo de respuestas
│       └── scheduler/             # Entry point del scheduler
├── openapi/openapi.yml            # Contrato público de la API
├── docs/                          # Documentación operativa, notas API y planes técnicos
├── scripts/                       # Setup, migraciones y utilidades de calidad
├── tests/                         # Tests unitarios, de integración y de base de datos
├── models/                        # Artefactos de modelo cargados por el adaptador ML
├── docker-compose.yml             # App, scheduler, postgres y redis
├── Makefile                       # Flujos de trabajo comunes de desarrollo
└── start.py                       # Script guiado de setup y ayuda OpenAPI
```

## Prerrequisitos

- Docker y Docker Compose
- Python `3.11` si quieres ejecutar la app en local fuera de contenedores
- Git

Alias recomendado para flujos basados en contenedores:

```bash
export APP_CTN=${APP_CTN:-mlb_forecast_backend-app-1}
```

## Arranque rapido con Docker

Esta es la ruta recomendada para el desarrollo diario porque replica mejor el runtime del proyecto.

1. Clona el repositorio:
   ```bash
   git clone https://github.com/luis-knd/mlb_forecast.git mlb_forecast_backend
   cd mlb_forecast_backend
   ```

2. Crea tu archivo local de entorno:
   ```bash
   cp .env.example .env
   ```

3. Construye y levanta el stack completo:
   ```bash
   docker compose up --build -d
   export APP_CTN=${APP_CTN:-mlb_forecast_backend-app-1}
   docker compose ps
   ```

4. Verifica la aplicación:
   - [API docs](http://localhost:8000/docs)
   - [ReDoc](http://localhost:8000/redoc)
   - [Healthcheck](http://localhost:8000/api/v1/health)

5. Sigue logs cuando lo necesites:
   ```bash
   docker compose logs -f app
   docker compose logs -f scheduler
   ```

6. Detén el stack:
   ```bash
   docker compose down
   ```

**Notas**:
- El contenedor `app` ejecuta `alembic upgrade head` al arrancar mediante `scripts/entrypoint.sh`.
- `python start.py` sigue disponible si prefieres un helper interactivo para setup, validación y generación OpenAPI.

## Desarrollo local
Usa este flujo si quieres ejecutar FastAPI en el host manteniendo PostgreSQL y Redis en Docker.

```bash
make setup
make env
make run-services
make run
```

Comandos locales útiles:

- `make run-services`: levanta solo `postgres` y `redis`
- `make run`: ejecuta `uvicorn src.interface.rest.main:app --reload`
- `make test`: ejecuta la suite local de pytest
- `make test-coverage`: genera cobertura en `htmlcov/`

## Uso rapido

Una vez levantado el proyecto, estas llamadas son un buen smoke test público del backend:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/
```

Si quieres explorar el contrato y probar endpoints desde navegador:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Configuración

La lista completa de variables de entorno vive en `.env.example`. Estas son las que tocarás con más frecuencia:

| Variable                                                           | Propósito                                                     |
|--------------------------------------------------------------------|---------------------------------------------------------------|
| `DATABASE_URL`                                                     | Cadena de conexión SQLAlchemy usada por la app                |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`                | Valores de bootstrap para PostgreSQL en Docker                |
| `REDIS_URL`                                                        | Cadena de conexión Redis                                      |
| `MLB_API_BASE_URL`, `MLB_API_VERSION`                              | Configuración base de MLB StatsAPI                            |
| `MLB_API_TIMEOUT`, `MLB_API_MAX_RETRIES`, `MLB_API_BACKOFF_FACTOR` | Controles de resiliencia frente a la API externa              |
| `MLB_PLAYER_STATS_ALL_GROUPS_CONCURRENCY`                          | Límite de concurrencia para ingestión fan-out de player stats |
| `CACHE_DEFAULT_TTL`, `CACHE_GAMES_TTL`, `CACHE_STATS_TTL`          | TTLs de la caché Redis                                        |
| `LOG_LEVEL`, `ENVIRONMENT`, `DEBUG`                                | Comportamiento de runtime y nivel de logging                  |

## Flujos de trabajo habituales

| Objetivo                                   | Comando                                                                     |
|--------------------------------------------|-----------------------------------------------------------------------------|
| Levantar todo en Docker                    | `docker compose up --build -d`                                              |
| Ejecutar la app Dockerizada desde Make     | `make run-docker`                                                           |
| Ver el estado de contenedores              | `docker compose ps`                                                         |
| Seguir logs de la app                      | `docker compose logs -f app`                                                |
| Ejecutar la suite local completa           | `make test`                                                                 |
| Ejecutar tests dentro del contenedor `app` | `docker exec -i "$APP_CTN" pytest -q`                                       |
| Ejecutar solo unit tests                   | `docker exec -i "$APP_CTN" pytest -q tests/unit`                            |
| Ejecutar solo integration tests            | `docker exec -i "$APP_CTN" pytest -q tests/integration`                     |
| Ejecutar mutación acotada antes de push    | `make test-mutation-scoped ARGS="--base-ref origin/develop --min-score 80"` |
| Ejecutar hooks locales                     | `pre-commit run --all-files`                                                |

## Contrato OpenAPI y código generado
`openapi/openapi.yml` es el primer archivo que debes revisar cuando añades o cambias comportamiento público de la API.

**Opciones de validación**:
```bash
make openapi-validate
docker exec -i "$APP_CTN" python -c "import start; start.validate_openapi()"
```

**Opciones de generación**:
```bash
make openapi-generate
docker exec -i "$APP_CTN" python -c "import start; start.generate_from_openapi()"
```

**Detalles importantes**:
- Los modelos generados viven en `src/interface/rest/generated/models/`.
- `start.generate_from_openapi()` omite por defecto la generación de routers y actualiza solo modelos generados.
- Si necesitas regenerar routers de forma intencional, define `CODEGEN_SKIP_ROUTERS=0` antes de lanzar la generación.
- Parte del código REST generado queda fuera de algunos quality gates y no debería editarse a mano salvo que el flujo lo
  requiera explícitamente.

## Base de datos y migraciones
El flujo Docker normal aplica migraciones automáticamente al arrancar el contenedor. Usa comandos Alembic manuales solo
cuando estés cambiando persistencia o depurando el estado de migraciones.

```bash
export APP_CTN=${APP_CTN:-mlb_forecast_backend-app-1}

docker exec -i "$APP_CTN" alembic current
docker exec -i "$APP_CTN" alembic history --verbose
docker exec -i "$APP_CTN" alembic revision --autogenerate -m "Describe change"
docker exec -i "$APP_CTN" alembic upgrade head
docker exec -i "$APP_CTN" alembic downgrade -1
```

Si cambias modelos de base de datos, mantén alineadas estas piezas:

- Modelos SQLAlchemy y repositorios en `src/infrastructure/db`
- Migración Alembic en `alembic/versions`
- Schemas OpenAPI si el cambio de persistencia afecta a DTOs públicos

## Resumen de arquitectura

Este repositorio sigue una estructura hexagonal con dirección de dependencias hacia dentro.

- `src/domain`: entidades de negocio y value objects sin dependencias de framework.
- `src/application`: puertos y casos de uso que orquestan el comportamiento del dominio.
- `src/infrastructure`: adaptadores concretos para persistencia, Redis, MLB StatsAPI, ML y jobs del scheduler.
- `src/interface/rest`: rutas FastAPI, adaptadores request/response y manejo centralizado de excepciones.
- `src/interface/scheduler`: entry point de ejecución programada separada de la capa HTTP.

La superficie REST actual gira alrededor de:
- equipos y estadísticas de temporada
- juegos
- jugadores y player stats
- predicciones
- endpoints de ingestión
- endpoints de sistema para health, cache e información de entorno

Para el detalle exacto de la superficie pública, prioriza siempre el contrato y la documentación servida por la
aplicación sobre el resumen del README.

## Notas importantes

- El contrato OpenAPI tiene dos representaciones que deben permanecer alineadas:
  - contrato estático en `openapi/openapi.yml`
  - OpenAPI servido por FastAPI desde `src/interface/rest/main.py`
- La clasificación visual de Swagger depende de los `tags` definidos por operación. No añadas `tags=` en
  `router.include_router(...)` porque terminarás contaminando endpoints de lectura con secciones incorrectas.
- `start.generate_from_openapi()` regenera modelos, no debe usarse como sustituto de revisar manualmente el contrato.
- El contenedor `app` aplica migraciones automáticamente al arrancar. Si una migración nueva rompe el arranque, el
  primer sitio donde mirar es `docker compose logs -f app`.

## Tests y quality gates
Verificación mínima antes de hacer push:

```bash
pre-commit run --all-files
docker exec -i "$APP_CTN" pytest -q tests/unit
docker exec -i "$APP_CTN" pytest -q tests/integration
make test-mutation-scoped ARGS="--base-ref origin/develop --min-score 90"
```

**Referencias adicionales de calidad**:

- `docs/quality-gates.md`: explica qué corre en local y qué corre en CI
- `.pre-commit-config.yaml`: lista autoritativa de hooks
- `pyproject.toml`: configuración de pytest, formato y mutmut

**Convenciones del repositorio que conviene recordar**:

- el código generado bajo `src/interface/rest/generated` queda fuera de algunos checks
- los tests deben seguir la convención `*_test.py` que fuerza pre-commit
- los ejemplos y comandos de este README están alineados con el estado real del repo a fecha `2026-03-28`

## Contribución

Las contribuciones son bienvenidas. La guía completa para preparar ramas, validar cambios y abrir PRs está en
[CONTRIBUTING.md](CONTRIBUTING.md).

Resumen rápido:

- para cambios grandes o ambiguos, abre antes un issue
- la rama debe seguir el patrón `feature|bugfix|hotfix|release/MLB-<id>-descripcion`; para contribuciones públicas externas puedes usar `MLB-00`
- si cambias la API pública, actualiza `openapi/openapi.yml` y valida los tests OpenAPI
- antes de abrir PR, ejecuta `pre-commit`, unit tests e integration tests

## Licencia

Este proyecto está publicado bajo licencia MIT. Consulta [LICENSE](LICENSE) para el texto completo.

## Referencias del proyecto

- Contrato OpenAPI: `openapi/openapi.yml`
- Entry point FastAPI: `src/interface/rest/main.py`
- Setup Docker: `docker-compose.yml`
- Flujos de desarrollo: `Makefile`
- Plantilla de entorno: `.env.example`
- Referencias MLB StatsAPI: `docs/mlbExternalStatsApi/`
- Notas de player stats: `docs/player_stats_api.md`
- Notas de odds and props: `docs/oddsAndProps.md`
- Quality gates: `docs/quality-gates.md`
- Planes y decisiones técnicas: `docs/plans/`

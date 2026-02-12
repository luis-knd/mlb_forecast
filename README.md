# Backend de Pronósticos MLB

Sistema completo de backend para pronósticos de partidos de MLB con arquitectura escalable, machine learning y automatización completa.

## 🏗️ Stack Tecnológico

- **Lenguaje**: Python 3.11+
- **Framework Web**: FastAPI (alto rendimiento, async, documentación automática)
- **Base de Datos**: PostgreSQL (robusta para datos relacionales complejos)
- **Caché**: Redis (rápido, persistente, estructuras de datos flexibles)
- **ORM**: SQLAlchemy + Alembic (migraciones)
- **ML**: scikit-learn + pandas + numpy (modelos estadísticos)
- **Validación**: Pydantic
- **Containerización**: Docker + docker-compose
- **HTTP Client**: httpx para llamadas async a APIs
- **Scheduler**: APScheduler para tareas periódicas
- **Logging**: structlog para logging estructurado

## 📁 Arquitectura del Proyecto

El proyecto utiliza una **Arquitectura Hexagonal** (también conocida como Ports & Adapters) que separa claramente el dominio de la aplicación de los detalles técnicos.

```
mlb_forecast_backend/
├── src/                           # Nueva arquitectura hexagonal
│   ├── domain/                    # Entidades y reglas de negocio
│   │   └── entities/              # Entidades del dominio
│   │       ├── game.py            # Entidad de juego
│   │       ├── player.py          # Entidad de jugador
│   │       ├── prediction.py      # Entidad de predicción
│   │       ├── team.py            # Entidad de equipo
│   │       └── team_stats.py      # Entidad de estadísticas de equipo
│   ├── application/               # Casos de uso y puertos
│   │   ├── ports/                 # Interfaces para adaptadores
│   │   │   ├── cache.py           # Puerto para caché
│   │   │   ├── game_repository.py # Puerto para repositorio de juegos
│   │   │   ├── ml_model.py        # Puerto para modelo ML
│   │   │   ├── mlb_api.py         # Puerto para API MLB
│   │   │   ├── player_repository.py # Puerto para repositorio de jugadores
│   │   │   ├── prediction_repository.py # Puerto para repositorio de predicciones
│   │   │   ├── team_repository.py # Puerto para repositorio de equipos
│   │   │   └── team_stats_repository.py # Puerto para repositorio de estadísticas
│   │   └── use_cases/             # Casos de uso de la aplicación
│   │       ├── game_use_cases.py  # Casos de uso para juegos
│   │       ├── player_use_cases.py # Casos de uso para jugadores
│   │       ├── prediction_use_cases.py # Casos de uso para predicciones
│   │       ├── team_stats_use_cases.py # Casos de uso para estadísticas
│   │       └── team_use_cases.py  # Casos de uso para equipos
│   ├── infrastructure/            # Adaptadores para servicios externos
│   │   ├── cache/                 # Adaptador para Redis
│   │   │   └── redis_adapter.py   # Implementación de caché con Redis
│   │   ├── config/                # Configuración
│   │   │   └── settings.py        # Configuración con Pydantic
│   │   ├── db/                    # Base de datos y repositorios
│   │   │   ├── database.py        # Configuración SQLAlchemy
│   │   │   ├── models.py          # Modelos de datos
│   │   │   └── repositories/      # Implementaciones de repositorios
│   │   ├── ml/                    # Adaptador para modelos ML
│   │   │   └── model_adapter.py   # Implementación de modelo ML
│   │   └── mlb_api/               # Adaptador para API MLB
│   │       └── adapter.py         # Implementación de cliente API MLB
│   └── interface/                 # Interfaces de usuario
│       └── rest/                  # API REST con FastAPI
│           ├── main.py            # Aplicación FastAPI principal
│           └── routes.py          # Rutas de la API
├── app/                           # Código legacy (deprecado)
│   ├── api/                       # Endpoints REST (legacy)
│   ├── core/                      # Configuración central (legacy)
│   ├── db/                        # Base de datos (legacy)
│   ├── services/                  # Servicios de negocio (legacy)
│   ├── ml/                        # Machine Learning (legacy)
│   ├── cache/                     # Sistema de caché (legacy)
│   └── main.py                    # Aplicación FastAPI principal (legacy)
├── alembic/                       # Sistema de migraciones
├── scripts/                       # Scripts de utilidad
├── tests/                         # Tests automatizados
├── docker-compose.yml             # Orquestación de servicios
├── Dockerfile                     # Imagen de la aplicación
├── requirements.txt               # Dependencias Python
├── alembic.ini                    # Configuración de migraciones
└── .env.example                   # Variables de entorno ejemplo
```

### 🏗️ Principios de la Arquitectura Hexagonal

1. **Independencia del Dominio**: El código de dominio (entidades y lógica de negocio) no depende de frameworks o infraestructura.
2. **Puertos e Interfaces**: Definimos interfaces (puertos) para comunicarnos con el exterior.
3. **Adaptadores**: Implementaciones concretas de los puertos para tecnologías específicas.
4. **Dependencias hacia adentro**: Las dependencias siempre apuntan hacia el dominio, nunca al revés.

Esta arquitectura facilita:

- **Testabilidad**: Podemos probar la lógica de negocio sin dependencias externas
- **Mantenibilidad**: Cambiar una tecnología (como la base de datos) no afecta al dominio
- **Evolución**: Podemos añadir nuevas funcionalidades sin modificar el código existente

## 🗄️ Migraciones de Base de Datos

Este proyecto utiliza **Alembic** para gestionar las migraciones de base de datos de manera automática y controlada.

### 🚀 Migraciones Automáticas

Las migraciones se ejecutan **automáticamente** al iniciar el contenedor gracias al script `entrypoint.sh`:

```bash
# Al ejecutar docker-compose up, las migraciones se aplican automáticamente
docker-compose up -d
```

> ✅ **No necesitas ejecutar migraciones manualmente** - se aplican automáticamente al inicio

### 📋 Comandos de Migración Manual

Si necesitas ejecutar migraciones manualmente o crear nuevas:

#### 🔄 Aplicar Migraciones

```bash
# Aplicar todas las migraciones pendientes
docker exec -it mlb_forecast_backend-app-1 alembic upgrade head

# Aplicar migración específica
docker exec -it mlb_forecast_backend-app-1 alembic upgrade +1

# Ver migración actual
docker exec -it mlb_forecast_backend-app-1 alembic current

# Ver historial de migraciones
docker exec -it mlb_forecast_backend-app-1 alembic history --verbose
```

#### ⬇️ Revertir Migraciones

```bash
# Revertir última migración
docker exec -it mlb_forecast_backend-app-1 alembic downgrade -1

# Revertir a migración específica
docker exec -it mlb_forecast_backend-app-1 alembic downgrade <revision_id>

# Revertir todas las migraciones (⚠️ CUIDADO: Elimina todas las tablas)
docker exec -it mlb_forecast_backend-app-1 alembic downgrade base
```

#### ➕ Crear Nueva Migración

```bash
# Crear migración con cambios detectados automáticamente
docker exec -it mlb_forecast_backend-app-1 alembic revision --autogenerate -m "Descripción del cambio"

# Crear migración vacía (para cambios manuales)
docker exec -it mlb_forecast_backend-app-1 alembic revision -m "Descripción del cambio"
```

#### 📊 Estado de la Base de Datos

```bash
# Verificar estado actual
docker exec -it mlb_forecast_backend-app-1 alembic current

# Mostrar diferencias pendientes
docker exec -it mlb_forecast_backend-app-1 alembic show <revision_id>

# Verificar si hay migraciones pendientes
docker exec -it mlb_forecast_backend-app-1 alembic check
```

## 🐳 Comandos Docker Útiles

### 📦 Gestión de Contenedores

```bash
# 🚀 Iniciar todos los servicios
docker-compose up -d

# 🛑 Detener todos los servicios
docker-compose down

# 🔄 Reiniciar servicios
docker-compose restart

# 🔄 Reiniciar servicio específico
docker-compose restart app
docker-compose restart postgres
docker-compose restart redis

# 📊 Ver estado de servicios
docker-compose ps

# 🔍 Ver logs en tiempo real
docker-compose logs -f app

# 📋 Ver logs de servicio específico
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f scheduler
```

### 🔧 Acceso a Contenedores

```bash
# 💻 Acceder al shell del contenedor principal
docker exec -it mlb_forecast_backend-app-1 bash

# 🗄️ Acceder a PostgreSQL
docker exec -it mlb_forecast_backend-postgres-1 psql -U mlb_user -d mlb_forecast

# 🔴 Acceder a Redis CLI
docker exec -it mlb_forecast_backend-redis-1 redis-cli

# 🐍 Ejecutar Python interactivo en el contenedor
docker exec -it mlb_forecast_backend-app-1 python

# 📦 Instalar paquetes adicionales (temporal)
docker exec -it mlb_forecast_backend-app-1 pip install nombre-paquete
```

### 🛠️ Comandos de Desarrollo

```bash
# 🔨 Rebuild completo (cuando cambias Dockerfile)
docker-compose build --no-cache
docker-compose up -d

# 🔄 Rebuild solo la app
docker-compose build app
docker-compose up -d app

# 📁 Sincronizar volúmenes (si hay problemas)
docker-compose down -v
docker-compose up -d

# 🧹 Limpiar contenedores y volúmenes
docker-compose down -v --remove-orphans
docker system prune -a
```

### 📊 Monitoreo y Debug

```bash
# 📈 Ver uso de recursos
docker stats mlb_forecast_backend-app-1

# 🔍 Inspeccionar contenedor
docker inspect mlb_forecast_backend-app-1

# 📋 Ver procesos dentro del contenedor
docker exec -it mlb_forecast_backend-app-1 ps aux

# 💾 Ver espacio en disco
docker exec -it mlb_forecast_backend-app-1 df -h

# 🌐 Verificar conectividad de red
docker exec -it mlb_forecast_backend-app-1 ping postgres
docker exec -it mlb_forecast_backend-app-1 ping redis
```

### 🗄️ Gestión de Base de Datos

```bash
# 📊 Ver tablas existentes
docker exec -it mlb_forecast_backend-postgres-1 psql -U mlb_user -d mlb_forecast -c "\dt"

# 📋 Describir estructura de tabla
docker exec -it mlb_forecast_backend-postgres-1 psql -U mlb_user -d mlb_forecast -c "\d teams"

# 🔍 Ejecutar consulta SQL
docker exec -it mlb_forecast_backend-postgres-1 psql -U mlb_user -d mlb_forecast -c "SELECT COUNT(*) FROM teams;"

# 💾 Crear backup de la base de datos
docker exec -it mlb_forecast_backend-postgres-1 pg_dump -U mlb_user -d mlb_forecast > backup.sql

# 📥 Restaurar backup
docker exec -i mlb_forecast_backend-postgres-1 psql -U mlb_user -d mlb_forecast < backup.sql
```

### 🔴 Gestión de Redis

```bash
# 📊 Ver información de Redis
docker exec -it mlb_forecast_backend-redis-1 redis-cli info

# 🔑 Ver todas las claves
docker exec -it mlb_forecast_backend-redis-1 redis-cli keys "*"

# 🗑️ Limpiar caché completo
docker exec -it mlb_forecast_backend-redis-1 redis-cli flushall

# 📋 Ver estadísticas de caché
docker exec -it mlb_forecast_backend-redis-1 redis-cli info stats

# 💾 Ver memoria utilizada
docker exec -it mlb_forecast_backend-redis-1 redis-cli info memory
```

## 🚨 Solución de Problemas Comunes

### ❌ Error de Migración

```bash
# Si las migraciones fallan, verificar estado
docker exec -it mlb_forecast_backend-app-1 alembic current

# Ver logs detallados
docker-compose logs app | grep alembic

# Forzar migración específica
docker exec -it mlb_forecast_backend-app-1 alembic stamp head
```

### 🔄 Resetear Base de Datos Completa

```bash
# ⚠️ CUIDADO: Esto elimina TODOS los datos
docker-compose down -v
docker-compose up -d postgres redis
sleep 10
docker-compose up -d app
```

### 🐛 Debug de Conexiones

```bash
# Verificar conectividad a PostgreSQL
docker exec -it mlb_forecast_backend-app-1 python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://mlb_user:mlb_password@postgres:5432/mlb_forecast')
    print('✅ PostgreSQL conectado')
    conn.close()
except Exception as e:
    print(f'❌ Error PostgreSQL: {e}')
"

# Verificar conectividad a Redis
docker exec -it mlb_forecast_backend-app-1 python -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, db=0)
    r.ping()
    print('✅ Redis conectado')
except Exception as e:
    print(f'❌ Error Redis: {e}')
"
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- **Python 3.10+** (instalación local opcional)
- **Docker** y **Docker Compose**
- **Git** (para clonar el repositorio)

### 🎯 Inicio Rápido con Instalador y Docker Compose

Se recomienda usar Docker para aislar dependencias y evitar instalar requisitos locales:

### Clonar repositorio e iniciar setup

```bash
git clone https://github.com/luis-knd/mlb_forecast
cd mlb_forecast_backend
```

**Ejecutar script de inicio automático**

```bash
python start.py
```

El script te guiará a través de las opciones disponibles:

<details open>
<summary><strong>Opción 1 → 🐳 Solo Docker (Recomendado)</strong>:</summary>
   Esta opción:

- Instala la python:3.11-slim.
- Instala las librerías necesarias en el contenedor.
- Crea automáticamente dento del contenedor un entorno virtual.
- Instala los requerimientos en el entorno virtual del contenedor.
- Ejecuta la aplicación.

La aplicación estará disponible en [localhost:8000](http://localhost:8000)

</details>

<details open>
<summary><strong>Opción 2 → 🚀 Setup completo con entorno virtual local</strong>:</summary>

Esta opción:

La aplicación estará disponible en [localhost:8000](http://localhost:8000)

</details>

<details open>
<summary><strong>Opción 3 → 🛠️ Setup Manual paso a paso</strong>:</summary>

Esta opción:

</details>

<details open>
<summary><strong>Opción 4 →  ℹ️ Mostrar información del proyecto</strong>:</summary>

Esta opción:
No ejecuta nada, solo muestra la información del proyecto.

</details>

<details open>
<summary><strong>Opción 5 → 🚫 Salir</strong>:</summary>
   Salir del script.
</details>

## 📊 Características Principales

### ⚾ Ingestión Automática de Datos

- **APIs Oficiales MLB**: Integración completa con statsapi.mlb.com
- **Datos en Tiempo Real**: Resultados, estadísticas y calendarios
- **Procesamiento Inteligente**: Validación y limpieza automática
- **Recuperación de Errores**: Sistema robusto ante fallos de API

### 🗄️ Almacenamiento Optimizado

- **Esquema Normalizado**: Base de datos PostgreSQL optimizada
- **Índices Estratégicos**: Consultas rápidas para análisis
- **Datos Históricos**: Almacenamiento eficiente de múltiples temporadas
- **Integridad Referencial**: Relaciones consistentes entre entidades

### ⚡ Sistema de Caché Inteligente

- **Caché Multicapa**: Redis con diferentes TTL por tipo de dato
- **Invalidación Inteligente**: Limpieza automática de datos obsoletos
- **Precalentamiento**: Caché de datos frecuentemente accedidos
- **Estadísticas de Uso**: Monitoreo de hit rates y rendimiento

### 🤖 Machine Learning Avanzado

- **Predicciones Múltiples**: Ganador, runs totales, métricas personalizadas
- **Entrenamiento Continuo**: Actualización automática con nuevos datos
- **Evaluación de Modelos**: Métricas de rendimiento y comparación
- **Características Avanzadas**: Ingeniería de features específicas para MLB

### 🔄 Automatización Completa

- **Scheduler Robusto**: Tareas programadas con APScheduler
- **Ingestión Periódica**: Datos actualizados automáticamente
- **Reentrenamiento ML**: Modelos siempre actualizados
- **Mantenimiento**: Limpieza automática de caché y datos

### 🌐 APIs REST Escalables

- **FastAPI**: Documentación automática y alta performance
- **Validación Automática**: Pydantic para request/response
- **Manejo de Errores**: Respuestas consistentes y logging
- **Rate Limiting**: Protección contra uso excesivo

## 📋 Endpoints Principales

### Equipos y Estadísticas

```http
GET /api/v1/teams                           # Lista de equipos
GET /api/v1/teams/{team_id}                 # Equipo específico
GET /api/v1/teams/{team_id}/stats/{season}  # Estadísticas por temporada
```

### Juegos

```http
GET /api/v1/games                           # Lista de juegos con filtros
GET /api/v1/games/{game_id}                 # Juego específico
```

### Predicciones

```http
POST /api/v1/predictions                    # Generar predicción
GET /api/v1/predictions/{game_id}           # Predicciones existentes
GET /api/v1/predictions/upcoming            # Predicciones próximas
```

### Ingestión de Datos

```http
POST /api/v1/data/ingest/teams              # Ingestar equipos
POST /api/v1/data/ingest/games              # Ingestar juegos
POST /api/v1/data/ingest/full               # Ingestión completa
```

### Sistema y ML

```http
POST /api/v1/ml/retrain                     # Reentrenar modelo
GET /api/v1/cache/stats                     # Estadísticas de caché
DELETE /api/v1/cache/clear                  # Limpiar caché
GET /api/v1/health                          # Estado del sistema
```

## ⚡ Comandos Útiles

### Comandos con Makefile

```bash
# 🏗️ Setup y desarrollo
make setup              # Configuración inicial completa
make dev                # Setup + ejecutar aplicación
make run                # Ejecutar solo la aplicación
make run-docker         # Ejecutar con Docker completo (--no-cache)

# 🧪 Testing y calidad
make test               # Ejecutar pruebas
make test-coverage      # Pruebas con coverage
make lint               # Verificar código con linters
make format             # Formatear código

# 🗄️ Base de datos
make migration-create MSG="descripción"  # Nueva migración
make migration-up       # Aplicar migraciones
make migration-down     # Revertir migración

# 🐳 Docker
make run-services       # Solo PostgreSQL y Redis
make stop               # Detener servicios
make logs               # Ver logs

# 🛠️ Utilidades
make health             # Verificar estado de la app
make clean              # Limpiar archivos temporales
make info               # Información del proyecto
make help               # Ver todos los comandos
```

### Comandos Manuales (Sin Makefile)

```bash
# Activar entorno virtual
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Ejecutar aplicación
uvicorn src.interface.rest.main:app --reload --host 0.0.0.0 --port 8000

# Migraciones
python scripts/migrate.py upgrade
python scripts/migrate.py create "nueva migración"

# Pruebas
python -m pytest tests/ -v

# Pruebas con coverage
python -m pytest tests/ --cov=app

# Ingestión de datos
curl -X POST http://localhost:8000/api/v1/data/ingest/full

# Reentrenamiento ML
curl -X POST http://localhost:8000/api/v1/ml/retrain
```

## 🔧 Configuración Avanzada

### Scheduler de Tareas

```bash
# Ejecutar jobs independiente
python -m src.interface.scheduler.main

# El jobs ha sido migrado a la nueva arquitectura hexagonal.
# Utiliza los mismos componentes que la aplicación principal.

# Tareas programadas:
# - Ingestión diaria de juegos (cada hora)
# - Estadísticas de equipos (diario 6 AM)
# - Reentrenamiento ML (diario 3 AM)
# - Mantenimiento de caché (cada 4 horas)
# - Predicciones próximas (cada 30 min)
```

## 🎯 Ejemplos de Uso

### Generar Predicción

```python
import httpx

# Generar predicción para un juego
response = httpx.post("http://localhost:8000/api/v1/predictions", json={
    "game_id": 123,
    "prediction_types": ["outcome", "total_runs"]
})

prediction = response.json()
print(f"Probabilidad local: {prediction['predictions']['outcome']['home_win_probability']}")
```

### Consultar Juegos del Día

```python
from datetime import datetime

# Obtener juegos de hoy
today = datetime.now().strftime("%Y-%m-%d")
response = httpx.get(f"http://localhost:8000/api/v1/games?date={today}")

games = response.json()
for game in games:
    print(f"Juego: {game['home_team_id']} vs {game['away_team_id']}")
```

### Ingestión Programática

```python
# Ejecutar ingestión completa
response = httpx.post("http://localhost:8000/api/v1/data/ingest/full?season=2024")

result = response.json()
print(f"Ingestión iniciada: {result['message']}")
```

## 🧪 Testing

```bash
# Ejecutar tests básicos
python -m pytest tests/ -v

# Tests específicos
python tests/basic_test.py

# Coverage
pip install pytest-cov
pytest --cov=app tests/
```

### Test en docker

Ejecutar todos los tests

```bash
docker exec -it mlb_forecast_backend-app-1 python -m pytest -v -W always
```

Ejecutar test de un archivo

```bash
docker exec -it mlb_forecast_backend-app-1 python -m pytest tests/integration/team_routes_test.py -v
```

Ejecutar test puntual

`````bash
docker exec -it mlb_forecast_backend-app-1 python -m pytest tests/t````est_basic.py::TestBasicEndpoints::test_health_endpoint -v -W always
`````

## 📈 Monitoreo y Logs

### Logs Estructurados

```bash
# Ver logs en tiempo real
docker-compose logs -f app

# Logs del jobs
docker-compose logs -f jobs

# Logs específicos de ML
grep "ML" docker-compose logs
```

### Métricas de Rendimiento

```bash
# Estado del sistema
curl http://localhost:8000/api/v1/health

# Estadísticas de caché
curl http://localhost:8000/api/v1/cache/stats

# Info de la aplicación
curl http://localhost:8000/info
```

## 🔒 Consideraciones de Producción

### Escalabilidad

- **Horizontal**: Múltiples instancias de la aplicación
- **Base de Datos**: Connection pooling y read replicas
- **Caché**: Cluster Redis para alta disponibilidad
- **Load Balancer**: NGINX o similar para distribución

### Seguridad

- **Variables de Entorno**: Usar secretos seguros en producción
- **Rate Limiting**: Configurar límites apropiados
- **CORS**: Especificar dominios exactos
- **HTTPS**: Terminar SSL en load balancer

### Monitoreo

- **Logging**: Centralizar logs con ELK stack
- **Métricas**: Prometheus + Grafana
- **Alertas**: Configurar notificaciones de errores
- **Health Checks**: Endpoints para monitoreo externo

## 🛠️ Desarrollo y Contribución

### Estructura de Código

- **Principios SOLID**: Cada clase tiene responsabilidad única
- **Patrón Factory**: Para conexiones y servicios
- **Strategy Pattern**: Para diferentes tipos de predicción
- **Open/Closed**: Fácil extensión sin modificación

### Extensiones Futuras

- **Nuevos Deportes**: Arquitectura preparada para otros deportes
- **ML Avanzado**: Redes neuronales y deep learning
- **Real-time**: WebSockets para actualizaciones en vivo
- **APIs Adicionales**: Integración con más fuentes de datos

## 📚 Documentación Adicional

- **API Docs**: http://localhost:8000/docs (Swagger)
- **Arquitectura**: Ver diagramas en [docs/diagrams/](docs/diagrams/)
- **ML Models**: Documentación detallada en `/docs/ml/`

## 🆘 Troubleshooting

### Problemas Comunes

1. **Error de conexión a PostgreSQL**

   ```bash
   # Verificar que el servicio esté ejecutándose
   docker-compose ps postgres

   # Reiniciar servicio
   docker-compose restart postgres
   ```

2. **Redis no conecta**

   ```bash
   # Verificar conexión
   docker-compose exec redis redis-cli ping
   ```

3. **Modelo ML no entrena**

   ```bash
   # Verificar datos suficientes
   curl http://localhost:8000/api/v1/games | jq length

   # Forzar reentrenamiento
   curl -X POST http://localhost:8000/api/v1/ml/retrain
   ```

4. **API MLB no responde**
   ```bash
   # Verificar estado de la API externa
   curl https://statsapi.mlb.com/api/v1/teams
   ```

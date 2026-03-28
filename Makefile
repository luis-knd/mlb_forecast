# Makefile para MLB Forecast Backend
# Simplifica comandos comunes de desarrollo

.PHONY: help setup install run run-docker test test-docker clean lint format migration health openapi-validate openapi-generate logs run-services stop migration-create migration-up migration-down test-coverage docs env dev quick-start docker-build docker-push info retrain-model ingest-data

# Variables
PYTHON := python
VENV_PATH := venv
VENV_PYTHON := $(VENV_PATH)/bin/python
VENV_PIP := $(VENV_PATH)/bin/pip
ifeq ($(OS),Windows_NT)
    VENV_PYTHON := $(VENV_PATH)/Scripts/python.exe
    VENV_PIP := $(VENV_PATH)/Scripts/pip.exe
endif

# Colores para output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Docker compose command (supports both Docker Compose v1 and v2)
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

help: ## Muestra esta ayuda
	@echo "$(BLUE)MLB Forecast Backend - Comandos Disponibles$(NC)"
	@echo "=============================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Configuración inicial completa del proyecto
	@echo "$(YELLOW)🏗️ Configuración inicial del proyecto...$(NC)"
	$(PYTHON) scripts/setup_venv.py
	@echo "$(GREEN)✅ Configuración completada$(NC)"

install: ## Instala todas las dependencias (producción + desarrollo) en entorno virtual existente
	@echo "$(YELLOW)📦 Instalando dependencias...$(NC)"
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✅ Todas las dependencias instaladas$(NC)"

install-dev: install ## Alias para instalar todas las dependencias

env: ## Crea archivo .env desde ejemplo
	@echo "$(YELLOW)📝 Creando archivo .env...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✅ Archivo .env creado desde ejemplo$(NC)"; \
	else \
		echo "$(YELLOW)ℹ️ Archivo .env ya existe$(NC)"; \
	fi

run: env ## Ejecuta la aplicación en modo desarrollo
	@echo "$(YELLOW)🚀 Iniciando aplicación en modo desarrollo...$(NC)"
	$(VENV_PYTHON) -m uvicorn src.interface.rest.main:app --reload --host 0.0.0.0 --port 8000

run-docker: env ## Ejecuta la aplicación con Docker Compose
	@echo "$(YELLOW)🐳 Iniciando aplicación con Docker...$(NC)"
	$(COMPOSE) up --build

run-services: ## Ejecuta solo PostgreSQL y Redis
	@echo "$(YELLOW)🗄️ Iniciando servicios de base de datos...$(NC)"
	$(COMPOSE) up -d postgres redis

stop: ## Detiene todos los servicios Docker
	@echo "$(YELLOW)⏹️ Deteniendo servicios...$(NC)"
	$(COMPOSE) down

migration-create: ## Crea nueva migración (usar: make migration-create MSG="descripción")
	@echo "$(YELLOW)📊 Creando nueva migración...$(NC)"
	$(VENV_PYTHON) scripts/migrate.py create "$(MSG)"

migration-up: ## Aplica migraciones pendientes
	@echo "$(YELLOW)⬆️ Aplicando migraciones...$(NC)"
	$(VENV_PYTHON) scripts/migrate.py upgrade

migration-down: ## Revierte última migración
	@echo "$(YELLOW)⬇️ Revirtiendo migración...$(NC)"
	$(VENV_PYTHON) scripts/migrate.py downgrade -1

test: ## Ejecuta pruebas
	@echo "$(YELLOW)🧪 Ejecutando pruebas...$(NC)"
	$(VENV_PYTHON) -m pytest tests/ -v

test-docker: ## Ejecuta pruebas dentro del contenedor app (sin depender de servicios)
	@echo "$(YELLOW)🐳 Ejecutando pruebas en contenedor app...$(NC)"
	$(COMPOSE) run --rm --no-deps app python -m pytest -v -W always

test-mutation: ## Ejecuta pruebas de mutación (mutmut) en el contenedor (uso ocasional)
	@echo "$(YELLOW)🧬 Ejecutando pruebas de mutación en contenedor app...$(NC)"
	$(COMPOSE) exec app mutmut run $(ARGS)

test-mutation-scoped: ## Ejecuta mutmut acotado a archivos src cambiados vs la rama base
	@echo "$(YELLOW)🧬 Ejecutando pruebas de mutación acotadas en contenedor app...$(NC)"
	$(COMPOSE) exec app python scripts/quality/run_scoped_mutmut.py $(ARGS)

test-coverage: ## Ejecuta pruebas con coverage
	@echo "$(YELLOW)📊 Ejecutando pruebas con coverage...$(NC)"
	$(VENV_PIP) install pytest-cov
	$(VENV_PYTHON) -m pytest tests/ --cov=src --cov-report=html --cov-report=term

lint: ## Ejecuta linters (flake8)
	@echo "$(YELLOW)🔍 Ejecutando linters...$(NC)"
	$(VENV_PIP) install flake8
	$(VENV_PYTHON) -m flake8 src/

format: ## Formatea código con black
	@echo "$(YELLOW)🎨 Formateando código...$(NC)"
	$(VENV_PIP) install black isort
	$(VENV_PYTHON) -m black src/ scripts/ tests/
	$(VENV_PYTHON) -m isort src/ scripts/ tests/

clean: ## Limpia archivos temporales y caché
	@echo "$(YELLOW)🧹 Limpiando archivos temporales...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	@echo "$(GREEN)✅ Limpieza completada$(NC)"

clean-all: clean ## Limpia todo incluyendo entorno virtual
	@echo "$(YELLOW)🗑️ Limpieza completa (incluyendo venv)...$(NC)"
	rm -rf $(VENV_PATH) 2>/dev/null || true
	@echo "$(GREEN)✅ Limpieza completa terminada$(NC)"

health: ## Verifica estado de la aplicación
	@echo "$(YELLOW)❤️ Verificando estado de la aplicación...$(NC)"
	@curl -s http://localhost:8000/api/v1/health | jq . || echo "$(RED)❌ Aplicación no disponible$(NC)"

logs: ## Muestra logs de Docker Compose
	$(COMPOSE) logs -f

shell: ## Abre shell en el entorno virtual
	@echo "$(YELLOW)🐚 Abriendo shell en entorno virtual...$(NC)"
	@echo "$(BLUE)Usa 'exit' para salir$(NC)"
	@$(VENV_PYTHON) -c "import sys; print(f'Python {sys.version}')"
	@bash --init-file <(echo "source $(VENV_PATH)/bin/activate; echo '$(GREEN)✅ Entorno virtual activado$(NC)'")

docs: ## Abre documentación de la API
	@echo "$(YELLOW)📚 Abriendo documentación...$(NC)"
	@python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')"

ingest-data: ## Ejecuta ingestión completa de datos
	@echo "$(YELLOW)📊 Ejecutando ingestión de datos...$(NC)"
	curl -X POST http://localhost:8000/api/v1/data/ingest/full

retrain-model: ## Ejecuta reentrenamiento del modelo ML
	@echo "$(YELLOW)🤖 Ejecutando reentrenamiento de modelo...$(NC)"
	curl -X POST http://localhost:8000/api/v1/ml/retrain

# OpenAPI helpers
openapi-validate: ## Valida el archivo OpenAPI (usa start.py)
	@echo "$(YELLOW)🧪 Validando OpenAPI...$(NC)"
	$(VENV_PYTHON) -c "import start; start.validate_openapi()"

openapi-generate: ## Genera modelos y stubs desde OpenAPI (usa start.py)
	@echo "$(YELLOW)🧬 Generando modelos/stubs desde OpenAPI...$(NC)"
	$(VENV_PYTHON) -c "import start; start.generate_from_openapi()"

# Comandos de desarrollo rápido
dev: setup run ## Setup completo + ejecutar aplicación

quick-start: env run-services ## Inicia servicios y aplicación rápidamente
	@sleep 5
	@$(MAKE) run

# Comandos de Docker
docker-build: ## Construye imagen Docker
	docker build -t mlb-forecast-backend .

docker-push: ## Empuja imagen a registry (configurar REGISTRY)
	docker tag mlb-forecast-backend $(REGISTRY)/mlb-forecast-backend:latest
	docker push $(REGISTRY)/mlb-forecast-backend:latest

# Información del proyecto
info: ## Muestra información del proyecto
	@echo "$(BLUE)MLB Forecast Backend$(NC)"
	@echo "===================="
	@echo "🐍 Python: $(shell $(VENV_PYTHON) --version 2>/dev/null || echo 'No disponible')"
	@echo "📦 Pip: $(shell $(VENV_PIP) --version 2>/dev/null || echo 'No disponible')"
	@echo "🐳 Docker: $(shell docker --version 2>/dev/null || echo 'No disponible')"
	@echo "📁 Directorio: $(PWD)"
	@echo "🔗 Entorno virtual: $(VENV_PATH)"
	@echo ""
	@echo "📋 Archivos importantes:"
	@echo "  - .env: $(shell [ -f .env ] && echo 'Existe' || echo 'No existe')"
	@echo "  - venv/: $(shell [ -d $(VENV_PATH) ] && echo 'Existe' || echo 'No existe')"
	@echo "  - requirements.txt: $(shell [ -f requirements.txt ] && echo 'Existe' || echo 'No existe')"

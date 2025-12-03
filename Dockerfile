# --- Stage 1: Builder with system dependencies ---
FROM python:3.11-slim AS builder

# Instalar dependencias de compilación y PostgreSQL client
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        libblas-dev \
        liblapack-dev \
        libopenblas-dev \
        postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Directorio de trabajo y crear virtualenv
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias Python (con herramienta de debug)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# --- Stage 2: Production image ---
FROM python:3.11-slim AS production

# Solo PostgreSQL client en producción
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar virtualenv desde el builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código de la aplicación
COPY . .

# Copiar y hacer ejecutable el script de entrada
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PATH="/opt/venv/bin:$PATH"

# Crear usuario no-root y ajustar permisos
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app /opt/venv
RUN chown app:app /entrypoint.sh
USER app

# Exponer puerto
EXPOSE 8000

# Usar el script de entrada para ejecutar migraciones automáticamente
ENTRYPOINT ["/entrypoint.sh"]

# Comando por defecto
CMD ["uvicorn", "src.interface.rest.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

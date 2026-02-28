#!/usr/bin/env python3
"""
Script de configuración para entorno de desarrollo.
Automatiza la inicialización del proyecto.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command, description=""):
    """Ejecuta un comando y maneja errores."""
    if description:
        print(f"\n🔄 {description}")

    print(f"Ejecutando: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Completado exitosamente")
        if result.stdout and "--verbose" in sys.argv:
            print(result.stdout)
    else:
        print("❌ Error ejecutando comando")
        if result.stderr:
            print(result.stderr)
        return False

    return True


def check_prerequisites():
    """Verifica que las herramientas necesarias estén instaladas."""
    print("🔍 Verificando prerequisitos...")

    prerequisites = [
        ("python3", "Python 3.11+"),
        ("pip", "pip package manager"),
        ("docker", "Docker"),
        ("docker-compose", "Docker Compose"),
    ]

    missing = []

    for command, description in prerequisites:
        result = subprocess.run(f"which {command}", shell=True, capture_output=True)
        if result.returncode != 0:
            missing.append(description)
        else:
            print(f"✅ {description} encontrado")

    if missing:
        print("\n❌ Faltan las siguientes herramientas:")
        for tool in missing:
            print(f"  - {tool}")
        print("\nInstala las herramientas faltantes e inténtalo de nuevo.")
        return False

    print("✅ Todos los prerequisitos están disponibles")
    return True


def create_env_file():
    """Crea archivo .env desde el ejemplo."""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("ℹ️ Archivo .env ya existe, saltando...")
        return True

    if not env_example.exists():
        print("❌ Archivo .env.example no encontrado")
        return False

    print("📝 Creando archivo .env desde ejemplo...")

    try:
        with open(env_example) as src, open(env_file, "w") as dst:
            dst.write(src.read())
        print("✅ Archivo .env creado")
        return True
    except Exception as e:
        print(f"❌ Error creando .env: {e}")
        return False


def setup_python_environment():
    """Configura el entorno Python con entorno virtual."""
    print("\n🐍 Configurando entorno Python...")

    # Verificar si existe entorno virtual
    venv_exists = Path("venv").exists()

    if not venv_exists:
        print("📦 Configurando entorno virtual...")
        if not run_command("python scripts/setup_venv.py", "Ejecutando setup de entorno virtual"):
            return False
    else:
        print("ℹ️ Entorno virtual ya existe")

    # Crear directorios adicionales
    directories = ["ml_models", "logs", "data", "exports"]
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir()
            print(f"📁 Directorio {directory} creado")

    return True


def setup_database():
    """Configura la base de datos."""
    print("\n🗄️ Configurando base de datos...")

    # Crear migraciones iniciales
    if not run_command(
        "python scripts/migrate.py create 'Initial migration'",
        "Creando migración inicial",
    ):
        print("ℹ️ Migración inicial ya existe o falló, continuando...")

    return True


def start_services():
    """Inicia los servicios con Docker."""
    print("\n🚀 Iniciando servicios con Docker...")

    if not run_command("docker-compose up -d postgres redis", "Iniciando PostgreSQL y Redis"):
        return False

    # Esperar a que los servicios estén listos
    print("⏳ Esperando a que los servicios estén listos...")
    import time

    time.sleep(10)

    return True


def run_migrations():
    """Ejecuta las migraciones de base de datos."""
    print("\n📊 Ejecutando migraciones...")

    return run_command("python scripts/migrate.py upgrade", "Aplicando migraciones")


def test_setup():
    """Prueba que la configuración esté funcionando."""
    print("\n🧪 Probando configuración...")

    # Test básico de importación
    test_script = """
import sys
sys.path.append('.')
try:
    from src.infrastructure.config.settings import settings
    from src.infrastructure.db.database import engine
    print("✅ Configuración básica OK")
except Exception as e:
    print(f"❌ Error en configuración: {e}")
    sys.exit(1)
"""

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)

    if result.returncode == 0:
        print(result.stdout)
        return True
    else:
        print(result.stderr)
        return False


def show_next_steps():
    """Muestra los próximos pasos."""
    print(
        """
🎉 ¡Configuración completada exitosamente!

Próximos pasos:

1. Iniciar la aplicación completa:
   docker-compose up --build

2. Acceder a la documentación de la API:
   http://localhost:8000/docs

3. Ejecutar ingestión inicial de datos:
   curl -X POST http://localhost:8000/api/v1/data/ingest/full

4. Verificar el estado del sistema:
   curl http://localhost:8000/api/v1/health

5. Para desarrollo, también puedes ejecutar solo la API:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

6. Para ejecutar el jobs por separado:
   python -m app.services.jobs

Archivos importantes:
  - .env                    # Variables de entorno
  - docker-compose.yml      # Orquestación de servicios
  - app/main.py            # Aplicación principal
  - app/api/routes.py      # Endpoints de la API

Comandos útiles:
  - docker-compose logs    # Ver logs de servicios
  - docker-compose down    # Detener servicios
  - python scripts/migrate.py history  # Ver migraciones

¡Feliz desarrollo! 🚀
"""
    )


def main():
    """Función principal."""
    print("🏗️ Configuración de entorno de desarrollo MLB Forecast Backend")
    print("=" * 60)

    steps = [
        ("Verificar prerequisitos", check_prerequisites),
        ("Crear archivo .env", create_env_file),
        ("Configurar entorno Python", setup_python_environment),
        ("Configurar base de datos", setup_database),
        ("Iniciar servicios", start_services),
        ("Ejecutar migraciones", run_migrations),
        ("Probar configuración", test_setup),
    ]

    for step_name, step_func in steps:
        print(f"\n{'=' * 20} {step_name} {'=' * 20}")

        if not step_func():
            print(f"\n❌ Error en paso: {step_name}")
            print("Configuración interrumpida. Revisa los errores anteriores.")
            return False

    print("\n" + "=" * 60)
    show_next_steps()
    return True


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)

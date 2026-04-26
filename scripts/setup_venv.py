#!/usr/bin/env python3
"""
Script para configurar entorno virtual y dependencias.
Automatiza la creación del venv y instalación de dependencias.
"""

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve


def run_command(command, description="", cwd=None):
    """Ejecuta un comando y maneja errores."""
    if description:
        print(f"\n🔄 {description}")

    print(f"Ejecutando: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)

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


def check_python_version():
    """Verifica que la versión de Python sea compatible."""
    print("🐍 Verificando versión de Python...")

    version = sys.version_info
    if version.major != 3 or version.minor < 9:
        print(f"❌ Se requiere Python 3.9+ (actual: {version.major}.{version.minor})")
        return False

    print(f"✅ Python {version.major}.{version.minor}.{version.micro} es compatible")
    return True


def create_virtual_environment():
    """Crea el entorno virtual y asegura que pip esté instalado, incluso si ensurepip no está disponible."""
    venv_path = Path("venv")

    if venv_path.exists():
        print("ℹ️ El entorno virtual ya existe")
    else:
        print("📦 Creando entorno virtual sin pip (por compatibilidad)...")
        try:
            venv.create("venv", with_pip=False)
            print("✅ Entorno virtual creado en ./venv")
        except (OSError, RuntimeError, ValueError) as e:
            print(f"❌ Error creando entorno virtual: {e}")
            return False

    pip_path = get_venv_pip()
    python_exec = get_venv_python()

    if not Path(pip_path).exists():
        print("⚠️ Pip no está disponible en el entorno virtual. Descargando get-pip.py...")

        try:
            url = "https://bootstrap.pypa.io/get-pip.py"
            get_pip_script = "get-pip.py"
            urlretrieve(url, get_pip_script)
            print("📥 get-pip.py descargado con éxito")

            print("⚙️ Instalando pip en entorno virtual...")
            result = subprocess.run([python_exec, get_pip_script], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Falló la instalación manual de pip: {result.stderr}")
                return False

            print("✅ pip instalado correctamente en el entorno virtual")
            os.remove(get_pip_script)

        except (OSError, URLError, subprocess.SubprocessError) as e:
            print(f"❌ Error descargando o ejecutando get-pip.py: {e}")
            return False

    return True


def get_venv_python():
    """Obtiene la ruta del ejecutable Python del entorno virtual."""
    if os.name == "nt":  # Windows
        return "venv\\Scripts\\python.exe"
    else:  # Unix/Linux/macOS
        return "venv/bin/python"


def get_venv_pip():
    """Obtiene la ruta del ejecutable pip del entorno virtual."""
    if os.name == "nt":  # Windows
        return "venv\\Scripts\\pip.exe"
    else:  # Unix/Linux/macOS
        return "venv/bin/pip"


def ensure_pg_config():
    """Verifica que pg_config exista en el PATH."""
    if shutil.which("pg_config") is None:
        print("❌ No se encontró pg_config en el sistema.")
        print("   • En Debian/Ubuntu: sudo apt install libpq-dev build-essential")
        print("   • En RHEL/CentOS : sudo yum install postgresql-devel gcc make")
        return False
    return True


def ensure_build_deps():
    """Verifica que el compilador y librerías de BLAS/LAPACK estén presentes."""
    missing = []
    for exe in ("gcc", "gfortran", "pkg-config"):
        if shutil.which(exe) is None:
            missing.append(exe)
    if missing:
        print("❌ Faltan herramientas de compilación:", ", ".join(missing))
        print("   • En Debian/Ubuntu: sudo apt install build-essential gfortran")
        print("   • Y librerías BLAS/LAPACK: sudo apt install libblas-dev liblapack-dev libopenblas-dev")
        return False
    return True


def install_dependencies():
    """Instala las dependencias en el entorno virtual."""
    if not ensure_pg_config():
        sys.exit(1)

    if not ensure_build_deps():
        sys.exit(1)

    print("📋 Instalando dependencias...")
    pip_cmd = get_venv_pip()

    # Actualizar pip primero
    if not run_command(f"{pip_cmd} install --upgrade pip", "Actualizando pip"):
        return False

    # Instalar dependencias
    return run_command(
        f"{pip_cmd} install -r requirements.txt -c constraints.txt",
        "Instalando dependencias del proyecto con restricciones",
    )


def create_env_file():
    """Crea archivo .env desde el ejemplo."""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print("ℹ️ Archivo .env ya existe")
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
    except OSError as e:
        print(f"❌ Error creando .env: {e}")
        return False


def create_activation_scripts():
    """Crea scripts de activación para diferentes sistemas."""
    print("📄 Creando scripts de activación...")

    # Script para Unix/Linux/macOS
    unix_script = """#!/bin/bash
# Script de activación del entorno virtual para Unix/Linux/macOS

echo "🚀 Activando entorno virtual MLB Forecast Backend..."

# Verificar que el entorno virtual existe
if [ ! -d "venv" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta: python scripts/setup_venv.py"
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate

echo "✅ Entorno virtual activado"
echo "📍 Python: $(which python)"
echo "📍 pip: $(which pip)"

echo ""
echo "Comandos disponibles:"
echo "  🚀 Iniciar aplicación: uvicorn app.main:app --reload"
echo "  🐳 Docker completo: docker-compose up --build"
echo "  🔄 Migraciones: python scripts/migrate.py upgrade"
echo "  🧪 Tests: python -m pytest tests/"
echo "  ❌ Desactivar: deactivate"
"""

    # Script para Windows
    windows_script = """@echo off
REM Script de activación del entorno virtual para Windows

echo 🚀 Activando entorno virtual MLB Forecast Backend...

REM Verificar que el entorno virtual existe
if not exist "venv" (
    echo ❌ Entorno virtual no encontrado. Ejecuta: python scripts/setup_venv.py
    exit /b 1
)

REM Activar entorno virtual
call venv\\Scripts\\activate.bat

echo ✅ Entorno virtual activado
python --version
pip --version

echo.
echo Comandos disponibles:
echo   🚀 Iniciar aplicación: uvicorn app.main:app --reload
echo   🐳 Docker completo: docker-compose up --build
echo   🔄 Migraciones: python scripts/migrate.py upgrade
echo   🧪 Tests: python -m pytest tests/
echo   ❌ Desactivar: deactivate
"""

    try:
        with open("activate_venv.sh", "w") as f:
            f.write(unix_script)
        os.chmod("activate_venv.sh", 0o755)  # Hacer ejecutable

        with open("activate_venv.bat", "w") as f:
            f.write(windows_script)

        print("✅ Scripts de activación creados:")
        print("  - activate_venv.sh (Unix/Linux/macOS)")
        print("  - activate_venv.bat (Windows)")
        return True

    except OSError as e:
        print(f"❌ Error creando scripts: {e}")
        return False


def create_directories():
    """Crea directorios necesarios."""
    print("📁 Creando directorios necesarios...")

    directories = ["ml_models", "logs", "data", "exports"]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

    print(f"✅ Directorios creados: {', '.join(directories)}")
    return True


def show_next_steps():
    """Muestra los próximos pasos."""
    activation_script = "activate_venv.bat" if os.name == "nt" else "./activate_venv.sh"

    print(
        f"""
🎉 ¡Configuración del entorno virtual completada!

📋 Próximos pasos:

1. 🔄 Activar el entorno virtual:
   {activation_script}

2. 🚀 Opción A - Ejecutar solo la API (desarrollo):
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

3. 🐳 Opción B - Ejecutar con Docker (completo):
   docker-compose up --build

4. 🌐 Acceder a la aplicación:
   - Documentación API: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

5. 📊 Inicializar datos (opcional):
   curl -X POST http://localhost:8000/api/v1/data/ingest/full

📁 Archivos importantes creados:
  - venv/                 # Entorno virtual
  - .env                  # Variables de entorno
  - activate_venv.sh      # Script activación Unix
  - activate_venv.bat     # Script activación Windows

💡 Consejos:
  - Siempre activa el entorno virtual antes de trabajar
  - Usa 'deactivate' para salir del entorno virtual
  - Revisa el README.md para documentación completa

¡Listo para desarrollar! 🚀⚾
"""
    )


def main():
    """Función principal."""
    print("🏗️ Configuración de Entorno Virtual - MLB Forecast Backend")
    print("=" * 60)

    # Cambiar al directorio del proyecto
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    os.chdir(project_dir)

    print(f"📍 Directorio de trabajo: {os.getcwd()}")

    steps = [
        ("Verificar versión de Python", check_python_version),
        ("Crear entorno virtual", create_virtual_environment),
        ("Instalar dependencias", install_dependencies),
        ("Crear archivo .env", create_env_file),
        ("Crear directorios", create_directories),
        ("Crear scripts de activación", create_activation_scripts),
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

#!/usr/bin/env python3
"""
Quick start script for MLB Forecast Backend.
Detects the system and runs the appropriate setup.
"""

import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


class ProgressSpinner:
    """Spinner animado para mostrar progreso."""

    def __init__(self, message: str = "Procesando"):
        self.message = message
        self.spinning = False
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_char = 0
        self.thread = None

    def _spin(self):
        """Función interna para animar el spinner."""
        while self.spinning:
            char = self.spinner_chars[self.current_char]
            sys.stdout.write(f"\r{char} {self.message}...")
            sys.stdout.flush()
            self.current_char = (self.current_char + 1) % len(self.spinner_chars)
            time.sleep(0.1)

    def start(self):
        """Iniciar el spinner."""
        self.spinning = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self, final_message: str | None = None):
        """Detener el spinner y mostrar mensaje final."""
        self.spinning = False
        if self.thread:
            self.thread.join(timeout=0.2)

        if final_message:
            sys.stdout.write(f"\r✅ {final_message}\n")
        else:
            sys.stdout.write(f"\r✅ {self.message} completado\n")
        sys.stdout.flush()


def create_progress_bar(percentage: int, width: int = 40) -> str:
    """Crea una barra de progreso visual."""
    filled_width = int(width * percentage / 100)
    bar = "█" * filled_width + "░" * (width - filled_width)
    return f"[{bar}] {percentage}%"


def print_banner():
    """Display welcome banner."""
    banner = """
███╗   ███╗██╗     ██████╗     ███████╗ ██████╗ ██████╗ ███████╗ ██████╗ █████╗ ███████╗████████╗
████╗ ████║██║     ██╔══██╗    ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝
██╔████╔██║██║     ██████╔╝    █████╗  ██║   ██║██████╔╝█████╗  ██║     ███████║███████╗   ██║
██║╚██╔╝██║██║     ██╔══██╗    ██╔══╝  ██║   ██║██╔══██╗██╔══╝  ██║     ██╔══██║╚════██║   ██║
██║ ╚═╝ ██║███████╗██████╔╝    ██║     ╚██████╔╝██║  ██║███████╗╚██████╗██║  ██║███████║   ██║
╚═╝     ╚═╝╚══════╝╚═════╝     ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝

🏗️ Configuración Automática de Backend MLB
"""
    print(banner)


def detect_system():
    """Detect the operating system."""
    system = platform.system().lower()
    return system


def check_requirements():
    """Verify system requirements."""
    print("🔍 Verificando requisitos del sistema...")

    requirements = {
        "python": ["python", "--version"],
        "git": ["git", "--version"],
        "docker": ["docker", "--version"],
        "docker-compose": ["docker-compose", "--version"],
    }

    missing = []
    available = []

    for name, command in requirements.items():
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                available.append(name)
                print(f"  ✅ {name}: Disponible")
            else:
                missing.append(name)
                print(f"  ❌ {name}: No disponible")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(name)
            print(f"  ❌ {name}: No encontrado")

    return available, missing


def show_menu():
    """Show menu options."""
    print("\n📋 Selecciona una opción de instalación:")
    print("1. 🐳 Setup con Docker (Recomendado, sin requisitos locales)")
    print("2. ✅ Validar OpenAPI (openapi/openapi.yml)")
    print("3. 🧬 Generar modelos desde OpenAPI (sin rutas autogeneradas)")
    print("4. ℹ️  Mostrar información del proyecto")
    print("5. ❌ Salir")

    while True:
        try:
            choice = input("\nIngresa tu opción (1-5): ").strip()
            if choice in ["1", "2", "3", "4", "5"]:
                return int(choice)
            else:
                print("❌ Opción inválida. Ingresa un número entre 1 y 5.")
        except KeyboardInterrupt:
            print("\n\n👋 Instalación cancelada.")
            sys.exit(0)


def run_docker_build_with_progress(command: str, description: str = "") -> bool:
    """Ejecuta comando Docker build con indicador de progreso específico mejorado."""
    if description:
        print(f"\n🔄 {description}")

    print(f"Ejecutando: {command}")
    spinner = None
    spinner_active = False
    process = None

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # Sin buffering para ver salida inmediata
            universal_newlines=True,
        )

        print("🐳 Construyendo imagen Docker...")

        # Variables para tracking del progreso
        current_step = 0
        total_steps = 0
        last_progress_line = ""

        # Iniciamos con spinner por defecto
        spinner = ProgressSpinner("Preparando construcción")
        spinner.start()
        spinner_active = True

        for line in iter(process.stdout.readline, ""):
            if not line:
                break

            line_clean = line.strip()

            # Detener spinner si está activo para mostrar progreso específico
            if spinner_active and any(
                keyword in line_clean.lower() for keyword in ["step ", "pulling", "downloading", "extracting"]
            ):
                if spinner:
                    spinner.stop()
                    spinner_active = False

            # Detectar número total de pasos al inicio
            if line_clean.startswith("Step ") and "/" in line_clean and total_steps == 0:
                try:
                    # Extraer formato "Step X/Y"
                    step_match = re.search(r"Step\s+(\d+)/(\d+)", line_clean)
                    if step_match:
                        total_steps = int(step_match.group(2))
                        print(f"\n📋 Detectados {total_steps} pasos de construcción")
                except (ValueError, IndexError):
                    pass

            # Mostrar progreso de pasos
            if line_clean.startswith("Step ") and total_steps > 0:
                try:
                    step_match = re.search(r"Step\s+(\d+)/(\d+)", line_clean)
                    if step_match:
                        current_step = int(step_match.group(1))
                        progress = int((current_step / total_steps) * 100)
                        progress_bar = create_progress_bar(progress, 35)

                        # Extraer descripción del paso
                        step_desc = line_clean.split(":", 1)[1].strip() if ":" in line_clean else ""
                        if step_desc:
                            step_desc = step_desc[:50] + "..." if len(step_desc) > 50 else step_desc

                        progress_text = f"📦 {progress_bar} ({current_step}/{total_steps})"
                        if step_desc:
                            progress_text += f" {step_desc}"

                        print(f"\r{progress_text}", end="", flush=True)
                        last_progress_line = progress_text
                except (re.error, ValueError, IndexError):
                    # Si hay error en parsing, mostrar línea completa
                    print(f"\n   {line_clean}")

            # Mostrar progreso de descarga/extracción con mini barra
            elif "%" in line_clean and any(
                keyword in line_clean.lower() for keyword in ["downloading", "extracting", "pulling"]
            ):
                try:
                    match = re.search(r"(\d+(?:\.\d+)?)%", line_clean)
                    if match:
                        percentage = int(float(match.group(1)))
                        mini_bar = create_progress_bar(percentage, 20)

                        # Detectar tipo de operación
                        operation = "Descargando"
                        if "extracting" in line_clean.lower():
                            operation = "Extrayendo"
                        elif "pulling" in line_clean.lower():
                            operation = "Obteniendo"

                        print(f"\r   🔄 {operation}: {mini_bar}", end="", flush=True)

                        # Si llegamos al 100%, agregar nueva línea
                        if percentage >= 100:
                            print()  # Nueva línea
                except ValueError:
                    pass

            # Mostrar líneas importantes siempre
            elif any(
                keyword in line_clean.lower()
                for keyword in [
                    "error",
                    "failed",
                    "successfully built",
                    "successfully tagged",
                    "complete",
                    "finished",
                    "warning",
                    "=> cached",
                ]
            ):
                # Nueva línea si estábamos mostrando progreso inline
                if last_progress_line and not line_clean.startswith("\n"):
                    print()  # Nueva línea
                    last_progress_line = ""

                # Colorear líneas según contenido
                if "error" in line_clean.lower() or "failed" in line_clean.lower():
                    print(f"   ❌ {line_clean}")
                elif "successfully" in line_clean.lower() or "complete" in line_clean.lower():
                    print(f"   ✅ {line_clean}")
                elif "warning" in line_clean.lower():
                    print(f"   ⚠️  {line_clean}")
                elif "cached" in line_clean.lower():
                    print(f"   💾 {line_clean}")
                else:
                    print(f"   ℹ️  {line_clean}")

            # Si no hemos detectado pasos específicos, mantener spinner o mostrar actividad
            elif not total_steps and not spinner_active:
                # Mostrar líneas que indican actividad sin spinner
                if any(
                    keyword in line_clean.lower()
                    for keyword in ["from", "run", "copy", "add", "expose", "cmd", "workdir"]
                ):
                    print(f"   📝 {line_clean}")

        # Limpiar spinner si aún está activo
        if spinner_active and spinner:
            spinner.stop()

        # Asegurar nueva línea al final
        if last_progress_line:
            print()

        process.wait()

        if process.returncode == 0:
            print("✅ Imagen construida exitosamente")
            return True
        else:
            print(f"❌ Error en la construcción (código: {process.returncode})")
            return False

    except Exception as e:
        print(f"\n❌ Error ejecutando comando: {e}")
        return False
    finally:
        # Limpiar recursos
        if "spinner" in locals() and spinner and spinner_active:
            spinner.stop()
        if "process" in locals() and process.poll() is None:
            process.terminate()
            process.wait()


def run_command_with_live_output(command: str, description: str = "") -> bool:
    """
    Versión alternativa que muestra toda la salida en tiempo real.
    Útil para debugging o cuando el progreso específico no funciona.
    """
    if description:
        print(f"\n🔄 {description}")

    print(f"Ejecutando: {command}")

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=0,  # Sin buffering
            universal_newlines=True,
        )

        print("🔍 Salida en tiempo real:")
        print("-" * 50)

        for line in iter(process.stdout.readline, ""):
            if line:
                # Agregar timestamp para mejor tracking
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] {line.rstrip()}")

        process.wait()

        print("-" * 50)
        if process.returncode == 0:
            print("✅ Comando completado exitosamente")
            return True
        else:
            print(f"❌ Error (código: {process.returncode})")
            return False

    except Exception as e:
        print(f"❌ Error ejecutando comando: {e}")
        return False


def run_command_with_spinner(command: str, description: str = "") -> bool:
    """Ejecuta comando genérico con spinner animado."""
    if description:
        print(f"\n🔄 {description}")

    print(f"Ejecutando: {command}")

    spinner = ProgressSpinner("Procesando")
    spinner.start()

    try:
        result = subprocess.run(command, shell=True, text=True, timeout=600, capture_output=True)

        spinner.stop()

        # Mostrar salida después de completar
        if result.stdout:
            print(result.stdout)

        if result.returncode == 0:
            print("✅ Comando completado exitosamente")
            return True
        else:
            print(f"❌ Error (código: {result.returncode})")
            if result.stderr:
                print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        spinner.stop("Comando tardó demasiado (timeout)")
        return False
    except Exception as e:
        spinner.stop(f"Error ejecutando comando: {e}")
        return False


def run_command(command: str, description: str = "") -> bool:
    """
    Función principal mejorada con mejor detección y fallback.
    """
    # Detectar si es comando de Docker con más precisión
    is_docker_build = False
    command_lower = command.lower()

    if any(
        pattern in command_lower
        for pattern in ["docker build", "docker-compose build", "docker compose build", "podman build", "buildah"]
    ):
        is_docker_build = True

    # Variable de entorno para forzar modo de salida
    force_live_output = os.getenv("FORCE_LIVE_OUTPUT", "").lower() in ["1", "true", "yes"]

    if is_docker_build and not force_live_output:
        return run_docker_build_with_progress(command, description)
    elif is_docker_build and force_live_output:
        print("🔧 Usando modo de salida en tiempo real (FORCE_LIVE_OUTPUT=1)")
        return run_command_with_live_output(command, description)
    else:
        return run_command_with_spinner(command, description)


def _compose_cmd() -> str:
    """Return 'docker compose' if available, otherwise 'docker-compose'."""
    try:
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return "docker compose"
    except (FileNotFoundError, OSError):
        pass
    return "docker-compose"


def setup_with_docker():
    """Setup using Docker only."""
    print("\n🐳 Iniciando setup con Docker...")

    compose = _compose_cmd()

    if not Path(".env").exists():
        run_command("cp .env.example .env", "Creando archivo de configuración")

    # Build & Up
    print("\n" + "=" * 60)
    print("🏗️  FASE 1: CONSTRUCCIÓN DE IMÁGENES DOCKER")
    print("=" * 60)
    print("⏱️  Esto puede tomar varios minutos la primera vez...")

    success = run_command(f"{compose} build", "Construyendo servicios Docker")

    if success:
        print("\n" + "=" * 60)
        print("🚀 FASE 2: INICIANDO SERVICIOS")
        print("=" * 60)
        run_command(f"{compose} up -d", "Iniciando servicios Docker en segundo plano")

        print(
            """
            ✅ ¡Configuración básica completada!

            Se crearon los siguientes servicios Docker:
            - app
            - scheduler
            - redis
            - postgres

            1. 📋 Para ver los logs de Docker:
                docker-compose logs -f <servicio>

            Ejemplos:
                docker-compose logs -f app
                docker-compose logs -f scheduler
                docker-compose logs -f redis
                docker-compose logs -f postgres

            2. 🌐 Acceder a la aplicación:
               - Docs: http://localhost:8000/docs
               - Health: http://localhost:8000/api/v1/health

            3. ⏹️ Detener servicios:
               docker-compose down

            4. 🚮 Eliminar contenedores y volúmenes:
                docker system prune -a --volumes

        💡 Tip: Revisa docker-compose.yml para configuración avanzada.
            """
        )
        return True
    else:
        print("\n❌ Error durante la construcción. Por favor, revisa los logs arriba.")
        return False


def validate_openapi() -> bool:
    """
    Validate the OpenAPI specification using the official CLI (same as hook).
    1) Try the 'app' image WITHOUT entrypoint.
    2) If not available, use an ephemeral container with isolated tools.
    """
    compose = _compose_cmd()
    spec = _resolve_openapi_path()
    print(f"\n🧪 Validando {spec} ...")

    # Attempt A: 'app' image without entrypoint (clean shell)
    cmd_a = f'{compose} run --rm --no-deps --entrypoint "" app sh -lc "set -e; openapi-spec-validator {spec}"'
    ok = run_command(cmd_a, "Validando OpenAPI (imagen app)")
    if ok:
        return True

    print("ℹ️  openapi-spec-validator no está disponible en la imagen 'app'. Usando contenedor efímero...")
    # Attempt B: ephemeral container (isolated venv, no root paths)
    cmd_b = (
        'docker run --rm -u "$(id -u):$(id -g)" '
        "-e HOME=/tmp -e PIP_CACHE_DIR=/tmp/pipcache "
        '-v "$PWD":/work -w /work python:3.11 '
        'bash -lc "set -e; '
        "python -m venv /tmp/.venv && "
        ". /tmp/.venv/bin/activate && "
        "python -m pip install -q --upgrade pip && "
        "pip install -q openapi-spec-validator==0.8.0b1 && "
        'openapi-spec-validator openapi/openapi.yml"'
    )
    return run_command(cmd_b, "Validando OpenAPI (contenedor efímero)")


def _postprocess_models(models_file: str) -> bool:
    """
    Convert v1-style root models (__root__ on BaseModel) to Pydantic v2 RootModel,
    and ensure we import from `pydantic` (not `pydantic.v1`) so FastAPI can build OpenAPI.
    """
    p = Path(models_file)
    if not p.exists():
        return False

    src = p.read_text(encoding="utf-8")
    changed = False

    # 1) Ensure v2 imports (BaseModel, Field, RootModel) and remove v1-compat imports if present
    if "from pydantic.v1 import BaseModel" in src:
        src = src.replace(
            "from pydantic.v1 import BaseModel, Field",
            "from pydantic import BaseModel, Field, RootModel, ConfigDict",
        ).replace(
            "from pydantic.v1 import BaseModel",
            "from pydantic import BaseModel, RootModel, ConfigDict",
        )
        changed = True
    if "from pydantic import BaseModel" in src and "RootModel" not in src:
        src = src.replace(
            "from pydantic import BaseModel, Field",
            "from pydantic import BaseModel, Field, RootModel, ConfigDict",
        ).replace(
            "from pydantic import BaseModel",
            "from pydantic import BaseModel, RootModel, ConfigDict",
        )
        changed = True

    # 1.1) Remove Extra import and convert class Config -> model_config with ConfigDict
    if " Extra" in src or "Extra," in src:
        src = src.replace(
            "from pydantic import BaseModel, RootModel, Extra, Field",
            "from pydantic import BaseModel, RootModel, Field, ConfigDict",
        ).replace(
            "from pydantic import BaseModel, Extra, Field",
            "from pydantic import BaseModel, Field, ConfigDict",
        )
        changed = True

    # Replace simple 'class Config: extra = Extra.forbid' patterns
    src = re.sub(
        r"class\s+Config:\s*\n\s*extra\s*=\s*Extra\.forbid",
        "model_config = ConfigDict(extra='forbid')",
        src,
    )

    pattern = re.compile(
        r"class\s+(?P<name>\w+)\(BaseModel\):\s+"
        r"(?:(?:\"\"\".*?\"\"\"\s+)*)?"  # optional docstring
        r"__root__\s*:\s*(?P<typ>[^\n=]+)"
        r"(?:\s*=\s*Field\([^)]*\))?\s*$",
        re.MULTILINE,
    )

    def _repl(m: re.Match) -> str:
        name = m.group("name")
        typ = m.group("typ").strip()
        return f"class {name}(RootModel[{typ}]):\n    pass"

    new_src = pattern.sub(_repl, src)
    if new_src != src:
        src = new_src
        changed = True

    if changed:
        p.write_text(src, encoding="utf-8")
        print("🔧 Converted __root__ BaseModel classes to Pydantic v2 RootModel and fixed imports.")
    else:
        print("ℹ️ No root-model conversion needed.")
    return changed


def generate_from_openapi() -> bool:
    """
    Generate Pydantic models and FastAPI stubs from OpenAPI.

    Strategy:
    - If CODEGEN_FORCE_EPHEMERAL=1 -> use ephemeral python:3.11 toolchain (pinned, v2-ready).
    - Else try the 'app' image first; if it fails, fallback to ephemeral.
    - After generation, if models still contain '__root__' on BaseModel, apply a v1-compat import patch automatically.

    Note: datamodel-codegen requires --output to point to a FILE, not a directory.
    """
    compose = _compose_cmd()
    spec = _resolve_openapi_path()
    print("\n🧬 Generando código desde OpenAPI ...")

    models_dir = "src/interface/rest/generated/models"
    routers_dir = "src/interface/rest/generated/routers"
    models_file = f"{models_dir}/models.py"

    # Clean previous generated models to avoid permission issues
    print("🧹 Cleaning previously generated models...")
    shutil.rmtree(models_dir, ignore_errors=True)
    os.makedirs(models_dir, exist_ok=True)

    base_dirs = f"mkdir -p {models_dir} {routers_dir}"
    detect_flag = 'FLAG="--use-pydantic-v2"; datamodel-codegen --help | grep -q -- "--use-pydantic-v2" || FLAG=""; '
    # Build a resilient FastAPI codegen invocation into a temporary directory.
    routers_tmp = f"{routers_dir}_tmp"

    # Commands split: models first, then routers.
    models_codegen_cmd = (
        f"{base_dirs}; "
        f"{detect_flag}"
        f"datamodel-codegen --input {spec} --input-file-type openapi "
        f"--output {models_file} "
        "$FLAG "
        "--target-python-version 3.11 "
        "--enum-field-as-literal all --strict-nullable"
    )

    # Try using the app image for models only
    cmd_models_a = f'{compose} run --rm --no-deps --entrypoint "" app sh -lc "set -e; {models_codegen_cmd}"'
    cmd_models_b = (
        'docker run --rm -u "$(id -u):$(id -g)" '
        "-e HOME=/tmp -e PIP_CACHE_DIR=/tmp/pipcache "
        '-v "$PWD":/work -w /work python:3.11 '
        'bash -lc "set -e; '
        "python -m venv /tmp/.venv && "
        ". /tmp/.venv/bin/activate && "
        "python -m pip install -q --upgrade pip && "
        "pip install -q datamodel-code-generator==0.30.1 PyYAML==6.0.2 Jinja2==3.1.4 && "
        f'{models_codegen_cmd}"'
    )

    # Routers codegen uses the ephemeral toolchain; pip installs the generator as needed inside command
    # Prepare a robust shell script for routers generation to avoid quoting issues
    routers_shell = (
        f"set -e; "
        f"python -m venv /tmp/.venv && . /tmp/.venv/bin/activate && "
        f"python -m pip install -q --upgrade pip && "
        f"(python -m pip install -q fastapi-code-generator==0.5.4 || true); "
        f"rm -rf {routers_tmp} && mkdir -p {routers_tmp}; "
        # Attempt several CLI variants to accommodate different versions
        # 1) Preferred short flags
        f"(fastapi-codegen -i {spec} -o {routers_tmp} || "
        f" python -m fastapi_code_generator -i {spec} -o {routers_tmp} || "
        # 2) Long flags with --output-dir
        f" fastapi-codegen --input {spec} --output-dir {routers_tmp} || "
        f" python -m fastapi_code_generator --input {spec} --output-dir {routers_tmp} || "
        # 3) Positional args: input then output
        f" fastapi-codegen {spec} {routers_tmp} || "
        f" python -m fastapi_code_generator {spec} {routers_tmp} || "
        # 4) Fallback to older generator version and try again
        f" (python -m pip install -q fastapi-code-generator==0.4.5 && "
        f"   (fastapi-codegen -i {spec} -o {routers_tmp} || "
        f"    python -m fastapi_code_generator -i {spec} -o {routers_tmp} || "
        f"    fastapi-codegen {spec} {routers_tmp} || "
        f"    python -m fastapi_code_generator {spec} {routers_tmp}))) ; "
        # Ensure we actually produced python files
        f"sh -lc 'ls -1 {routers_tmp}/*.py >/dev/null 2>&1' ; "
        f"rm -rf {routers_dir} && mv {routers_tmp} {routers_dir}"
    )

    cmd_routers_b = (
        'docker run --rm -u "$(id -u):$(id -g)" '
        "-e HOME=/tmp -e PIP_CACHE_DIR=/tmp/pipcache "
        '-v "$PWD":/work -w /work python:3.11 '
        f'bash -lc "{routers_shell}"'
    )

    force_ephemeral = os.getenv("CODEGEN_FORCE_EPHEMERAL") == "1"

    # 1) Generate models
    if force_ephemeral:
        ok_models = run_command(cmd_models_b, "Generating Pydantic models from OpenAPI (ephemeral toolchain)")
    else:
        ok_models = run_command(cmd_models_a, "Generating Pydantic models from OpenAPI (app image)")
        if not ok_models:
            print("ℹ️  Tools not available in 'app'. Using ephemeral toolchain...")
            ok_models = run_command(cmd_models_b, "Generating Pydantic models from OpenAPI (ephemeral toolchain)")

    if not ok_models:
        print("❌ Models generation failed.")
        return False

    # Always postprocess models to ensure Pydantic v2 compatibility
    _postprocess_models(models_file)

    # 2) Optionally generate routers
    if os.getenv("CODEGEN_SKIP_ROUTERS", "1").lower() in ("1", "true", "yes"):
        print("ℹ️ Skipping routers generation by default (models only). Set CODEGEN_SKIP_ROUTERS=0 to enable.")
        print("📦 Generated models are available at src/interface/rest/generated/models")
        return True

    ok_routers = run_command(cmd_routers_b, "Generating FastAPI routers from OpenAPI (ephemeral toolchain)")
    if not ok_routers:
        print("❌ Routers generation failed. Preserving existing generated routers.")
        print("📦 Models were updated successfully.")
        return True

    print("📦 Code generated at src/interface/rest/generated")
    return True


def show_info():
    """Display project information."""
    print(
        """
📚 MLB Forecast Backend - Información del Proyecto

🎯 Descripción:
   Sistema completo de backend para pronósticos de partidos de MLB
   con machine learning, APIs REST y automatización.

🏗️ Arquitectura:
   - FastAPI para APIs REST
   - PostgreSQL para almacenamiento
   - Redis para caché
   - scikit-learn para ML
   - Docker para contenedores
   - Arquitectura Hexagonal (Ports & Adapters)

📁 Estructura Principal:
   src/                           # Nueva arquitectura hexagonal
   ├── domain/                   # Entidades y reglas de negocio
   │   └── entities/             # Entidades del dominio
   ├── application/              # Casos de uso y puertos
   │   ├── ports/                # Interfaces para adaptadores
   │   └── use_cases/            # Casos de uso de la aplicación
   ├── infrastructure/           # Adaptadores para servicios externos
   │   ├── cache/                # Adaptador para Redis
   │   ├── config/               # Configuración
   │   ├── db/                   # Base de datos y repositorios
   │   ├── ml/                   # Adaptador para modelos ML
   │   └── mlb_api/              # Adaptador para API MLB
   └── interface/                # Interfaces de usuario
       └── rest/                 # API REST con FastAPI

   app/                           # Código legacy (deprecado)

🔗 Enlaces Útiles:
   - Documentación completa: README.md
   - Configuración: .env.example
   - Scripts: scripts/
   - Tests: tests/

🚀 Comandos Rápidos:
   make setup        # Configuración inicial
   make run          # Ejecutar aplicación
   make test         # Ejecutar pruebas
   make help         # Ver todos los comandos

💡 ¿Necesitas ayuda?
   Revisa el README.md para documentación completa.
"""
    )


def _resolve_openapi_path() -> str:
    """Return the path to the OpenAPI file; prefer openapi/openapi.yml."""
    candidates = [Path("openapi/openapi.yml"), Path("openapi.yml")]
    for c in candidates:
        if c.exists():
            return str(c)
    # explicit fallback so the error is clear if it does not exist
    return "openapi/openapi.yml"


def main():
    print_banner()

    # Ensure we are at repo root
    if not Path("requirements.txt").exists() or (not Path("app").exists() and not Path("src").exists()):
        print("❌ Error: Este script debe ejecutarse desde el directorio raíz del proyecto.")
        print("📁 Asegúrate de estar en el directorio 'mlb_forecast_backend'.")
        sys.exit(1)

    # Verify system requirements
    available, missing = check_requirements()

    if missing:
        print(f"\n⚠️ Herramientas faltantes: {', '.join(missing)}")
        print("💡 Algunas opciones pueden no estar disponibles.")

    # Menu loop
    while True:
        choice = show_menu()

        if choice == 1:
            if "docker" in available:
                setup_with_docker()
                break
            else:
                print("❌ Docker no está disponible. Instala Docker primero.")
        elif choice == 2:
            validate_openapi()
            continue
        elif choice == 3:
            generate_from_openapi()
            continue
        elif choice == 4:
            show_info()
            continue
        elif choice == 5:
            print("👋 ¡Hasta luego!")
            sys.exit(0)

        # Continue?
        if choice != 4:
            try:
                cont = input("\n¿Quieres seleccionar otra opción? (s/n): ").lower().strip()
                if cont not in ["s", "sí", "si", "y", "yes"]:
                    break
            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                sys.exit(0)

    print("\n🎉 ¡Gracias por usar MLB Forecast Backend!")


if __name__ == "__main__":
    main()

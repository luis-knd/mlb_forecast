#!/usr/bin/env python3
"""
Script de utilidad para ejecutar migraciones de base de datos.
"""

import subprocess
import sys


def run_command(command):
    """Ejecuta un comando y maneja errores."""
    print(f"Ejecutando: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Comando ejecutado exitosamente")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ Error ejecutando comando")
        if result.stderr:
            print(result.stderr)
        return False

    return True


def create_migration(message):
    """Crea una nueva migración."""
    command = f"alembic revision --autogenerate -m '{message}'"
    return run_command(command)


def run_migrations():
    """Ejecuta todas las migraciones pendientes."""
    command = "alembic upgrade head"
    return run_command(command)


def show_migration_history():
    """Muestra el historial de migraciones."""
    command = "alembic history"
    return run_command(command)


def show_current_revision():
    """Muestra la revisión actual."""
    command = "alembic current"
    return run_command(command)


def downgrade_migration(revision="base"):
    """Revierte migraciones."""
    command = f"alembic downgrade {revision}"
    return run_command(command)


def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print(
            """
Uso: python migrate.py <comando> [argumentos]

Comandos disponibles:
  create <mensaje>     - Crear nueva migración
  upgrade             - Ejecutar migraciones pendientes
  history             - Mostrar historial de migraciones
  current             - Mostrar revisión actual
  downgrade [rev]     - Revertir migraciones (por defecto a base)

Ejemplos:
  python migrate.py create "Agregar tabla de usuarios"
  python migrate.py upgrade
  python migrate.py history
  python migrate.py downgrade -1
        """
        )
        return

    command = sys.argv[1].lower()

    if command == "create":
        if len(sys.argv) < 3:
            print("Error: Debe proporcionar un mensaje para la migración")
            return
        message = " ".join(sys.argv[2:])
        create_migration(message)

    elif command == "upgrade":
        run_migrations()

    elif command == "history":
        show_migration_history()

    elif command == "current":
        show_current_revision()

    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "base"
        downgrade_migration(revision)

    else:
        print(f"Comando desconocido: {command}")


if __name__ == "__main__":
    main()

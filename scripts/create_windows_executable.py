"""Build the Streamlit application as a Windows executable.

This helper is designed to be executed on a Windows machine.  It removes any
previous build artefacts, ensures that PyInstaller is available and then
packages :mod:`run.py` into a single-file ``.exe`` that can be distributed to
end users.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRY_POINT = PROJECT_ROOT / "run.py"
EXECUTABLE_NAME = "anonymizer_app"


def _assert_windows_platform() -> None:
    """Warn when the script is executed on a non-Windows platform."""

    if not sys.platform.startswith("win"):
        print(
            "⚠️  Ce script est prévu pour être exécuté depuis Windows.\n"
            "    Vous pouvez toujours créer l'exécutable sous Linux en utilisant\n"
            "    `build_windows_executable.py` mais le résultat est garanti\n"
            "    uniquement lorsque la compilation est faite sur Windows."
        )


def _ensure_entry_point() -> None:
    """Check that the Streamlit entry point is available."""

    if not ENTRY_POINT.exists():
        raise FileNotFoundError(
            "Le fichier run.py est introuvable. Exécutez ce script depuis la racine du projet."
        )


def _ensure_pyinstaller() -> None:
    """Install PyInstaller if it is missing from the environment."""

    try:
        import PyInstaller  # type: ignore  # noqa: F401
    except ImportError:
        print("📦 Installation de PyInstaller…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])



def _cleanup_previous_builds() -> None:
    """Remove artefacts produced by earlier PyInstaller runs."""

    for directory in (PROJECT_ROOT / "build", PROJECT_ROOT / "dist"):
        if directory.exists():
            print(f"🧹 Suppression du dossier {directory}…")
            shutil.rmtree(directory)

    spec_file = PROJECT_ROOT / f"{EXECUTABLE_NAME}.spec"
    if spec_file.exists():
        print("🧹 Suppression de l'ancien fichier .spec…")
        spec_file.unlink()



def _resource_arguments(resources: list[Path]) -> list[str]:
    """Return ``--add-data`` arguments for PyInstaller."""

    arguments: list[str] = []
    for resource in resources:
        if resource.exists():
            destination = resource.name
            arguments.extend([
                "--add-data",
                f"{resource}{os.pathsep}{destination}",
            ])
    return arguments



def build_windows_executable() -> None:
    """Invoke PyInstaller so that it produces ``anonymizer_app.exe``."""

    _assert_windows_platform()
    _ensure_entry_point()
    _ensure_pyinstaller()
    _cleanup_previous_builds()

    command = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        EXECUTABLE_NAME,
        "--collect-all",
        "streamlit",
        "--collect-submodules",
        "src",
    ]

    resources = [PROJECT_ROOT / "data", PROJECT_ROOT / "docs"]
    command.extend(_resource_arguments(resources))
    command.append(str(ENTRY_POINT))

    print("🚀 Lancement de PyInstaller…")
    subprocess.check_call(command)

    executable = PROJECT_ROOT / "dist" / f"{EXECUTABLE_NAME}.exe"
    if executable.exists():
        print("✅ Exécutable généré :", executable)
    else:
        print("⚠️ PyInstaller a terminé mais l'exécutable n'a pas été trouvé dans dist/.\n"
              "   Vérifiez les messages précédents pour diagnostiquer le problème.")



def main() -> None:
    try:
        build_windows_executable()
    except subprocess.CalledProcessError as exc:  # pragma: no cover - runtime failure helper
        print("❌ Échec de la création de l'exécutable.")
        print("Commande:", " ".join(map(str, exc.cmd if isinstance(exc.cmd, (list, tuple)) else [exc.cmd])))
        print("Code de retour:", exc.returncode)
        sys.exit(exc.returncode)
    except Exception as exc:  # pragma: no cover - safeguard for runtime errors
        print(f"❌ Erreur: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

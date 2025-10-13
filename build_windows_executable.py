"""Utilities to package the Streamlit application as a Windows executable.

Running this script will build a standalone ``.exe`` in the ``dist`` folder
using PyInstaller.  The script installs PyInstaller if it is missing, cleans up
previous build artefacts, and bundles the resources required by the
application.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_ROOT / "run.py"
EXECUTABLE_NAME = "anonymizer_app"


def ensure_entry_point() -> None:
    """Make sure the entry script exists before invoking PyInstaller."""

    if not ENTRY_POINT.exists():
        raise FileNotFoundError(
            "Le fichier run.py est introuvable. Exécutez ce script depuis la racine du projet."
        )


def ensure_pyinstaller() -> None:
    """Install PyInstaller if it is not already available."""

    try:
        import PyInstaller  # type: ignore  # noqa: F401 - only check availability
    except ImportError:  # pragma: no cover - executed only when missing
        print("📦 Installation de PyInstaller…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def resource_arguments(resources: Iterable[Path]) -> List[str]:
    """Return the ``--add-data`` options for the provided resources."""

    arguments: List[str] = []
    for resource in resources:
        if not resource.exists():
            continue

        destination = resource.name
        arguments.extend([
            "--add-data",
            f"{resource}{os.pathsep}{destination}",
        ])

    return arguments


def clean_previous_builds() -> None:
    """Remove previous build artefacts to ensure a fresh build."""

    for directory in (PROJECT_ROOT / "build", PROJECT_ROOT / "dist"):
        if directory.exists():
            print(f"🧹 Suppression du dossier {directory}…")
            shutil.rmtree(directory)

    spec_file = PROJECT_ROOT / f"{EXECUTABLE_NAME}.spec"
    if spec_file.exists():
        print("🧹 Suppression de l'ancien fichier .spec…")
        spec_file.unlink()


def build_executable() -> None:
    """Invoke PyInstaller with the required options."""

    ensure_entry_point()
    ensure_pyinstaller()

    from PyInstaller.__main__ import run as pyinstaller_run

    clean_previous_builds()

    resources = [
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "docs",
    ]

    command = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        EXECUTABLE_NAME,
        "--collect-all",
        "streamlit",
        "--collect-all",
        "docx",
        "--collect-all",
        "pdfplumber",
        "--collect-all",
        "pdf2docx",
        "--collect-submodules",
        "src",
    ]

    command.extend(resource_arguments(resources))
    command.append(str(ENTRY_POINT))

    print("🚀 Lancement de PyInstaller…")
    pyinstaller_run(command)

    executable_candidates = []
    if sys.platform.startswith("win"):
        executable_candidates.append(PROJECT_ROOT / "dist" / f"{EXECUTABLE_NAME}.exe")
    else:
        # ``--onefile`` on Unix platforms produces a binary without an extension.
        executable_candidates.append(PROJECT_ROOT / "dist" / EXECUTABLE_NAME)
        # Some PyInstaller configurations may still output ``.exe`` or ``.app``,
        # so keep these variants as fallbacks.
        executable_candidates.append(PROJECT_ROOT / "dist" / f"{EXECUTABLE_NAME}.exe")
        executable_candidates.append(PROJECT_ROOT / "dist" / f"{EXECUTABLE_NAME}.app")

    for candidate in executable_candidates:
        if candidate.exists():
            print("✅ Exécutable généré :", candidate)
            break
    else:
        print("⚠️ PyInstaller ne semble pas avoir produit l'exécutable attendu.")


def main() -> None:
    """Script entry point."""

    try:
        build_executable()
    except subprocess.CalledProcessError as exc:
        print("❌ Échec de la création de l'exécutable.")
        print("Commande:", " ".join(exc.cmd if isinstance(exc.cmd, list) else [exc.cmd]))
        print("Code de retour:", exc.returncode)
        sys.exit(exc.returncode)
    except Exception as exc:  # pragma: no cover - safeguard for runtime errors
        print(f"❌ Erreur: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()


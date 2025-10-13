from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    entry_point = project_root / "run.py"
    if not entry_point.exists():
        print("❌ run.py introuvable. Lancez ce script depuis la racine du projet.")
        sys.exit(1)

    log_path = Path.cwd() / "build.log"
    log_lines: list[str] = []

    def log(message: str) -> None:
        print(message)
        log_lines.append(message)

    start_time = datetime.now()
    log(f"Début du build : {start_time.isoformat(timespec='seconds')}")

    log("[1/3] Nettoyage des artefacts précédents…")
    for path in (project_root / "build", project_root / "dist"):
        if path.exists():
            try:
                shutil.rmtree(path)
                log(f"  Suppression de {path}")
            except Exception as exc:
                log(f"  Impossible de supprimer {path}: {exc}")
    spec_file = project_root / "anonymizer_app.spec"
    if spec_file.exists():
        try:
            spec_file.unlink()
            log(f"  Suppression de {spec_file}")
        except Exception as exc:
            log(f"  Impossible de supprimer {spec_file}: {exc}")

    hidden_imports = [
        "python-docx",
        "pdfplumber",
        "pdf2docx",
        "fitz",
        "spacy",
        "transformers",
    ]
    command = [
        "pyinstaller",
        "--onefile",
        "--name",
        "anonymizer_app",
    ]
    for module in hidden_imports:
        command.extend(["--hidden-import", module])
    command.extend([
        "--exclude-module",
        "tensorflow",
        "--exclude-module",
        "keras",
        str(entry_point),
    ])

    log("[2/3] Lancement de PyInstaller…")
    result = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    log("Commande exécutée : " + " ".join(command))
    if result.stdout:
        log("--- stdout ---")
        for line in result.stdout.strip().splitlines():
            print(line)
            log_lines.append(line)
    if result.stderr:
        log("--- stderr ---")
        for line in result.stderr.strip().splitlines():
            print(line)
            log_lines.append(line)

    executable = project_root / "dist" / "anonymizer_app.exe"

    if result.returncode == 0 and executable.exists():
        log("[3/3] Build terminé avec succès.")
        finish_time = datetime.now()
        log(f"Fin du build : {finish_time.isoformat(timespec='seconds')}")
        log(f"Durée : {finish_time - start_time}")
        with log_path.open("w", encoding="utf-8") as log_file:
            log_file.write("\n".join(log_lines))
        print(f"✅ Exécutable disponible : {executable.resolve()}")
    else:
        log("[3/3] Échec du build.")
        finish_time = datetime.now()
        log(f"Fin du build : {finish_time.isoformat(timespec='seconds')}")
        log(f"Durée : {finish_time - start_time}")
        with log_path.open("w", encoding="utf-8") as log_file:
            log_file.write("\n".join(log_lines))
        print("❌ La création de l'exécutable a échoué. Consultez build.log pour les détails.")
        if result.stderr:
            print(result.stderr.strip())
        sys.exit(result.returncode or 1)


if __name__ == "__main__":
    main()

import sys
import zipfile

FICHIERS_OBLIGATOIRES = [
    "install_and_run.bat",
    "run_app.bat",
    "LISEZMOI.txt",
    "main.py",
    "requirements.txt",
    "src/__init__.py",
    "src/anonymizer.py",
    "src/entity_manager.py",
    "src/config.py",
    "src/utils.py",
]


def verifier_zip(chemin_zip: str) -> bool:
    """Verifie la presence des fichiers indispensables dans le ZIP."""
    print(f"Verification de {chemin_zip}...")

    with zipfile.ZipFile(chemin_zip, "r") as archive:
        fichiers_zip = archive.namelist()

    manquants = []
    for fichier in FICHIERS_OBLIGATOIRES:
        if any(element.endswith(fichier) for element in fichiers_zip):
            print(f"✓ {fichier}")
        else:
            print(f"✗ {fichier} MANQUANT")
            manquants.append(fichier)

    if manquants:
        print(f"\n❌ {len(manquants)} fichier(s) manquant(s)")
        return False

    print("\n✅ Tous les fichiers obligatoires sont presents")
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python verifier_zip.py chemin/vers/anonymiseur.zip")
        return 1

    chemin_zip = argv[1]

    try:
        resultat = verifier_zip(chemin_zip)
    except FileNotFoundError:
        print(f"Le fichier {chemin_zip} est introuvable.")
        return 1
    except zipfile.BadZipFile:
        print(f"Le fichier {chemin_zip} n'est pas un ZIP valide.")
        return 1

    return 0 if resultat else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

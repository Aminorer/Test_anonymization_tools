#!/usr/bin/env python3
"""Script CLI pour évaluer l'anonymiseur sur un corpus."""
import argparse
from src.anonymizer import evaluate

def main():
    parser = argparse.ArgumentParser(description="Benchmark de l'anonymiseur")
    parser.add_argument("--dataset", default="data/benchmark", help="Dossier du corpus")
    parser.add_argument("--output", default="benchmark_report.csv", help="Fichier de sortie CSV")
    args = parser.parse_args()

    df = evaluate(args.dataset)
    df.to_csv(args.output, index=False)
    print(f"Rapport sauvegardé dans {args.output}")

if __name__ == "__main__":
    main()

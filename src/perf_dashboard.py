import json
from pathlib import Path
import streamlit as st

METRICS_FILE = Path("temp") / "metrics.json"

def load_metrics():
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}

def display_performance_dashboard():
    """Affiche les métriques de performance de l'anonymisation"""
    metrics = load_metrics()
    st.header("📈 Performance de l'anonymisation")
    col1, col2, col3 = st.columns(3)
    precision = metrics.get("precision")
    recall = metrics.get("recall")
    processing_time = metrics.get("processing_time")
    col1.metric(
        "Précision",
        f"{precision*100:.2f}%" if isinstance(precision, (int, float)) else "N/A",
    )
    col2.metric(
        "Rappel",
        f"{recall*100:.2f}%" if isinstance(recall, (int, float)) else "N/A",
    )
    col3.metric(
        "Temps de traitement",
        f"{processing_time:.2f}s" if isinstance(processing_time, (int, float)) else "N/A",
    )


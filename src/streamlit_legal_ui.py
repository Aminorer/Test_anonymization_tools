import streamlit as st
from typing import Dict, List, Any

from src.variant_management_ui import (
    VariantManager,
    display_entity_group_compact,
    display_variant_management,
)


def display_legal_dashboard(
    analysis: Dict[str, Any],
    entity_summary: Dict[str, List[str]],
    recommendations: List[str],
) -> None:
    """Display the legal document analysis dashboard.

    Parameters
    ----------
    analysis:
        Mapping containing details about the document (type, complexity,
        rgpd_score).
    entity_summary:
        Mapping of legal categories to detected entities.
    recommendations:
        List of contextual recommendations to display.
    """
    st.header("\ud83d\udcc8 Tableau de bord juridique")

    col1, col2, col3 = st.columns(3)
    col1.metric("Type de document", analysis.get("type", "N/A"))
    col2.metric("Complexit\u00e9", analysis.get("complexity", "N/A"))
    col3.metric("Score RGPD", analysis.get("rgpd_score", "N/A"))

    st.subheader("Entit\u00e9s d\u00e9tect\u00e9es par cat\u00e9gorie")
    for category, entities in entity_summary.items():
        with st.expander(category):
            st.write(", ".join(entities) if entities else "Aucune entit\u00e9")

    if recommendations:
        st.subheader("Recommandations contextuelles")
        for rec in recommendations:
            st.info(rec)

    st.subheader("Actions rapides")
    action_col1, action_col2 = st.columns(2)
    action_col1.button("\u2705 Valider")
    action_col2.button("\ud83d\udce4 Exporter")


def display_legal_entity_manager(groups: List[Dict[str, Any]]) -> None:
    """Display and manage entity groups and their variants."""

    st.header("\ud83d\uddc3\ufe0f Gestionnaire d'entit\u00e9s")
    manager = VariantManager(groups)

    for group in list(manager.groups.values()):
        display_entity_group_compact(group)
        if st.session_state.get(f"show_details_{group['id']}"):
            display_variant_management(group, manager)
            if st.button("\u2b05\ufe0f Retour", key=f"back_{group['id']}"):
                st.session_state[f"show_details_{group['id']}"] = False
                st.experimental_rerun()
            st.write("---")

    delete_id = st.session_state.get("delete_group")
    if delete_id in manager.groups:
        del manager.groups[delete_id]
        st.session_state.pop("delete_group", None)
        groups[:] = list(manager.groups.values())
        st.experimental_rerun()

    groups[:] = list(manager.groups.values())

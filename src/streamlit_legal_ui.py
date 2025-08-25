import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional

from src.variant_manager_ui import (
    VariantManager,
    display_entity_group_compact,
    display_variant_management,
)
from src.entity_manager import EntityManager


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


def display_legal_entity_manager(
    groups: List[Dict[str, Any]],
    entity_manager: Optional[EntityManager] = None,
) -> None:
    """Display and manage entity groups and their variants."""

    st.header("\ud83d\uddc3\ufe0f Gestionnaire d'entit\u00e9s")
    manager = VariantManager(groups)

    # Search field to filter groups by token
    search_term = st.text_input("Rechercher un groupe", "").lower()

    filtered_groups = {
        gid: g
        for gid, g in manager.groups.items()
        if search_term in g.get("token", "").lower()
    }

    # Header for the table
    header_cols = st.columns([3, 2, 1, 1])
    header_cols[0].markdown("**Token**")
    header_cols[1].markdown("**Occurrences**")
    header_cols[2].markdown("**Gérer**")
    header_cols[3].markdown("**Supprimer**")

    table_rows: List[Dict[str, Any]] = []
    for gid, group in filtered_groups.items():
        cols = st.columns([3, 2, 1, 1])
        token = group.get("token")
        occurrences = group.get("total_occurrences", 0)
        cols[0].write(token)
        cols[1].write(occurrences)
        manage_clicked = cols[2].button("Gérer", key=f"manage_{gid}")
        delete_clicked = cols[3].button("Supprimer", key=f"delete_{gid}")

        table_rows.append(
            {
                "Token": token,
                "Occurrence Count": occurrences,
                "Manage": manage_clicked,
                "Delete": delete_clicked,
                "id": gid,
            }
        )

        if manage_clicked:
            st.session_state[f"show_details_{gid}"] = True
        if delete_clicked:
            st.session_state["delete_group"] = gid

    # Display the table for reference (non-interactive)
    st.dataframe(
        pd.DataFrame(table_rows)[["Token", "Occurrence Count", "Manage", "Delete"]],
        hide_index=True,
    )

    # Show variant management for selected groups
    for group in list(manager.groups.values()):
        if st.session_state.get(f"show_details_{group['id']}"):
            display_variant_management(group, manager)
            if st.button("\u2b05\ufe0f Retour", key=f"back_{group['id']}"):
                st.session_state[f"show_details_{group['id']}"] = False
                st.rerun()
            st.write("---")

    delete_id = st.session_state.get("delete_group")
    if delete_id in manager.groups:
        del manager.groups[delete_id]
        st.session_state.pop("delete_group", None)
        groups[:] = list(manager.groups.values())
        st.rerun()

    groups[:] = list(manager.groups.values())

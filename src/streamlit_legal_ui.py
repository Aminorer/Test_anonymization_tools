import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional

from src.variant_manager_ui import (
    VariantManager,
    display_entity_group_compact,
    display_variant_management,
)
from src.group_ui_utils import mark_groups_for_management, delete_groups
from src.entity_manager import EntityManager
from src.locale import get_locale, LOCALES


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
    language: Optional[str] = None,
) -> None:
    """Display and manage entity groups and their variants."""

    lang = language or st.session_state.get("language", "en")
    if language is None:
        lang = st.selectbox(
            LOCALES[lang]["language_label"],
            options=list(LOCALES.keys()),
            format_func=lambda x: LOCALES[x]["language_name"],
            index=list(LOCALES.keys()).index(lang),
        )
        st.session_state["language"] = lang
    texts = get_locale(lang)

    st.header(texts["entity_manager_header"])
    manager = VariantManager(groups)
    search = st.text_input("Rechercher un groupe", "")

    # Feedback after a successful deletion
    if st.session_state.pop("delete_success", False):
        st.success(texts["delete_success"])

    # Filter groups by search term
    if search:
        filtered_groups = {
            gid: g
            for gid, g in manager.groups.items()
            if search.lower() in g.get("token", "").lower()
        }
    else:
        filtered_groups = manager.groups

    # Header for the table
    header_cols = st.columns([3, 2, 1, 1])
    header_cols[0].markdown(f"**{texts['table_token']}**")
    header_cols[1].markdown(f"**{texts['table_occurrences']}**")
    header_cols[2].markdown(f"**{texts['table_manage']}**")
    header_cols[3].markdown(f"**{texts['table_delete']}**")

    table_rows: List[Dict[str, Any]] = []
    selected_manage: List[str] = []
    selected_delete: List[str] = []
    for gid, group in filtered_groups.items():
        cols = st.columns([3, 2, 1, 1])
        token = group.get("token")
        occurrences = group.get("total_occurrences", 0)
        cols[0].write(token)
        cols[1].write(occurrences)
        manage_checked = cols[2].checkbox("", key=f"manage_{gid}")
        delete_checked = cols[3].checkbox("", key=f"delete_{gid}")

        if manage_checked:
            selected_manage.append(gid)
        if delete_checked:
            selected_delete.append(gid)

        table_rows.append(
            {
                texts["table_token"]: token,
                texts["table_occurrences"]: occurrences,
                texts["table_manage"]: manage_checked,
                texts["table_delete"]: delete_checked,
                "id": gid,
            }
        )

    # Display the table for reference (non-interactive)
    df = pd.DataFrame(
        table_rows,
        columns=[
            texts["table_token"],
            texts["table_occurrences"],
            texts["table_manage"],
            texts["table_delete"],
        ],
    )
    st.dataframe(df, hide_index=True)

    # Bulk operation buttons
    bulk_cols = st.columns(2)
    if bulk_cols[0].button(texts["manage_selection"], disabled=not selected_manage):
        mark_groups_for_management(st.session_state, selected_manage)
        st.rerun()

    if bulk_cols[1].button(texts["delete_selection"], disabled=not selected_delete):
        st.session_state["show_delete_modal"] = True
        st.session_state["pending_delete"] = list(selected_delete)

    if st.session_state.get("show_delete_modal"):
        with st.modal(texts["confirm_delete"]):
            st.write(texts["delete_confirmation_question"])
            modal_cols = st.columns(2)
            if modal_cols[0].button(texts["delete_confirm"], key="confirm_delete"):
                delete_groups(
                    manager,
                    groups,
                    st.session_state,
                    st.session_state.get("pending_delete", []),
                )
                st.session_state["show_delete_modal"] = False
                st.session_state["delete_success"] = True
                st.rerun()
            if modal_cols[1].button(texts["delete_cancel"], key="cancel_delete"):
                st.session_state["show_delete_modal"] = False
                st.rerun()

    # Show variant management for selected groups
    for group in list(manager.groups.values()):
        if st.session_state.get(f"show_details_{group['id']}"):
            display_variant_management(group, manager)
            if st.button(texts["back"], key=f"back_{group['id']}"):
                st.session_state[f"show_details_{group['id']}"] = False
                st.rerun()
            st.write("---")

    groups[:] = list(manager.groups.values())

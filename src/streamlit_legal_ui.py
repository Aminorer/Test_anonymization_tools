import streamlit as st
from typing import Dict, List, Any


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


def display_legal_entity_manager(groups: Dict[str, List[Dict[str, Any]]]) -> None:
    """Display and manage entities grouped by legal roles.

    Parameters
    ----------
    groups:
        Mapping of roles (Parties, Avocats, Tiers, R\u00e9f\u00e9rences) to a list
        of entity dictionaries. Each entity can contain the keys ``name`` and
        ``category``.
    """
    st.header("\ud83d\udcdd Gestionnaire d'entit\u00e9s")

    roles = ["Parties", "Avocats", "Tiers", "R\u00e9f\u00e9rences"]
    for role in roles:
        entities = groups.get(role, [])
        with st.expander(role):
            if not entities:
                st.write("Aucune entit\u00e9")
            for idx, entity in enumerate(entities):
                col_a, col_b = st.columns([3, 1])
                col_a.text_input(
                    "Nom", entity.get("name", ""), key=f"{role}_{idx}_name"
                )
                approved = col_b.checkbox(
                    "Approuv\u00e9", value=entity.get("approved", False), key=f"{role}_{idx}_ok"
                )
                entity["approved"] = approved
            if entities:
                if st.button(f"Fusionner les variantes - {role}"):
                    st.success("Variantes fusionn\u00e9es")
                if st.button(f"Exporter le rapport - {role}"):
                    st.success("Rapport de tra\u00e7abilit\u00e9 export\u00e9")

import streamlit as st
import pandas as pd
from typing import Any, Dict, List, Optional

from src.entity_manager import EntityManager
from src.locale import get_locale, LOCALES
from src.config import ENTITY_COLORS


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
    """Display and manage entity groups with advanced controls."""

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

    st.markdown(
        """
        <style>
        .group-table {width:100%;}
        .token-badge{padding:2px 6px;border-radius:4px;color:#fff;background:#333;}
        .action-button button{margin-right:4px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("selected_groups", [])
    st.session_state.setdefault("group_filters", {"query": "", "types": []})
    st.session_state.setdefault(
        "table_sort", {"column": texts["table_token"], "ascending": True}
    )
    st.session_state.setdefault("table_page", 0)

    filters = st.session_state["group_filters"]
    filters["query"] = st.text_input(texts["search_group"], filters.get("query", ""))
    type_options = sorted({g.get("type", "") for g in groups if g.get("type")})
    filters["types"] = st.multiselect(
        texts["table_type"], type_options, default=filters.get("types", [])
    )
    st.session_state["group_filters"] = filters

    sort = st.session_state["table_sort"]
    sort_cols = [texts["table_token"], texts["table_type"], texts["table_occurrences"]]
    sort["column"] = st.selectbox("Sort", sort_cols, index=sort_cols.index(sort["column"]))
    sort["ascending"] = st.radio("Order", ["asc", "desc"], index=0 if sort["ascending"] else 1) == "asc"
    st.session_state["table_sort"] = sort

    def _match(g: Dict[str, Any]) -> bool:
        q = filters["query"].lower()
        if q and q not in g.get("token", "").lower():
            return False
        if filters["types"] and g.get("type") not in filters["types"]:
            return False
        return True

    filtered = [g for g in groups if _match(g)]

    key_map = {
        texts["table_token"]: lambda g: g.get("token", ""),
        texts["table_type"]: lambda g: g.get("type", ""),
        texts["table_occurrences"]: lambda g: g.get("total_occurrences", 0),
    }
    filtered.sort(
        key=key_map.get(sort["column"], lambda g: g.get("token", "")),
        reverse=not sort["ascending"],
    )

    PER_PAGE = 50
    total_pages = max(1, (len(filtered) + PER_PAGE - 1) // PER_PAGE)
    page = min(st.session_state["table_page"], total_pages - 1)
    st.session_state["table_page"] = page
    start = page * PER_PAGE
    page_groups = filtered[start : start + PER_PAGE]

    pag_cols = st.columns(3)
    if pag_cols[0].button("⬅️", disabled=page <= 0):
        st.session_state["table_page"] = max(0, page - 1)
        st.rerun()
    pag_cols[1].write(f"Page {page + 1}/{total_pages}")
    if pag_cols[2].button("➡️", disabled=page + 1 >= total_pages):
        st.session_state["table_page"] = min(total_pages - 1, page + 1)
        st.rerun()

    header_cols = st.columns([0.5, 2, 1, 1, 2, 2])
    header_cols[0].markdown(f"**{texts['table_select']}**")
    header_cols[1].markdown(f"**{texts['table_token']}**")
    header_cols[2].markdown(f" **{texts['table_type']}**")
    header_cols[3].markdown(f"**{texts['table_occurrences']}**")
    header_cols[4].markdown(f"**{texts['table_variants']}**")
    header_cols[5].markdown(f"**{texts['table_actions']}**")

    selected = st.session_state["selected_groups"]

    for g in page_groups:
        gid = g.get("id")
        cols = st.columns([0.5, 2, 1, 1, 2, 2])
        checked = cols[0].checkbox("", value=gid in selected, key=f"sel_{gid}")
        if checked and gid not in selected:
            selected.append(gid)
        if not checked and gid in selected:
            selected.remove(gid)

        token_html = f"<span class='token-badge'>{g.get('token')}</span>"
        type_color = ENTITY_COLORS.get(g.get("type"), "#999999")
        type_html = (
            f"<span class='token-badge' style='background-color:{type_color}'>"
            f"{g.get('type')}</span>"
        )
        cols[1].markdown(token_html, unsafe_allow_html=True)
        cols[2].markdown(type_html, unsafe_allow_html=True)
        cols[3].write(g.get("total_occurrences", 0))
        cols[4].write(", ".join(g.get("variants", {}).keys()))

        act_cols = cols[5].columns(3)
        if act_cols[0].button(texts["action_edit"], key=f"edit_{gid}"):
            st.session_state["editing_group"] = gid
        if act_cols[1].button(texts["action_merge"], key=f"merge_{gid}"):
            st.session_state["merge_group"] = gid
        if act_cols[2].button(texts["action_delete"], key=f"del_{gid}"):
            st.session_state["delete_group"] = gid

    st.session_state["selected_groups"] = selected

    if st.session_state.get("editing_group") is not None:
        gid = st.session_state["editing_group"]
        group = next((gr for gr in groups if gr.get("id") == gid), None)
        if group:
            with st.modal(texts["action_edit"]):
                new_token = st.text_input(texts["table_token"], group.get("token", ""))
                new_type = st.text_input(texts["table_type"], group.get("type", ""))
                variants_str = st.text_area(
                    texts["table_variants"],
                    ", ".join(group.get("variants", {}).keys()),
                )
                if st.button("Save", key="save_edit"):
                    group["token"] = new_token
                    group["type"] = new_type
                    group["variants"] = {
                        v.strip(): {"value": v.strip(), "count": 0, "positions": []}
                        for v in variants_str.split(",")
                        if v.strip()
                    }
                    if entity_manager:
                        entity_manager.update_group(
                            gid,
                            {
                                "token": new_token,
                                "type": new_type,
                                "variants": group["variants"],
                            },
                        )
                        for v in group["variants"].keys():
                            entity_manager.update_token_variants(new_token, v)
                    st.session_state["editing_group"] = None
                    st.rerun()
                if st.button(texts["delete_cancel"], key="cancel_edit"):
                    st.session_state["editing_group"] = None
                    st.rerun()

    if st.session_state.get("merge_group") is not None:
        gid = st.session_state["merge_group"]
        source = next((gr for gr in groups if gr.get("id") == gid), None)
        if source:
            with st.modal(texts["action_merge"]):
                target = st.selectbox(
                    "Target",
                    [gr["token"] for gr in groups if gr["id"] != gid],
                )
                if st.button(texts["action_merge"], key="confirm_merge"):
                    if entity_manager:
                        entity_manager.merge_entity_groups(source["token"], target)
                        groups[:] = list(entity_manager.get_grouped_entities().values())
                    st.session_state["merge_group"] = None
                    st.rerun()
                if st.button(texts["delete_cancel"], key="cancel_merge"):
                    st.session_state["merge_group"] = None
                    st.rerun()

    if st.session_state.get("delete_group") is not None:
        gid = st.session_state["delete_group"]
        with st.modal(texts["confirm_delete"]):
            st.write(texts["delete_confirmation_question"])
            dc = st.columns(2)
            if dc[0].button(texts["delete_confirm"], key="confirm_del"):
                if entity_manager:
                    entity_manager.delete_group(gid)
                    groups[:] = list(entity_manager.get_grouped_entities().values())
                else:
                    groups[:] = [g for g in groups if g.get("id") != gid]
                st.session_state["delete_group"] = None
                st.rerun()
            if dc[1].button(texts["delete_cancel"], key="cancel_del"):
                st.session_state["delete_group"] = None
                st.rerun()

    if st.session_state["selected_groups"]:
        bulk = st.columns(3)
        if bulk[0].button(texts["merge_selection"], disabled=len(selected) < 2):
            st.session_state["merge_group"] = selected[0]
        if bulk[1].button(texts["delete_selection"]):
            if entity_manager:
                for gid in list(selected):
                    entity_manager.delete_group(gid)
                groups[:] = list(entity_manager.get_grouped_entities().values())
            else:
                groups[:] = [g for g in groups if g.get("id") not in selected]
            st.session_state["selected_groups"] = []
            st.rerun()
        bulk[2].button(texts["export_selection"], disabled=False)

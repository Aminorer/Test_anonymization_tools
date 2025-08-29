import streamlit as st
import pandas as pd
import re
from typing import Any, Dict, List, Optional

from src.entity_manager import EntityManager
from src.locale import get_locale, LOCALES


TYPE_COLORS = {
    "EMAIL": "#4285F4",
    "PHONE": "#0F9D58",
    "DATE": "#F4B400",
    "PERSON": "#DB4437",
    "ORG": "#AB47BC",
    "IBAN": "#F4511E",
}


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

    type_styles = "\n".join(
        f".type-badge-{t.lower()}{{background:{c};}}" for t, c in TYPE_COLORS.items()
    )
    st.markdown(
        f"""
        <style>
        .group-table {{width:100%;}}
        .token-badge{{padding:2px 6px;border-radius:4px;color:#fff;background:#333;}}
        .type-badge {{ padding:2px 6px; border-radius:10px; color:#fff; }}
        {type_styles}
        .action-button button{{margin-right:4px;}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("group_filters", {"query": "", "types": []})
    st.session_state.setdefault(
        "table_sort", {"column": texts["table_token"], "ascending": True}
    )
    st.session_state.setdefault("table_page", 0)

    filters = st.session_state["group_filters"]
    filters["query"] = st.text_input(texts["search_group"], filters.get("query", ""))
    type_options = sorted({g.get("type", "") for g in groups if g.get("type")})
    if not filters.get("types"):
        filters["types"] = type_options
    filters["types"] = st.multiselect(
        texts["table_type"], type_options, default=filters["types"]
    )
    st.session_state["group_filters"] = filters

    sort = st.session_state["table_sort"]
    sort_cols = [texts["table_token"], texts["table_type"], texts["table_occurrences"]]
    sort["column"] = st.selectbox("Sort", sort_cols, index=sort_cols.index(sort["column"]))
    sort["ascending"] = st.radio("Order", ["asc", "desc"], index=0 if sort["ascending"] else 1) == "asc"
    st.session_state["table_sort"] = sort

    cache_decorator = getattr(st, "cache_data", lambda fn: fn)

    @cache_decorator
    def _filter_and_paginate(
        groups: List[Dict[str, Any]],
        filters: Dict[str, Any],
        sort: Dict[str, Any],
        page: int,
        texts: Dict[str, str],
    ) -> Any:
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

        per_page = 50
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        start = page * per_page
        page_groups = filtered[start : start + per_page]
        return filtered, page_groups, total_pages, page

    filtered, page_groups, total_pages, page = _filter_and_paginate(
        groups, filters, sort, st.session_state["table_page"], texts
    )
    st.session_state["table_page"] = page

    pag_cols = st.columns(3)
    if pag_cols[0].button("⬅️", disabled=page <= 0):
        st.session_state["table_page"] = max(0, page - 1)
    pag_cols[1].write(f"Page {page + 1}/{total_pages}")
    if pag_cols[2].button("➡️", disabled=page + 1 >= total_pages):
        st.session_state["table_page"] = min(total_pages - 1, page + 1)

    df = pd.DataFrame(
        [
            {
                "id": g.get("id"),
                texts["table_token"]: g.get("token"),
                texts["table_type"]: g.get("type", ""),
                texts["table_occurrences"]: g.get("total_occurrences", 0),
                texts["table_variants"]: ", ".join(
                    f"[{v}]" for v in g.get("variants", {})
                ),
                texts["action_edit"]: False,
                texts["action_merge"]: False,
                texts["action_delete"]: False,
            }
            for g in page_groups
        ]
    )

    with st.form("group_delete_form"):
        edited_df = st.data_editor(
            df,
            key="group_table_editor",
            hide_index=True,
            column_config={
                texts["action_edit"]: st.column_config.CheckboxColumn(required=False),
                texts["action_merge"]: st.column_config.CheckboxColumn(required=False),
                texts["action_delete"]: st.column_config.CheckboxColumn(required=False),
                texts["table_type"]: st.column_config.TextColumn(),
                "id": None,
            },
            disabled=[
                texts["table_token"],
                texts["table_type"],
                texts["table_occurrences"],
                texts["table_variants"],
            ],
        )
        selected_ids = edited_df.loc[edited_df[texts["action_delete"]], "id"].tolist()
        submitted = st.form_submit_button(
            "Valider suppression", disabled=not selected_ids
        )

    edit_ids = edited_df.loc[edited_df[texts["action_edit"]], "id"]
    if not edit_ids.empty:
        st.session_state["editing_group"] = edit_ids.iloc[-1]

    merge_ids = edited_df.loc[edited_df[texts["action_merge"]], "id"]
    if not merge_ids.empty:
        st.session_state["merge_group"] = merge_ids.iloc[-1]

    if submitted and selected_ids:
        ids_to_delete = selected_ids
        if entity_manager:
            for gid in ids_to_delete:
                entity_manager.delete_group_by_token(gid)
            groups[:] = list(entity_manager.get_grouped_entities().values())
        else:
            groups[:] = [g for g in groups if g.get("id") not in ids_to_delete]
        st.rerun()

    if st.session_state.get("editing_group") is not None:
        gid = st.session_state["editing_group"]
        group = next((gr for gr in groups if gr.get("id") == gid), None)
        if group:
            modal_ctx = st.modal if hasattr(st, "modal") else st.expander
            with modal_ctx(texts["action_edit"]):
                new_token = st.text_input(texts["table_token"], group.get("token", ""))
                new_type = st.text_input(texts["table_type"], group.get("type", ""))
                variants_str = st.text_area(
                    texts["table_variants"],
                    ", ".join(f"[{v}]" for v in group.get("variants", {})),
                )
                if st.button("Save", key="save_edit"):
                    group["token"] = new_token
                    group["type"] = new_type
                    variants = re.findall(r"\[(.*?)\]", variants_str)
                    group["variants"] = {
                        v.strip(): {"value": v.strip(), "count": 0, "positions": []}
                        for v in variants
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
                if st.button(texts["delete_cancel"], key="cancel_edit"):
                    st.session_state["editing_group"] = None

    if st.session_state.get("merge_group") is not None:
        gid = st.session_state["merge_group"]
        source = next((gr for gr in groups if gr.get("id") == gid), None)
        if source:
            modal_ctx = st.modal if hasattr(st, "modal") else st.expander
            with modal_ctx(texts["action_merge"]):
                options = [gr["token"] for gr in groups if gr["id"] != gid]
                token_to_variants = {
                    gr["token"]: ", ".join(gr.get("variants", {}).keys())
                    for gr in groups
                }
                targets = st.multiselect(
                    "Targets",
                    options,
                    format_func=lambda t: token_to_variants.get(t, t),
                )
                st.write(
                    "Variantes du groupe source : "
                    + ", ".join(source.get("variants", {}).keys())
                )
                choice = st.radio(
                    "Token à conserver",
                    ["source", "target", "custom"],
                    format_func=lambda x: {
                        "source": "Conserver le token du groupe source",
                        "target": "Conserver le token du groupe cible",
                        "custom": "Créer un nouveau token",
                    }[x],
                    key="merge_choice",
                )
                new_token = ""
                if choice == "custom":
                    new_token = st.text_input("Nouveau token", key="new_token")
                if st.button(texts["action_merge"], key="confirm_merge") and targets:
                    if entity_manager:
                        if choice == "target":
                            final_token = targets[0]
                            entity_manager.merge_entity_groups(source["token"], final_token)
                            for tgt in targets[1:]:
                                entity_manager.merge_entity_groups(tgt, final_token)
                        elif choice == "source":
                            for tgt in targets:
                                entity_manager.merge_entity_groups(tgt, source["token"])
                        else:
                            final = new_token or source["token"]
                            entity_manager.merge_entity_groups(source["token"], final)
                            for tgt in targets:
                                entity_manager.merge_entity_groups(tgt, final)
                        groups[:] = list(entity_manager.get_grouped_entities().values())
                    st.session_state["merge_group"] = None
                if st.button(texts["delete_cancel"], key="cancel_merge"):
                    st.session_state["merge_group"] = None


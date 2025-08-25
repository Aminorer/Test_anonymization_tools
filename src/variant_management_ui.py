import streamlit as st
from collections import OrderedDict
from typing import List, Dict, Tuple, Any


def get_page_distribution(
    entity_positions: List[Tuple[int, int]],
    total_pages: int | None = None,
    chunk: int = 5,
) -> Dict[str, int]:
    """Calcule la répartition des occurrences par tranches de pages."""

    pages = []
    for pos in entity_positions:
        page = pos[0] if isinstance(pos, (list, tuple)) else pos
        pages.append(page)

    max_page = total_pages or (max(pages) if pages else 0)
    dist: Dict[str, int] = OrderedDict()

    for page in pages:
        start = ((page - 1) // chunk) * chunk + 1
        end = min(start + chunk - 1, max_page)
        label = f"Pages {start}-{end}"
        dist[label] = dist.get(label, 0) + 1

    return dist


class VariantManager:
    """Gestion simple des groupes d'entités et de leurs variantes."""

    def __init__(self, groups: List[Dict[str, Any]]) -> None:
        self.groups = {g["id"]: g for g in groups}

    def exclude_variant(self, group_id: int, variant_value: str) -> None:
        group = self.groups[group_id]
        group["variants"] = [v for v in group["variants"] if v["value"] != variant_value]

    def modify_variant(self, group_id: int, old_value: str, new_value: str) -> None:
        group = self.groups[group_id]
        for v in group["variants"]:
            if v["value"] == old_value:
                v["value"] = new_value
                break

    def create_new_group_from_variants(
        self, selected_variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        new_id = max(self.groups) + 1 if self.groups else 1
        new_group = {
            "id": new_id,
            "token": f"PERSON_{new_id}",
            "representative_value": selected_variants[0]["value"],
            "variants": selected_variants,
            "total_occurrences": sum(v["count"] for v in selected_variants),
            "positions": [p for v in selected_variants for p in v["positions"]],
        }
        self.groups[new_id] = new_group
        return new_group

    def get_variant_contexts(
        self, variant_value: str, max_contexts: int = 3
    ) -> List[str]:
        return [f"... {variant_value} ..."] * max_contexts


def remove_titles(text: str) -> str:
    titles = {"monsieur", "madame", "docteur"}
    return " ".join([w for w in text.split() if w.lower() not in titles])


def get_smart_suggestion(variant: Dict[str, Any]) -> Dict[str, str] | None:
    suggestions: List[Dict[str, str]] = []

    if len(variant["value"].split()) > 2:
        words = variant["value"].split()
        if words[0].lower() in {"débouter", "contacter", "rencontrer"}:
            suggestions.append(
                {
                    "action": f'Garder seulement "{words[0]}"',
                    "new_value": words[0],
                    "reason": "Éviter de capturer le contexte",
                }
            )

    if any(t in variant["value"].lower() for t in ["monsieur", "madame", "docteur"]):
        without_title = remove_titles(variant["value"])
        if without_title != variant["value"]:
            suggestions.append(
                {
                    "action": f'Enlever le titre → "{without_title}"',
                    "new_value": without_title,
                    "reason": "Séparer titre et nom",
                }
            )

    return suggestions[0] if suggestions else None


def display_variant_editor(
    group_id: int, variant_index: int, variant: Dict[str, Any], manager: VariantManager
) -> None:
    key = f"editing_{group_id}_{variant_index}"
    if st.session_state.get(key):
        st.write("✏️ Modification de variante :")
        new_value = st.text_input(
            "Nouvelle valeur :",
            value=variant["value"],
            key=f"edit_input_{group_id}_{variant_index}",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmer", key=f"conf_{group_id}_{variant_index}"):
                manager.modify_variant(group_id, variant["value"], new_value)
                st.session_state[key] = False
                st.rerun()
        with col2:
            if st.button("❌ Annuler", key=f"cancel_{group_id}_{variant_index}"):
                st.session_state[key] = False
                st.rerun()


def display_variant_management(group: Dict[str, Any], manager: VariantManager) -> None:
    st.subheader(f"📋 Gestion - {group['token']} ({group['total_occurrences']} occurrences)")

    selected_variants: List[Dict[str, Any]] = []
    for i, variant in enumerate(group["variants"]):
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])

        with col1:
            checked = st.checkbox(
                "", value=variant.get("included", True), key=f"select_{group['id']}_{i}"
            )
            if checked:
                selected_variants.append(variant)

        with col2:
            st.write(f"**{variant['value']}** ({variant['count']} occurrences)")
            var_dist = get_page_distribution(variant["positions"])
            dist_text = " | ".join(
                [f"{pages}: {count}" for pages, count in var_dist.items()]
            )
            st.caption(f"📊 {dist_text}")

        with col3:
            if st.button("✏️ Modifier", key=f"edit_{group['id']}_{i}"):
                st.session_state[f"editing_{group['id']}_{i}"] = True
            if st.button("🔍 Contextes", key=f"context_{group['id']}_{i}"):
                ctx = manager.get_variant_contexts(variant["value"])
                with st.expander("Contextes"):
                    for c in ctx:
                        st.write(c)

        with col4:
            if st.button("🗑️ Exclure", key=f"exclude_{group['id']}_{i}"):
                manager.exclude_variant(group["id"], variant["value"])
                st.rerun()
            suggestion = get_smart_suggestion(variant)
            if suggestion and st.button(
                f"💡 {suggestion['action']}", key=f"suggest_{group['id']}_{i}"
            ):
                manager.modify_variant(
                    group["id"], variant["value"], suggestion["new_value"]
                )
                st.rerun()

        display_variant_editor(group["id"], i, variant, manager)

    if selected_variants:
        st.write("---")
        st.write(f"💡 Actions sur {len(selected_variants)} variante(s) sélectionnée(s):")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📝 Nouveau groupe", key=f"new_group_{group['id']}"):
                manager.create_new_group_from_variants(selected_variants)
                st.rerun()

        with col2:
            target = st.selectbox(
                "🔗 Fusionner avec",
                [g["token"] for g in manager.groups.values() if g["id"] != group["id"]],
                key=f"merge_{group['id']}",
            )
            if st.button("Fusionner"):
                target_id = [
                    g["id"] for g in manager.groups.values() if g["token"] == target
                ][0]
                manager.groups[target_id]["variants"].extend(selected_variants)
                st.rerun()

        with col3:
            if st.button("🗑️ Supprimer sélection", key=f"del_sel_{group['id']}"):
                for v in selected_variants:
                    manager.exclude_variant(group["id"], v["value"])
                st.rerun()


def display_entity_group_compact(group: Dict[str, Any]) -> None:
    col1, col2, col3 = st.columns([2, 3, 2])

    with col1:
        st.write(f"**{group['token']}**: {group['representative_value']}")
        st.caption(f"{group['total_occurrences']} occurrences, {len(group['variants'])} variantes")

    with col2:
        page_dist = get_page_distribution(group["positions"])
        dist_text = " | ".join(
            [f"{pages}: {count} occ." for pages, count in page_dist.items()]
        )
        st.write(f"📊 {dist_text}")

    with col3:
        if st.button("📋 Gérer", key=f"manage_{group['id']}"):
            st.session_state[f"show_details_{group['id']}"] = True
        if st.button("🗑️", key=f"delete_{group['id']}"):
            st.session_state["delete_group"] = group["id"]

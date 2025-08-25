import streamlit as st
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Tuple


def get_page_distribution(
    positions: Iterable[Tuple[int, int]] | Iterable[int],
    total_pages: int | None = None,
    chunk: int = 5,
) -> Dict[str, int]:
    """Return the distribution of occurrences by ranges of ``chunk`` pages.

    Parameters
    ----------
    positions:
        Iterable containing either page numbers or (page, position) tuples.
    total_pages:
        Maximum page number to consider. If ``None`` it is inferred from
        ``positions``.
    chunk:
        Size of each page range.
    """
    pages: List[int] = []
    for pos in positions:
        if isinstance(pos, (list, tuple)):
            pages.append(int(pos[0]))
        else:
            pages.append(int(pos))

    max_page = total_pages or (max(pages) if pages else 0)
    distribution: Dict[str, int] = OrderedDict()
    for page in pages:
        start = ((page - 1) // chunk) * chunk + 1
        end = min(start + chunk - 1, max_page)
        label = f"Pages {start}-{end}"
        distribution[label] = distribution.get(label, 0) + 1
    return distribution


class VariantManager:
    """Simple manager for groups of entity variants."""

    def __init__(self, groups: List[Dict[str, Any]]) -> None:
        # Store groups in a dictionary for quick access by id
        self.groups: Dict[int, Dict[str, Any]] = {g["id"]: g for g in groups}

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    def add_variant(
        self, group_id: int, value: str, positions: List[Tuple[int, int]] | None = None
    ) -> None:
        """Add a new variant to a group."""
        group = self.groups[group_id]
        positions = positions or []
        variant = {"value": value, "count": len(positions), "positions": positions}
        group.setdefault("variants", []).append(variant)
        group.setdefault("positions", []).extend(positions)
        group["total_occurrences"] = group.get("total_occurrences", 0) + variant["count"]

    def update_variant(self, group_id: int, old_value: str, new_value: str) -> None:
        """Modify the value of a variant."""
        group = self.groups[group_id]
        for variant in group.get("variants", []):
            if variant["value"] == old_value:
                variant["value"] = new_value
                break

    def exclude_variant(self, group_id: int, variant_value: str) -> None:
        """Remove a variant from a group."""
        group = self.groups[group_id]
        for variant in list(group.get("variants", [])):
            if variant["value"] == variant_value:
                group["total_occurrences"] -= variant.get("count", 0)
                for pos in variant.get("positions", []):
                    if pos in group.get("positions", []):
                        group["positions"].remove(pos)
                group["variants"].remove(variant)
                break

    def merge_variants(
        self, source_group_id: int, target_group_id: int, variant_values: List[str]
    ) -> None:
        """Merge selected variants from one group into another."""
        if source_group_id == target_group_id:
            return
        source = self.groups[source_group_id]
        target = self.groups[target_group_id]
        to_move = [
            v for v in source.get("variants", []) if v["value"] in variant_values
        ]
        if not to_move:
            return

        for variant in to_move:
            target.setdefault("variants", []).append(variant)
            target.setdefault("positions", []).extend(variant.get("positions", []))
            target["total_occurrences"] = target.get("total_occurrences", 0) + variant.get(
                "count", 0
            )

        source["variants"] = [
            v for v in source.get("variants", []) if v["value"] not in variant_values
        ]
        source["positions"] = [
            p for v in source.get("variants", []) for p in v.get("positions", [])
        ]
        source["total_occurrences"] = sum(
            v.get("count", 0) for v in source.get("variants", [])
        )

    def delete_group(self, group_id: int) -> None:
        """Delete an entire group."""
        self.groups.pop(group_id, None)


# ----------------------------------------------------------------------
# UI helpers
# ----------------------------------------------------------------------

def _suggest_short_form(value: str) -> Dict[str, str] | None:
    """Return a simple suggestion for a variant if applicable."""
    titles = {"monsieur", "madame", "docteur"}
    words = value.split()
    if words and words[0].lower() in titles:
        without = " ".join(words[1:])
        return {"action": f'Enlever le titre → "{without}"', "new_value": without}
    return None


def display_entity_group_compact(group: Dict[str, Any]) -> None:
    """Compact summary of a group with basic actions."""
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.write(f"**{group['token']}**: {group.get('representative_value', '')}")
        st.caption(
            f"{group.get('total_occurrences', 0)} occurrences, {len(group.get('variants', []))} variantes"
        )
    with col2:
        dist = get_page_distribution(group.get("positions", []))
        dist_text = " | ".join([f"{k}: {v}" for k, v in dist.items()])
        if dist_text:
            st.write(f"📊 {dist_text}")
    with col3:
        if st.button("📋 Gérer", key=f"manage_{group['id']}"):
            st.session_state[f"show_details_{group['id']}"] = True
        if st.button("🗑️", key=f"delete_{group['id']}"):
            st.session_state["delete_group"] = group["id"]


def display_variant_management(group: Dict[str, Any], manager: VariantManager) -> None:
    """Detailed interface to manage variants within a group."""
    st.subheader(
        f"📋 Gestion - {group['token']} ({group.get('total_occurrences', 0)} occurrences)"
    )

    selected: List[Dict[str, Any]] = []
    for idx, variant in enumerate(group.get("variants", [])):
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
        with col1:
            if st.checkbox("", value=True, key=f"sel_{group['id']}_{idx}"):
                selected.append(variant)
        with col2:
            st.write(f"**{variant['value']}** ({variant.get('count', 0)} occ.)")
            var_dist = get_page_distribution(variant.get("positions", []))
            dist_text = " | ".join([f"{k}: {v}" for k, v in var_dist.items()])
            if dist_text:
                st.caption(f"📊 {dist_text}")
        with col3:
            btn_key = f"edit_btn_{group['id']}_{idx}"
            state_key = f"edit_{group['id']}_{idx}"
            st.session_state.setdefault(state_key, False)
            if st.button("✏️ Modifier", key=btn_key):
                st.session_state[state_key] = True
            if st.session_state.get(state_key):
                new_val = st.text_input(
                    "Nouvelle valeur", value=variant["value"], key=f"inp_{group['id']}_{idx}"
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅", key=f"save_{group['id']}_{idx}"):
                        manager.update_variant(group["id"], variant["value"], new_val)
                        st.session_state[state_key] = False
                        st.experimental_rerun()
                with c2:
                    if st.button("❌", key=f"cancel_{group['id']}_{idx}"):
                        st.session_state[state_key] = False
                        st.experimental_rerun()
            if st.button("🔍 Contextes", key=f"ctx_{group['id']}_{idx}"):
                with st.expander("Contextes"):
                    st.write(f"... {variant['value']} ...")
        with col4:
            if st.button("🗑️ Exclure", key=f"ex_{group['id']}_{idx}"):
                manager.exclude_variant(group["id"], variant["value"])
                st.experimental_rerun()
            suggestion = _suggest_short_form(variant["value"])
            if suggestion and st.button(
                f"💡 {suggestion['action']}", key=f"sugg_{group['id']}_{idx}"
            ):
                manager.update_variant(group["id"], variant["value"], suggestion["new_value"])
                st.experimental_rerun()

    if selected:
        st.write("---")
        st.write(f"💡 Actions sur {len(selected)} variante(s) sélectionnée(s) :")
        col1, col2 = st.columns(2)
        with col1:
            target = st.selectbox(
                "🔗 Fusionner avec",
                [g["token"] for g in manager.groups.values() if g["id"] != group["id"]],
                key=f"merge_sel_{group['id']}"
            )
            if st.button("Fusionner", key=f"merge_btn_{group['id']}"):
                target_id = [
                    g_id for g_id, g in manager.groups.items() if g["token"] == target
                ][0]
                manager.merge_variants(
                    group["id"], target_id, [v["value"] for v in selected]
                )
                st.experimental_rerun()
        with col2:
            if st.button("🗑️ Supprimer sélection", key=f"del_sel_{group['id']}"):
                for v in selected:
                    manager.exclude_variant(group["id"], v["value"])
                st.experimental_rerun()

    st.write("---")
    new_variant = st.text_input("Ajouter une variante", key=f"new_var_{group['id']}")
    if st.button("Ajouter", key=f"add_var_{group['id']}") and new_variant:
        manager.add_variant(group["id"], new_variant, [])
        st.experimental_rerun()

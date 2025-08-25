"""Utility functions for managing group-related UI state.

These helpers encapsulate the core logic for filtering groups and handling
selection or deletion actions so that it can be tested independently from the
Streamlit interface.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    from .variant_manager_ui import VariantManager


def filter_groups(groups: Dict[int, Dict[str, Any]], search_term: str) -> Dict[int, Dict[str, Any]]:
    """Return a subset of ``groups`` whose token contains ``search_term``.

    Parameters
    ----------
    groups:
        Mapping of group identifiers to group dictionaries.
    search_term:
        Term used to filter groups by their ``token`` field. The comparison is
        case-insensitive.
    """
    term = search_term.lower()
    return {gid: g for gid, g in groups.items() if term in g.get("token", "").lower()}


def mark_groups_for_management(session_state: Dict[str, Any], group_ids: Iterable[int]) -> None:
    """Mark ``group_ids`` to display their management interface.

    This updates ``session_state`` so that the details for the given groups are
    shown and any existing selection checkboxes are cleared.
    """
    for gid in group_ids:
        gid_str = str(gid)
        session_state[f"show_details_{gid_str}"] = True
        session_state[f"manage_{gid_str}"] = False
        session_state[f"delete_{gid_str}"] = False


def delete_groups(
    manager: "VariantManager",
    groups: List[Dict[str, Any]],
    session_state: Dict[str, Any],
    group_ids: Iterable[int],
) -> None:
    """Remove groups identified by ``group_ids`` from the manager.

    The provided ``groups`` list is updated in-place to reflect the current
    state of ``manager``. Related keys are removed from ``session_state``.
    """
    for gid in group_ids:
        gid_str = str(gid)
        manager.groups.pop(gid, None)
        session_state.pop(f"manage_{gid_str}", None)
        session_state.pop(f"delete_{gid_str}", None)
        session_state.pop(f"show_details_{gid_str}", None)
    groups[:] = list(manager.groups.values())

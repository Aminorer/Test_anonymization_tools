"""Simple localisation utilities for the Streamlit UI.

This module exposes a :data:`LOCALES` mapping containing translations for the
keys used throughout the minimal Streamlit interface. Only the strings needed
by ``display_legal_entity_manager`` are included, but the structure allows for
easy extension.
"""

from typing import Dict


LOCALES: Dict[str, Dict[str, str]] = {
    "en": {
        "language_name": "English",
        "language_label": "Language",
        "lang_en": "English",
        "lang_fr": "French",
        "entity_manager_header": "\U0001f4c3 Entity Manager",
        "delete_success": "Group deleted",
        "search_group": "Search group",
        "table_token": "Token",
        "table_type": "Type",
        "table_occurrences": "Occurrences",
        "table_variants": "Values to anonymize",
        "table_actions": "Actions",
        "action_edit": "Edit",
        "action_merge": "Merge",
        "action_delete": "Delete",
        "confirm_delete": "Confirm deletion",
        "delete_confirmation_question": "Are you sure you want to delete the selected groups?",
        "delete_confirm": "Delete",
        "delete_cancel": "Cancel",
        "back": "\u2b05\ufe0f Back",
    },
    "fr": {
        "language_name": "Français",
        "language_label": "Langue",
        "lang_en": "Anglais",
        "lang_fr": "Français",
        "entity_manager_header": "\U0001f4c3 Gestionnaire d'entités",
        "delete_success": "Groupe supprimé",
        "search_group": "Rechercher un groupe",
        "table_token": "Token",
        "table_type": "Type",
        "table_occurrences": "Occurrences",
        "table_variants": "Valeurs à anonymiser",
        "table_actions": "Actions",
        "action_edit": "Modifier",
        "action_merge": "Fusionner",
        "action_delete": "Supprimer",
        "confirm_delete": "Confirmer la suppression",
        "delete_confirmation_question": "Êtes-vous sûr de vouloir supprimer les groupes sélectionnés ?",
        "delete_confirm": "Supprimer",
        "delete_cancel": "Annuler",
        "back": "\u2b05\ufe0f Retour",
    },
}


def get_locale(lang: str) -> Dict[str, str]:
    """Return the translation mapping for ``lang``.

    Parameters
    ----------
    lang:
        Two letter language code such as ``"en"`` or ``"fr"``.

    Returns
    -------
    dict
        The translation dictionary for the requested language, defaulting to
        English if the language code is unknown.
    """

    return LOCALES.get(lang, LOCALES["en"])


"""
Internationalization module - Provides localized strings for the application

This module loads the appropriate language file based on configuration
and provides string access functions.
"""

from typing import Dict, Any, Optional


_current_language = "en"
_strings: Dict[str, Dict[str, Any]] = {}


def load_language(language_code: str = "en") -> bool:
    """Load strings for the specified language

    Args:
        language_code: Language code (e.g. 'en', 'fr')

    Returns:
        True if successful, False otherwise
    """
    global _current_language, _strings

    try:
        if language_code == "en":
            from i18n.en import GENERAL, HUNTING, FISHING, BALLS, LOG, STATS

            _strings = {
                "GENERAL": GENERAL,
                "HUNTING": HUNTING,
                "FISHING": FISHING,
                "BALLS": BALLS,
                "LOG": LOG,
                "STATS": STATS,
            }
        else:

            return load_language("en")

        _current_language = language_code
        return True

    except ImportError:

        if language_code != "en":
            return load_language("en")
        return False


def get_string(category: str, key: str, default: Optional[str] = None) -> str:
    """Get a localized string

    Args:
        category: String category (e.g. 'GENERAL', 'HUNTING')
        key: String key within the category
        default: Default value if string not found

    Returns:
        Localized string or default value
    """

    if not _strings:
        load_language()

    try:
        return _strings[category][key]
    except KeyError:
        if default is not None:
            return default
        return f"[{category}.{key}]"


load_language()

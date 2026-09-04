"""bible_translation_finder: download Bible translations as OpenSong XML.

This package helps people fetch full Bible translations and save them as
OpenSong-format XML files that can be loaded by presentation software
like OpenSong, FreeShow, and similar lyrics-display tools.

Quick start::

    import btf

    # List available translations
    btf.list_translations()

    # Download one translation to a directory
    btf.download("KJV", output_dir="./bibles")

    # Or many at once
    btf.batch(["KJV", "WEB", "LSG", "KOUGO"], output_dir="./bibles")

    # Or just get the XML string in memory (no disk write)
    xml = btf.fetch_xml("KJV")
"""

from .catalog import (
    get_by_abbreviation,
    get_catalog,
    get_copyrighted,
    get_freely_available,
    get_translation,
    list_languages,
    search_catalog,
)
from .cli import run_cli
from .converter import BIBLE_BOOKS, convert_to_opensong
from .library import Library, batch, default_data_dir, download, fetch_xml

__all__ = [
    "BIBLE_BOOKS",
    "Library",
    "default_data_dir",
    "download",
    "batch",
    "fetch_xml",
    "list_translations",
    "find_translations",
    "list_languages",
    "get_catalog",
    "get_translation",
    "get_by_abbreviation",
    "get_freely_available",
    "get_copyrighted",
    "search_catalog",
    "convert_to_opensong",
    "run_cli",
]

__version__ = "0.3.0"


def list_translations(include_copyrighted: bool = True):
    """List catalog entries, most popular first."""
    return get_catalog() if include_copyrighted else get_freely_available()


def find_translations(query: str = "", language: str = ""):
    """Offline catalog search by name/abbreviation/language (no download)."""
    return search_catalog(query=query, language=language)

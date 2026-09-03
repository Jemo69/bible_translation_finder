"""bible-translation-maker: find and read Bible verses in Python.

Library usage (for API servers, GUIs, TUIs)::

    import btm

    # One-shot lookups (downloads KJV on first use, then caches it)
    print(btm.get_verse("John 3:16").text)
    print(btm.get_passage("Ps 23:1-3", translation="WEB").text)
    for hit in btm.find("everlasting", translation="KJV", limit=5):
        print(hit.reference, "-", hit.text)

    # Browse the catalog (90 translations, 30+ languages — offline)
    for t in btm.find_translations("japanese"):
        print(t["abbreviation"], t["name"])

    # Hold a translation open for repeated queries
    bible = btm.load("KOUGO")          # Japanese Colloquial Version
    print(bible.get_verse("John", 3, 16).text)

The ``btm`` command-line tool keeps the original download workflow::

    btm list
    btm get "John 3:16" --translation KJV
    btm download KJV
"""

from .bible import Bible, Passage, Verse
from .catalog import (
    get_by_abbreviation,
    get_catalog,
    get_copyrighted,
    get_freely_available,
    get_translation,
    list_languages,
    search_catalog,
)
from .converter import BIBLE_BOOKS
from .library import Library, default_data_dir, get_library
from .reference import Reference, normalize_book_name, parse_reference

__all__ = [
    "Bible",
    "Passage",
    "Verse",
    "Reference",
    "Library",
    "get_library",
    "default_data_dir",
    "get_verse",
    "get_passage",
    "get_chapter",
    "find",
    "search",
    "load",
    "list_translations",
    "find_translations",
    "get_catalog",
    "get_translation",
    "get_by_abbreviation",
    "get_freely_available",
    "get_copyrighted",
    "list_languages",
    "search_catalog",
    "normalize_book_name",
    "parse_reference",
    "BIBLE_BOOKS",
]

__version__ = "0.2.0"


def load(translation: str = "KJV", data_dir=None) -> Bible:
    """Load a translation for repeated queries (downloads on first use)."""
    return get_library(data_dir).load(translation)


def get_verse(reference: str, translation: str = "KJV", data_dir=None) -> Verse:
    """Look up verses by reference, e.g. ``get_verse("John 3:16-17")``.

    A reference with a verse range returns the *first* verse of the range;
    use :func:`get_passage` for the whole range.
    """
    bible = get_library(data_dir).load(translation)
    ref = parse_reference(reference)
    if ref.chapter is None:
        raise ValueError(
            f"{reference!r} names a whole book; use get_passage() instead."
        )
    if ref.verse_start is None:
        raise ValueError(
            f"{reference!r} names a whole chapter; use get_chapter() or get_passage()."
        )
    assert ref.chapter is not None and ref.verse_start is not None
    return bible.get_verse(ref.book, ref.chapter, ref.verse_start)


def get_passage(reference: str, translation: str = "KJV", data_dir=None) -> Passage:
    """Return every verse for ``reference`` ('John 3:16-18', 'Ps 23', ...)."""
    return get_library(data_dir).load(translation).get_passage(reference)


def get_chapter(book: str, chapter: int, translation: str = "KJV", data_dir=None) -> Passage:
    """Return every verse in ``book``/``chapter``."""
    return get_library(data_dir).load(translation).get_chapter(book, chapter)


def find(query: str, translation: str = "KJV", limit: int = 50, data_dir=None):
    """Full-text search for ``query`` within one translation."""
    return get_library(data_dir).load(translation).search(query, limit=limit)


# Alias — ``btm.search(...)`` reads naturally too.
search = find


def list_translations(include_copyrighted: bool = True, data_dir=None):
    """List catalog entries, most popular first."""
    return get_library(data_dir).list_translations(include_copyrighted)


def find_translations(query: str = "", language: str = ""):
    """Offline catalog search by name/abbreviation/language (no download)."""
    return search_catalog(query=query, language=language)

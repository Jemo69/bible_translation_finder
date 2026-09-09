"""bible_translation_finder: find, read, and download Bible translations as OpenSong XML.

This package provides both a high-level Scripture lookup/search API and
tools to fetch full translations as OpenSong-format XML files compatible
with FreeShow, OpenSong, and other lyrics-display presentation software.

Quick start::

    import btm  # or import btf

    # Lookup verses & passages
    print(btm.get_verse("John 3:16").text)
    print(btm.get_passage("Ps 23:1-3", translation="WEB").text)

    # Search scripture text
    for hit in btm.find("everlasting", translation="KJV", limit=5):
        print(hit.reference, "-", hit.text)

    # Download translations as OpenSong XML
    btm.download("KJV", output_dir="./bibles")
    btm.batch(["KJV", "WEB", "LSG"], output_dir="./bibles")

    # In-memory XML string (no disk write)
    xml = btm.fetch_xml("KJV")

    # Work with loaded Bible objects
    bible = btm.load("KOUGO")
    print(bible.get_verse("John", 3, 16).text)
    xml_str = bible.to_opensong_xml()
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
from .cli import format_table, run_cli
from .converter import BIBLE_BOOKS, convert_to_opensong
from .library import (
    Library,
    batch,
    default_data_dir,
    download,
    downloaded,
    fetch_xml,
    file_for,
    get_library,
    is_downloaded,
    scan_local_bibles,
    convert_local_bible,
    search_ebible,
    search_translations,
)
from .reference import Reference, normalize_book_name, parse_reference

search_ebible_catalog = search_ebible

__all__ = [
    "Bible",
    "Passage",
    "Verse",
    "Reference",
    "BIBLE_BOOKS",
    "Library",
    "get_library",
    "default_data_dir",
    "download",
    "batch",
    "fetch_xml",
    "downloaded",
    "is_downloaded",
    "file_for",
    "scan_local_bibles",
    "convert_local_bible",
    "load",
    "load_file",
    "get_verse",
    "get_passage",
    "get_chapter",
    "find",
    "search",
    "list_translations",
    "find_translations",
    "list_languages",
    "get_catalog",
    "get_translation",
    "get_by_abbreviation",
    "get_freely_available",
    "get_copyrighted",
    "search_catalog",
    "search_ebible",
    "search_ebible_catalog",
    "search_translations",
    "normalize_book_name",
    "parse_reference",
    "convert_to_opensong",
    "format_table",
    "run_cli",
]

__version__ = "0.3.1"


def load(translation: str = "KJV", data_dir=None) -> Bible:
    """Load a translation for repeated queries (downloads on first use)."""
    return get_library(data_dir).load(translation)


def load_file(path, translation: str = "") -> Bible:
    """Load an OpenSong Bible XML file directly."""
    return get_library().load_file(path, translation=translation)


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
    if data_dir is not None:
        return get_library(data_dir).list_translations(include_copyrighted)
    return get_catalog() if include_copyrighted else get_freely_available()


def find_translations(query: str = "", language: str = ""):
    """Offline catalog search by name/abbreviation/language (no download)."""
    return search_catalog(query=query, language=language)


"""Local library: download, cache, and convert Bible translations to XML.

Translations are saved as OpenSong XML in a per-library data directory
(``~/.local/share/bible-translation-finder`` by default; override with the
``BTM_DATA_DIR`` environment variable) so the files can be dropped straight
into OpenSong, FreeShow, or any other presentation software that consumes
that format.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

from . import catalog as _catalog
from . import converter as _converter
from . import scraper as _scraper


def _make_stub(t: dict) -> str:
    """Build an OpenSong XML placeholder file for a copyrighted translation.

    Defined here too so :mod:`btm.cli` can import it without a circular dep.
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!--",
        f"  Translation: {t['name']} ({t['abbreviation']})",
        f"  Language: {t['language']}",
        f"  Copyright: {t['copyright']}",
        "",
        "  This is a STUB file. The full Bible text for this translation",
        "  is copyrighted and not freely redistributable.",
        "",
        "  To obtain this Bible translation, please contact the copyright holder",
        f"  or purchase a licensed copy from an authorized retailer.",
        "",
        "  For OpenSong format, you may be able to download from:",
        "  - https://opensong.org/downloads/",
        "  - https://freely-given.org/Software/BibleDropBox/Formats/OpenSongBibles.html",
        "-->",
        "<bible>",
    ]
    for book in _converter.BIBLE_BOOKS:
        lines.append(f'  <b n="{book}">')
        lines.append(f'    <c n="1">')
        lines.append(f'      <v n="1">[Placeholder - {t["abbreviation"]} Bible text not included]</v>')
        lines.append(f'    </c>')
        lines.append(f'  </b>')
    lines.append("</bible>")
    return "\n".join(lines)


def default_data_dir() -> Path:
    env = os.environ.get("BTM_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "bible-translation-finder"


def translation_filename(t: dict) -> str:
    return f"{t['abbreviation'].lower()}_{t['id'].replace('-', '_')}.xml"


def _fetch_opensong_xml(t: dict) -> Optional[str]:
    source_type = t.get("source_type")
    source_url = t.get("source_url")
    source_format = t.get("source_format")
    if source_type == "youversion":
        version_id = t.get("youversion_id")
        books = _scraper.YOUVERSION_BOOKS.get(t.get("youversion_books"))
        if not version_id or not books:
            raise ValueError(f"No YouVersion config for {t['abbreviation']}")
        return _scraper.download_youversion(version_id, books, t["name"])
    if source_type == "open-bibles" and source_url:
        filename = source_url.rstrip("/").split("/")[-1]
        raw = _scraper.download_open_bibles(filename)
    elif source_type == "ebible" and source_url:
        raw = _scraper.download_ebible_usfx(source_url)
    else:
        raise ValueError(f"No download method for {t['abbreviation']}")
    if not raw:
        return None
    return _converter.convert_to_opensong(raw, source_format)


def fetch_xml(translation: str) -> str:
    """Return the OpenSong XML for ``translation`` as a string (no disk write).

    Useful when you want to stream the XML into another pipeline (e.g. load
    it directly into FreeShow's stage-display plugin) without touching the
    filesystem.
    """
    t = _catalog.get_by_abbreviation(translation)
    if t is None:
        raise KeyError(
            f"Unknown translation: {translation!r}. "
            "Use list_translations() or find_translations() to browse what is available."
        )
    if not t["freely_available"]:
        return _make_stub(t)
    xml = _fetch_opensong_xml(t)
    if not xml:
        return _make_stub(t)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml


def download(
    translation: str,
    output_dir: Optional[Union[Path, str]] = None,
    data_dir: Optional[Union[Path, str]] = None,
    overwrite: bool = False,
    progress: bool = True,
) -> Path:
    """Download ``translation`` to an OpenSong XML file and return its path.

    When ``output_dir`` is given, the file is written there. Otherwise the
    library's ``data_dir`` is used (so the translation is available to
    :class:`Library` afterwards).
    """
    t = _catalog.get_by_abbreviation(translation)
    if t is None:
        raise KeyError(
            f"Unknown translation: {translation!r}. "
            "Use list_translations() or find_translations() to browse what is available."
        )
    if data_dir is None:
        data_dir = default_data_dir() if output_dir is None else None
    if data_dir is not None:
        data_dir = Path(data_dir).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        dest = data_dir / translation_filename(t)
    else:
        dest = Path(output_dir).expanduser() / translation_filename(t)
        dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not overwrite:
        return dest

    opensong_xml: Optional[str] = None
    if t["freely_available"]:
        if progress:
            print(f"Downloading {t['name']} ({t['abbreviation']})...")
        opensong_xml = _fetch_opensong_xml(t)
    else:
        if progress:
            print(
                f"Note: {t['abbreviation']} is copyrighted; writing a stub file."
            )

    if opensong_xml:
        content = '<?xml version="1.0" encoding="UTF-8"?>\n' + opensong_xml
    else:
        content = _make_stub(t)
    dest.write_text(content, encoding="utf-8")
    if progress:
        print(f"Wrote: {dest}")
    return dest


def batch(
    translations: Optional[list[str]] = None,
    output_dir: Optional[Union[Path, str]] = None,
    data_dir: Optional[Union[Path, str]] = None,
    overwrite: bool = False,
    progress: bool = True,
) -> list[Path]:
    """Download several translations; returns the list of written file paths.

    When ``translations`` is None or omitted, every freely available translation
    in the curated catalog is downloaded.
    """
    if translations is None:
        translations = [t["abbreviation"] for t in _catalog.get_freely_available()]
    paths: list[Path] = []
    for tid in translations:
        try:
            paths.append(
                download(
                    tid,
                    output_dir=output_dir,
                    data_dir=data_dir,
                    overwrite=overwrite,
                    progress=progress,
                )
            )
        except Exception as e:
            if progress:
                print(f"  Error processing {tid}: {e}")
    return paths


class Library:
    """Manages a local collection of downloaded Bible translation XML files."""

    def __init__(self, data_dir: Optional[Union[Path, str]] = None):
        self.data_dir = Path(data_dir).expanduser() if data_dir else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, object] = {}

    # -- catalog ------------------------------------------------------
    def list_translations(self, include_copyrighted: bool = True) -> list[dict]:
        translations = _catalog.get_catalog()
        if not include_copyrighted:
            translations = [t for t in translations if t["freely_available"]]
        return sorted(translations, key=lambda t: t.get("popularity_rank", 99))

    def find_translations(self, query: str = "", language: str = "") -> list[dict]:
        return _catalog.search_catalog(query=query, language=language)

    def languages(self) -> list[str]:
        return _catalog.list_languages()

    def resolve(self, translation: str) -> dict:
        t = _catalog.get_by_abbreviation(translation)
        if t is None:
            raise KeyError(
                f"Unknown translation: {translation!r}. "
                "Use Library().find_translations() to browse what is available."
            )
        return t

    # -- local files --------------------------------------------------
    def file_for(self, translation: str) -> Path:
        t = self.resolve(translation)
        return self.data_dir / translation_filename(t)

    def is_downloaded(self, translation: str) -> bool:
        try:
            return self.file_for(translation).exists()
        except KeyError:
            return False

    def downloaded(self) -> list[dict]:
        have = []
        for t in _catalog.get_catalog():
            if (self.data_dir / translation_filename(t)).exists():
                have.append(t)
        return sorted(have, key=lambda t: t.get("popularity_rank", 99))

    def path(self, translation: str) -> Path:
        return self.file_for(translation)

    def download(
        self,
        translation: str,
        overwrite: bool = False,
        progress: bool = True,
    ) -> Path:
        """Download ``translation`` to this library's data_dir and return its path."""
        t = self.resolve(translation)
        self._cache.pop(t["id"], None)
        return download(
            translation,
            output_dir=None,
            data_dir=self.data_dir,
            overwrite=overwrite,
            progress=progress,
        )

    # -- loading ------------------------------------------------------
    def load(self, translation: str = "KJV", download: bool = True):
        """Load a translation as a :class:`Bible` (cached in memory).

        Downloads it first unless ``download=False``.
        """
        from .bible import Bible

        t = self.resolve(translation)
        if t["id"] in self._cache:
            return self._cache[t["id"]]
        path = self.data_dir / translation_filename(t)
        if not path.exists():
            if not download:
                raise FileNotFoundError(
                    f"{t['abbreviation']} is not cached at {path}. "
                    f"Call Library().download({t['abbreviation']!r}) first."
                )
            path = self.download(t["abbreviation"])
        bible = Bible.from_file(path, translation=t["abbreviation"], name=t["name"])
        self._cache[t["id"]] = bible
        return bible

    def load_file(self, path: Union[Path, str], translation: str = ""):
        """Load any OpenSong XML file directly (no catalog needed)."""
        from .bible import Bible

        return Bible.from_file(path, translation=translation)

    def batch(
        self,
        translations: Optional[list[str]] = None,
        output_dir: Optional[Union[Path, str]] = None,
        overwrite: bool = False,
        progress: bool = True,
    ) -> list[Path]:
        """Download multiple translations into this library (or output_dir)."""
        return batch(
            translations=translations,
            output_dir=output_dir,
            data_dir=self.data_dir if output_dir is None else None,
            overwrite=overwrite,
            progress=progress,
        )

    def fetch_xml(self, translation: str) -> str:
        """Return the OpenSong XML for ``translation`` as a string."""
        return fetch_xml(translation)

    def get_verse(self, reference: str, translation: str = "KJV"):
        """Look up a single verse in this library."""
        bible = self.load(translation)
        from .reference import parse_reference

        ref = parse_reference(reference)
        if ref.chapter is None:
            raise ValueError(
                f"{reference!r} names a whole book; use get_passage() instead."
            )
        if ref.verse_start is None:
            raise ValueError(
                f"{reference!r} names a whole chapter; use get_chapter() or get_passage()."
            )
        return bible.get_verse(ref.book, ref.chapter, ref.verse_start)

    def get_passage(self, reference: str, translation: str = "KJV"):
        """Return all verses for ``reference`` in this library."""
        return self.load(translation).get_passage(reference)

    def get_chapter(self, book: str, chapter: int, translation: str = "KJV"):
        """Return every verse in ``book``/``chapter`` in this library."""
        return self.load(translation).get_chapter(book, chapter)

    def find(self, query: str, translation: str = "KJV", limit: int = 50):
        """Full-text search for ``query`` in this library."""
        return self.load(translation).search(query, limit=limit)

    search = find

    def search_ebible(self, query: str = "", language: str = "") -> list[dict]:
        """Search the live eBible.org catalog."""
        return _scraper.search_ebible_catalog(query=query, language=language)

    def search_translations(
        self, query: str = "", language: str = "", include_ebible: bool = False
    ) -> list[dict]:
        """Search translations across local catalog and optionally eBible.org."""
        local = self.find_translations(query=query, language=language)
        if not include_ebible:
            return local
        try:
            ebible_results = self.search_ebible(query=query, language=language)
        except Exception:
            ebible_results = []
        return local + ebible_results

    def clear_cache(self) -> None:
        self._cache.clear()


# Shared default library for top-level convenience functions.
_default_library: Optional[Library] = None


def get_library(data_dir: Optional[Union[Path, str]] = None) -> Library:
    global _default_library
    if data_dir is not None:
        return Library(data_dir)
    if _default_library is None:
        _default_library = Library()
    return _default_library


def downloaded(data_dir: Optional[Union[Path, str]] = None) -> list[dict]:
    """Catalog entries that have a cached XML file in the data directory."""
    return get_library(data_dir).downloaded()


def is_downloaded(
    translation: str, data_dir: Optional[Union[Path, str]] = None
) -> bool:
    """Return True if ``translation`` is already cached locally."""
    return get_library(data_dir).is_downloaded(translation)


def file_for(
    translation: str, data_dir: Optional[Union[Path, str]] = None
) -> Path:
    """Return the cached OpenSong XML Path for ``translation``."""
    return get_library(data_dir).file_for(translation)


def search_ebible(query: str = "", language: str = "") -> list[dict]:
    """Search the online eBible.org catalog (1,500+ translations)."""
    return _scraper.search_ebible_catalog(query=query, language=language)


def search_translations(
    query: str = "", language: str = "", include_ebible: bool = False
) -> list[dict]:
    """Search translations across curated local catalog and optionally eBible.org."""
    return get_library().search_translations(
        query=query, language=language, include_ebible=include_ebible
    )



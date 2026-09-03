"""Local library: download, cache, and load Bible translations.

A :class:`Library` keeps downloaded OpenSong XML files in a data directory
(``~/.local/share/bible-translation-finder`` by default, overridable with the
``BTM_DATA_DIR`` environment variable or an explicit path) and loads them as
:class:`btm.bible.Bible` objects with an in-memory cache, so API servers,
GUIs, and TUIs can share one simple interface::

    from btm.library import Library
    lib = Library()
    bible = lib.load("KJV")          # downloads on first use, then caches
    print(bible.get_passage("John 3:16").text)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from . import catalog as _catalog
from . import converter as _converter
from . import scraper as _scraper
from .bible import Bible


def default_data_dir() -> Path:
    env = os.environ.get("BTM_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "bible-translation-finder"


def translation_filename(t: dict) -> str:
    return f"{t['abbreviation'].lower()}_{t['id'].replace('-', '_')}.xml"


class Library:
    """Manages a local collection of Bible translations."""

    def __init__(self, data_dir: Optional[Path | str] = None):
        self.data_dir = Path(data_dir).expanduser() if data_dir else default_data_dir()
        self._cache: dict[str, Bible] = {}

    # -- catalog ------------------------------------------------------
    def list_translations(self, include_copyrighted: bool = True) -> list[dict]:
        translations = _catalog.get_catalog()
        if not include_copyrighted:
            translations = [t for t in translations if t["freely_available"]]
        return sorted(translations, key=lambda t: t.get("popularity_rank", 99))

    def find_translations(self, query: str = "", language: str = "") -> list[dict]:
        """Offline search of the curated catalog."""
        return _catalog.search_catalog(query=query, language=language)

    def languages(self) -> list[str]:
        return _catalog.list_languages()

    def resolve(self, translation: str) -> dict:
        """Resolve an abbreviation or id to a catalog entry."""
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
        """Catalog entries that have a cached XML file in this library."""
        have = []
        for t in _catalog.get_catalog():
            if (self.data_dir / translation_filename(t)).exists():
                have.append(t)
        return sorted(have, key=lambda t: t.get("popularity_rank", 99))

    # -- download -----------------------------------------------------
    def download(
        self, translation: str, overwrite: bool = False, progress: bool = True
    ) -> Path:
        """Download (if needed) and return the cached OpenSong XML path.

        Copyrighted translations without a free source produce a stub file.
        """
        t = self.resolve(translation)
        dest = self.data_dir / translation_filename(t)
        if dest.exists() and not overwrite:
            return dest
        self.data_dir.mkdir(parents=True, exist_ok=True)

        opensong_xml: Optional[str] = None
        if t["freely_available"]:
            if progress:
                print(f"Downloading {t['name']} ({t['abbreviation']})...")
            opensong_xml = self._fetch(t)
        else:
            if progress:
                print(f"Note: {t['abbreviation']} is copyrighted; writing stub file.")

        from .cli import _make_stub  # reuse the stub builder

        if opensong_xml:
            content = '<?xml version="1.0" encoding="UTF-8"?>\n' + opensong_xml
        else:
            content = _make_stub(t)
        dest.write_text(content, encoding="utf-8")
        if progress:
            print(f"Wrote: {dest}")
        # Drop any stale in-memory copy so the next load re-reads the file.
        self._cache.pop(t["id"], None)
        return dest

    def _fetch(self, t: dict) -> Optional[str]:
        source_type = t.get("source_type")
        source_url = t.get("source_url")
        source_format = t.get("source_format")
        if source_type == "youversion":
            version_id = t.get("youversion_id")
            books = _scraper.YOUVERSION_BOOKS.get(t.get("youversion_books"))
            if not version_id or not books:
                raise ValueError(f"No YouVersion config for {t['abbreviation']}")
            print("  Downloading from YouVersion (bible.com); this takes a while...")
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
        print("  Converting to OpenSong format...")
        return _converter.convert_to_opensong(raw, source_format)

    # -- loading ------------------------------------------------------
    def load(self, translation: str = "KJV", download: bool = True) -> Bible:
        """Load a translation as a :class:`Bible` (cached in memory).

        Downloads it first unless ``download=False``.
        """
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

    def load_file(self, path: Path | str, translation: str = "") -> Bible:
        """Load any OpenSong XML file directly (no catalog needed)."""
        return Bible.from_file(path, translation=translation)

    def clear_cache(self) -> None:
        self._cache.clear()


# Shared default library for the top-level convenience functions.
_default_library: Optional[Library] = None


def get_library(data_dir: Optional[Path | str] = None) -> Library:
    global _default_library
    if data_dir is not None:
        return Library(data_dir)
    if _default_library is None:
        _default_library = Library()
    return _default_library

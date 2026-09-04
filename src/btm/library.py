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
    translations: list[str],
    output_dir: Optional[Union[Path, str]] = None,
    data_dir: Optional[Union[Path, str]] = None,
    overwrite: bool = False,
    progress: bool = True,
) -> list[Path]:
    """Download several translations; returns the list of written file paths."""
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
        return download(
            translation,
            output_dir=None,
            data_dir=self.data_dir,
            overwrite=overwrite,
            progress=progress,
        )

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
    abbrev = (t.get("abbreviation") or t.get("id") or "bible").lower()
    tid = (t.get("id") or abbrev).replace("-", "_").replace(" ", "_")
    return f"{abbrev}_{tid}.xml"


def _resolve_translation(translation: Union[str, dict]) -> dict:
    if isinstance(translation, dict):
        return translation
    t = _catalog.get_by_abbreviation(translation)
    if t is not None:
        return t
    key = translation.strip().lower()
    for entry in _catalog.get_catalog():
        if entry.get("id", "").lower() == key or entry.get("abbreviation", "").lower() == key:
            return entry
    eb = _scraper.get_ebible_translation_details(translation)
    if eb is not None:
        return eb
    raise KeyError(
        f"Unknown translation: {translation!r}. "
        "Use list_translations() or find_translations() to browse what is available."
    )


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
        raise ValueError(f"No download method for {t.get('abbreviation', t.get('id', 'unknown'))}")
    if not raw:
        return None
    return _converter.convert_to_opensong(raw, source_format)


def fetch_xml(translation: Union[str, dict]) -> str:
    """Return the OpenSong XML for ``translation`` as a string (no disk write).

    Useful when you want to stream the XML into another pipeline (e.g. load
    it directly into FreeShow's stage-display plugin) without touching the
    filesystem.
    """
    t = _resolve_translation(translation)
    if not t.get("freely_available", True):
        return _make_stub(t)
    xml = _fetch_opensong_xml(t)
    if not xml:
        return _make_stub(t)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml


def download(
    translation: Union[str, dict],
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
    t = _resolve_translation(translation)
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

    def resolve(self, translation: Union[str, dict]) -> dict:
        return _resolve_translation(translation)

    # -- local files --------------------------------------------------
    def file_for(self, translation: Union[str, dict]) -> Path:
        if isinstance(translation, (Path, str)) and str(translation).endswith(".xml") and Path(translation).exists():
            return Path(translation)
        t = self.resolve(translation)
        expected = self.data_dir / translation_filename(t)
        if expected.exists():
            return expected
        abbrev = (t.get("abbreviation") or "").lower()
        if abbrev:
            for cand in (self.data_dir / f"{abbrev}.xml", self.data_dir / f"{abbrev.upper()}.xml"):
                if cand.exists():
                    return cand
        return expected

    def is_downloaded(self, translation: Union[str, dict]) -> bool:
        try:
            return self.file_for(translation).exists()
        except KeyError:
            return False

    def downloaded(self) -> list[dict]:
        have = []
        seen_paths = set()
        for t in _catalog.get_catalog():
            fn = self.data_dir / translation_filename(t)
            if fn.exists():
                have.append(t)
                seen_paths.add(fn.resolve())
            else:
                abbrev = (t.get("abbreviation") or "").lower()
                if abbrev:
                    for cand in (self.data_dir / f"{abbrev}.xml", self.data_dir / f"{abbrev.upper()}.xml"):
                        if cand.exists():
                            have.append(t)
                            seen_paths.add(cand.resolve())
                            break
        for p in self.data_dir.glob("*.xml"):
            if p.resolve() in seen_paths:
                continue
            have.append({
                "id": p.stem.lower(),
                "abbreviation": p.stem.split("_")[0].upper() if "_" in p.stem else p.stem[:6].upper(),
                "name": p.stem.replace("_", " ").title(),
                "language": "Local",
                "freely_available": True,
                "path": p,
                "popularity_rank": 100,
            })
        return sorted(have, key=lambda t: t.get("popularity_rank", 99))

    def path(self, translation: Union[str, dict]) -> Path:
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


def scan_local_bibles(
    search_dirs: Optional[list[Union[Path, str]]] = None,
) -> list[dict]:
    """Scan local directories for OpenSong Bible XML files.

    Returns a list of metadata dicts for all detected OpenSong XML files.
    """
    import xml.etree.ElementTree as ET

    if search_dirs is None:
        dirs_to_check = [
            default_data_dir(),
            Path.home() / "Downloads",
            Path.home() / "projects" / "bible-translations",
        ]
    else:
        dirs_to_check = [Path(d).expanduser() for d in search_dirs]

    found: list[dict] = []
    seen_paths: set[Path] = set()

    for base_dir in dirs_to_check:
        base = Path(base_dir).expanduser()
        if not base.exists() or not base.is_dir():
            continue

        for p in base.glob("**/*.xml"):
            if not p.is_file():
                continue
            try:
                resolved = p.resolve()
            except Exception:
                continue
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)

            try:
                size = p.stat().st_size
                if size < 200:
                    continue
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    header = f.read(2048)
                if "<bible" not in header.lower() and "<xmlbible" not in header.lower() and "<usfx" not in header.lower():
                    continue

                tree = ET.parse(p)
                root = tree.getroot()
                tag_lower = root.tag.lower()
                if "bible" not in tag_lower and "usfx" not in tag_lower and "xmlbible" not in tag_lower:
                    continue

                is_zefania = "xmlbible" in tag_lower
                is_opensong = root.tag.lower() == "bible" and bool(root.findall("b") or root.findall(".//b"))

                if is_opensong:
                    b_elems = root.findall("b") or root.findall(".//b")
                    book_count = len(b_elems)
                    fmt = "opensong"
                elif is_zefania:
                    b_elems = root.findall("BIBLEBOOK") or root.findall(".//BIBLEBOOK")
                    book_count = len(b_elems)
                    fmt = "zefania"
                else:
                    b_elems = root.findall(".//book") or []
                    book_count = len(b_elems)
                    fmt = "usfx" if "usfx" in tag_lower else "xml"

                name = root.get("biblename") or root.get("name") or root.get("title") or ""
                if not name:
                    name = p.stem.replace("_", " ").title()

                abbrev = p.stem.split("_")[0].upper() if "_" in p.stem else p.stem[:6].upper()

                is_stub = False
                if is_opensong and b_elems:
                    first_v = b_elems[0].find(".//v")
                    if first_v is not None and first_v.text and "[Placeholder" in first_v.text:
                        is_stub = True

                found.append({
                    "id": p.stem.lower(),
                    "abbreviation": abbrev,
                    "name": name,
                    "language": "Local File",
                    "path": p,
                    "size_bytes": size,
                    "book_count": book_count,
                    "format": fmt,
                    "is_opensong": is_opensong,
                    "freely_available": True,
                    "is_stub": is_stub,
                    "is_local": True,
                })
            except Exception:
                continue

    return sorted(found, key=lambda x: str(x["name"]))


def convert_local_bible(
    source_path: Union[Path, str],
    output_dir: Optional[Union[Path, str]] = None,
    output_filename: Optional[str] = None,
) -> Path:
    """Convert a local Bible XML file (Zefania, OSIS, USFX, or OpenSong) to standard OpenSong format."""
    import xml.etree.ElementTree as ET

    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Source Bible file does not exist: {src}")

    dest_dir = Path(output_dir).expanduser() if output_dir else default_data_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    content = src.read_text(encoding="utf-8", errors="ignore")
    tree = ET.fromstring(content)
    tag_lower = tree.tag.lower()

    if tag_lower == "bible" and bool(tree.findall("b")):
        # Already OpenSong format!
        out_name = output_filename or f"{src.stem.lower()}_opensong.xml"
        dest = dest_dir / out_name
        if dest.resolve() != src.resolve():
            dest.write_text(content, encoding="utf-8")
        return dest
    elif "xmlbible" in tag_lower:
        opensong_xml = _converter.convert_zefania_to_opensong(content)
        if not opensong_xml:
            raise ValueError(f"Failed to convert Zefania XML file {src.name}")
        abbrev = src.stem.split("_")[0].lower()
        out_name = output_filename or f"{abbrev}_{src.stem.lower()}.xml"
        dest = dest_dir / out_name
        dest.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + opensong_xml, encoding="utf-8")
        return dest
    elif "usfx" in tag_lower:
        opensong_xml = _converter.convert_usfx_to_opensong(content)
        if not opensong_xml:
            raise ValueError(f"Failed to convert USFX XML file {src.name}")
        out_name = output_filename or f"{src.stem.lower()}.xml"
        dest = dest_dir / out_name
        dest.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + opensong_xml, encoding="utf-8")
        return dest
    else:
        opensong_xml = _converter.convert_osis_to_opensong(content)
        if not opensong_xml:
            raise ValueError(f"Failed to convert OSIS XML file {src.name}")
        out_name = output_filename or f"{src.stem.lower()}.xml"
        dest = dest_dir / out_name
        dest.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + opensong_xml, encoding="utf-8")
        return dest





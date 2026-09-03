"""Core query API: load an OpenSong Bible XML file and look up verses.

This module is deliberately dependency-free (stdlib only) so GUIs, TUIs,
and API servers can all build on it.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional, Union

from .converter import BIBLE_BOOKS, book_alias_to_name
from .reference import Reference, normalize_book_name, parse_reference


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _verse_sort_key(verse_id: str):
    s = str(verse_id).strip()
    m = re.match(r"(\d+)", s)
    if m:
        return (0, int(m.group(1)), s)
    return (1, 0, s)


def _verse_id_covers(verse_id: str, number: int) -> bool:
    """True if an OpenSong verse id (e.g. '5' or bridge '5-6') covers number."""
    s = str(verse_id).strip()
    if s == str(number):
        return True
    m = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", s)
    if m:
        try:
            return int(m.group(1)) <= number <= int(m.group(2))
        except ValueError:
            return False
    m2 = re.match(r"^(\d+)", s)
    return m2 is not None and int(m2.group(1)) == number


@dataclass(frozen=True)
class Verse:
    """A single Bible verse."""

    book: str
    chapter: int
    verse: str
    text: str
    translation: str = ""

    @property
    def reference(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"

    def __str__(self) -> str:
        label = f"{self.reference} ({self.translation})" if self.translation else self.reference
        return f"{label} — {self.text}"


@dataclass(frozen=True)
class Passage:
    """An ordered list of verses for one reference."""

    reference: str
    translation: str
    verses: tuple[Verse, ...] = field(default_factory=tuple)

    @property
    def text(self) -> str:
        """Verses joined as 'Book C:V text' lines."""
        return "\n".join(f"{v.reference} {v.text}" for v in self.verses)

    @property
    def text_inline(self) -> str:
        """All verse texts joined into one string (for display/TTS)."""
        return " ".join(v.text for v in self.verses)

    def __len__(self) -> int:
        return len(self.verses)

    def __iter__(self) -> Iterator[Verse]:
        return iter(self.verses)


# books[book][chapter][verse_id] = text
_Books = dict[str, dict[int, dict[str, str]]]


def _parse_opensong_element(root: ET.Element, translation: str = "") -> _Books:
    books: _Books = {}
    for b in root.findall("b"):
        raw_name = (b.get("name") or b.get("n") or "").strip()
        if not raw_name:
            continue
        try:
            name = normalize_book_name(raw_name)
        except ValueError:
            # Fall back to converter alias; skip if still unknown.
            try:
                candidate = book_alias_to_name(raw_name)
            except Exception:
                continue
            if candidate not in BIBLE_BOOKS:
                continue
            name = candidate
        chapters: dict[int, dict[str, str]] = books.setdefault(name, {})
        for c in b.findall("c"):
            try:
                cnum = int(str(c.get("n", "")).strip())
            except ValueError:
                continue
            verses = chapters.setdefault(cnum, {})
            for v in c.findall("v"):
                vnum = (v.get("n") or "").strip()
                if not vnum:
                    continue
                text = _collapse_ws("".join(v.itertext()))
                if text:
                    verses[vnum] = text
    return books


class Bible:
    """A loaded Bible translation ready for verse lookup and search.

    Use :meth:`from_file`, :meth:`from_opensong_xml`, or a
    :class:`btm.library.Library` to obtain an instance::

        bible = Bible.from_file("output/kjv_eng_kjv.xml", translation="KJV")
        print(bible.get_verse("John", 3, 16).text)
        print(bible.get_passage("Ps 23:1-3").text)
        for hit in bible.search("everlasting"):
            print(hit)
    """

    def __init__(self, books: _Books, translation: str = "", name: str = ""):
        self._books = books
        self.translation = translation
        self.name = name or translation

    # -- constructors -------------------------------------------------
    @classmethod
    def from_opensong_xml(
        cls, xml: str, translation: str = "", name: str = ""
    ) -> "Bible":
        if xml.lstrip().startswith("\ufeff"):
            xml = xml.lstrip("\ufeff")
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as e:
            raise ValueError(f"Could not parse OpenSong XML: {e}")
        if root.tag != "bible":
            raise ValueError(
                f"Expected <bible> root element, found <{root.tag}>"
            )
        books = _parse_opensong_element(root, translation=translation)
        if not books:
            raise ValueError("No Bible books found in OpenSong XML")
        return cls(books, translation=translation, name=name or translation)

    @classmethod
    def from_file(
        cls, path: Union[str, Path], translation: str = "", name: str = ""
    ) -> "Bible":
        path = Path(path)
        xml = path.read_text(encoding="utf-8-sig")
        # Default the translation label from the filename when possible.
        label = translation or path.stem.split("_")[0].upper()
        return cls.from_opensong_xml(xml, translation=label, name=name or label)

    # -- metadata -----------------------------------------------------
    @property
    def book_names(self) -> list[str]:
        """Canonical book names present in this translation, in order."""
        return [b for b in BIBLE_BOOKS if b in self._books]

    def has_book(self, book: str) -> bool:
        try:
            return normalize_book_name(book) in self._books
        except ValueError:
            return False

    def chapters(self, book: str) -> list[int]:
        name = normalize_book_name(book)
        if name not in self._books:
            raise KeyError(f"Book not in this translation: {name!r}")
        return sorted(self._books[name].keys())

    def verse_count(self) -> int:
        return sum(
            len(verses)
            for chapters in self._books.values()
            for verses in chapters.values()
        )

    def __len__(self) -> int:
        return self.verse_count()

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            try:
                self.get_passage(item)
                return True
            except (ValueError, KeyError):
                return False
        return False

    # -- lookup -------------------------------------------------------
    def get_verse(
        self, book: str, chapter: int, verse: Union[int, str]
    ) -> Verse:
        """Return a single verse. ``verse`` may be an int or an id string."""
        name = normalize_book_name(book)
        if name not in self._books:
            raise KeyError(f"Book not in this translation: {name!r}")
        chapters = self._books[name]
        if chapter not in chapters:
            raise KeyError(f"{name} {chapter} not in this translation")
        verses = chapters[chapter]
        wanted = int(verse) if isinstance(verse, int) else None
        key = str(verse).strip()
        if key in verses:
            return Verse(
                book=name,
                chapter=chapter,
                verse=key,
                text=verses[key],
                translation=self.translation,
            )
        if wanted is not None:
            # Verse bridges ("5-6") or suffixed ids ("3a"): find covering id.
            for vid in sorted(verses.keys(), key=_verse_sort_key):
                if _verse_id_covers(vid, wanted):
                    return Verse(
                        book=name,
                        chapter=chapter,
                        verse=vid,
                        text=verses[vid],
                        translation=self.translation,
                    )
            raise KeyError(f"{name} {chapter}:{verse} not in this translation")
        raise KeyError(f"{name} {chapter}:{verse} not in this translation")

    def get_passage(self, ref: Union[str, Reference]) -> Passage:
        """Return all verses for a reference like 'John 3:16-18' or 'Ps 23'."""
        r = parse_reference(ref) if isinstance(ref, str) else ref
        if r.is_whole_book:
            verses: list[Verse] = []
            for cnum in self.chapters(r.book):
                verses.extend(self._chapter_verses(r.book, cnum))
            return Passage(
                reference=str(r), translation=self.translation, verses=tuple(verses)
            )
        assert r.chapter is not None
        if r.verse_start is None:
            return Passage(
                reference=str(r),
                translation=self.translation,
                verses=tuple(self._chapter_verses(r.book, r.chapter)),
            )
        assert r.verse_start is not None
        end = r.verse_end if r.verse_end is not None else r.verse_start
        found: list[Verse] = []
        for vnum in range(r.verse_start, end + 1):
            try:
                found.append(self.get_verse(r.book, r.chapter, vnum))
            except KeyError:
                continue
        if not found:
            raise KeyError(f"{r} not in this translation ({self.translation})")
        return Passage(
            reference=str(r), translation=self.translation, verses=tuple(found)
        )

    def get_chapter(self, book: str, chapter: int) -> Passage:
        """Return every verse in a chapter."""
        name = normalize_book_name(book)
        return Passage(
            reference=f"{name} {chapter}",
            translation=self.translation,
            verses=tuple(self._chapter_verses(name, chapter)),
        )

    def _chapter_verses(self, book: str, chapter: int) -> list[Verse]:
        name = normalize_book_name(book)
        if name not in self._books:
            raise KeyError(f"Book not in this translation: {name!r}")
        chapters = self._books[name]
        if chapter not in chapters:
            raise KeyError(f"{name} {chapter} not in this translation")
        verses = chapters[chapter]
        return [
            Verse(
                book=name,
                chapter=chapter,
                verse=vid,
                text=verses[vid],
                translation=self.translation,
            )
            for vid in sorted(verses.keys(), key=_verse_sort_key)
        ]

    # -- search -------------------------------------------------------
    def search(
        self,
        query: str,
        limit: int = 50,
        case_sensitive: bool = False,
        books: Optional[list[str]] = None,
    ) -> list[Verse]:
        """Full-text substring search over verse texts.

        ``books`` optionally restricts the search to given books
        (names or abbreviations).
        """
        if not query or not query.strip():
            raise ValueError("Search query must not be empty")
        needle = query if case_sensitive else query.lower()
        only: Optional[set[str]] = None
        if books:
            only = {normalize_book_name(b) for b in books}
        hits: list[Verse] = []
        for bname in BIBLE_BOOKS:
            if bname not in self._books:
                continue
            if only is not None and bname not in only:
                continue
            for cnum in sorted(self._books[bname].keys()):
                verses = self._books[bname][cnum]
                for vid in sorted(verses.keys(), key=_verse_sort_key):
                    text = verses[vid]
                    hay = text if case_sensitive else text.lower()
                    if needle in hay:
                        hits.append(
                            Verse(
                                book=bname,
                                chapter=cnum,
                                verse=vid,
                                text=text,
                                translation=self.translation,
                            )
                        )
                        if len(hits) >= limit:
                            return hits
        return hits

    # Backwards-compatible alias
    find = search

"""Bible reference parsing: "John 3:16", "Ps 23", "1 Cor 13:4-7", ..."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .converter import BIBLE_BOOKS, book_alias_to_name


# Extra common abbreviations not already covered by converter.BOOK_ALIASES.
# Keys are compared lowercased with spaces/dots removed.
_EXTRA_ABBREVS = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
    "exo": "Exodus", "ex": "Exodus", "exod": "Exodus",
    "lev": "Leviticus", "le": "Leviticus", "lv": "Leviticus",
    "num": "Numbers", "nu": "Numbers", "nm": "Numbers",
    "deut": "Deuteronomy", "dt": "Deuteronomy",
    "josh": "Joshua", "jos": "Joshua", "jsh": "Joshua",
    "judg": "Judges", "jdg": "Judges", "jg": "Judges",
    "ruth": "Ruth", "ru": "Ruth", "rth": "Ruth",
    "1sam": "1 Samuel", "1sa": "1 Samuel", "1sm": "1 Samuel",
    "2sam": "2 Samuel", "2sa": "2 Samuel", "2sm": "2 Samuel",
    "1kgs": "1 Kings", "1ki": "1 Kings", "1kin": "1 Kings",
    "2kgs": "2 Kings", "2ki": "2 Kings", "2kin": "2 Kings",
    "1chr": "1 Chronicles", "1ch": "1 Chronicles",
    "2chr": "2 Chronicles", "2ch": "2 Chronicles",
    "ezra": "Ezra", "ezr": "Ezra",
    "neh": "Nehemiah", "ne": "Nehemiah",
    "esth": "Esther", "est": "Esther", "es": "Esther",
    "job": "Job", "jb": "Job",
    "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms", "psalms": "Psalms", "pss": "Psalms",
    "prov": "Proverbs", "pro": "Proverbs", "pr": "Proverbs", "proverbs": "Proverbs",
    "eccl": "Ecclesiastes", "ecc": "Ecclesiastes", "ec": "Ecclesiastes",
    "song": "Song of Solomon", "sos": "Song of Solomon", "songofsolomon": "Song of Solomon",
    "songofsongs": "Song of Solomon", "canticles": "Song of Solomon",
    "isa": "Isaiah", "is": "Isaiah",
    "jer": "Jeremiah", "je": "Jeremiah", "jr": "Jeremiah",
    "lam": "Lamentations", "la": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel", "ezk": "Ezekiel",
    "dan": "Daniel", "da": "Daniel", "dn": "Daniel",
    "hos": "Hosea", "ho": "Hosea",
    "joel": "Joel", "jl": "Joel",
    "amos": "Amos", "am": "Amos",
    "obad": "Obadiah", "ob": "Obadiah",
    "jonah": "Jonah", "jon": "Jonah",
    "mic": "Micah", "mi": "Micah",
    "nah": "Nahum", "na": "Nahum",
    "hab": "Habakkuk", "hb": "Habakkuk",
    "zeph": "Zephaniah", "zep": "Zephaniah",
    "hag": "Haggai", "hg": "Haggai",
    "zech": "Zechariah", "zec": "Zechariah", "zc": "Zechariah",
    "mal": "Malachi",
    "matt": "Matthew", "mat": "Matthew", "mt": "Matthew",
    "mark": "Mark", "mar": "Mark", "mk": "Mark", "mrk": "Mark",
    "luke": "Luke", "luk": "Luke", "lk": "Luke",
    "john": "John", "joh": "John", "jn": "John", "jhn": "John",
    "acts": "Acts", "act": "Acts", "ac": "Acts",
    "rom": "Romans",
    "1cor": "1 Corinthians", "1co": "1 Corinthians",
    "2cor": "2 Corinthians", "2co": "2 Corinthians",
    "gal": "Galatians",
    "eph": "Ephesians", "ep": "Ephesians",
    "phil": "Philippians", "php": "Philippians", "pp": "Philippians",
    "col": "Colossians",
    "1thess": "1 Thessalonians", "1th": "1 Thessalonians", "1thes": "1 Thessalonians",
    "2thess": "2 Thessalonians", "2th": "2 Thessalonians", "2thes": "2 Thessalonians",
    "1tim": "1 Timothy", "1ti": "1 Timothy",
    "2tim": "2 Timothy", "2ti": "2 Timothy",
    "titus": "Titus", "tit": "Titus", "ti": "Titus",
    "philem": "Philemon", "phm": "Philemon", "phlm": "Philemon",
    "heb": "Hebrews",
    "jas": "James", "jm": "James",
    "1pet": "1 Peter", "1pe": "1 Peter", "1pt": "1 Peter",
    "2pet": "2 Peter", "2pe": "2 Peter", "2pt": "2 Peter",
    "1john": "1 John", "1jn": "1 John", "1jo": "1 John",
    "2john": "2 John", "2jn": "2 John", "2jo": "2 John",
    "3john": "3 John", "3jn": "3 John", "3jo": "3 John",
    "jude": "Jude", "jud": "Jude",
    "rev": "Revelation",
}


def _build_book_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for name in BIBLE_BOOKS:
        lookup[name.lower().replace(" ", "")] = name
        lookup[name.lower()] = name
    from .converter import BOOK_ALIASES

    for alias, name in BOOK_ALIASES.items():
        lookup[alias.lower().replace(" ", "")] = name
    for alias, name in _EXTRA_ABBREVS.items():
        lookup.setdefault(alias, name)
    return lookup


_BOOK_LOOKUP = _build_book_lookup()


def normalize_book_name(raw: str) -> str:
    """Return the canonical English book name for an abbreviation or name.

    Raises ValueError if the book cannot be recognised.
    """
    key = raw.strip().lower().replace(".", "").replace(" ", "")
    if key in _BOOK_LOOKUP:
        return _BOOK_LOOKUP[key]
    # Fall back to the converter's alias logic (handles OSIS codes etc.)
    try:
        candidate = book_alias_to_name(raw)
    except Exception:
        candidate = raw.strip()
    if candidate in BIBLE_BOOKS:
        return candidate
    raise ValueError(
        f"Unknown Bible book: {raw!r}. "
        "Use a full name ('Genesis') or abbreviation ('Gen', '1 Cor')."
    )


@dataclass(frozen=True)
class Reference:
    """A parsed Bible reference."""

    book: str
    chapter: Optional[int] = None
    verse_start: Optional[int] = None
    verse_end: Optional[int] = None

    def __post_init__(self):
        if self.book not in BIBLE_BOOKS:
            raise ValueError(f"Unknown Bible book: {self.book!r}")
        if self.verse_start is not None and self.chapter is None:
            raise ValueError("A verse number requires a chapter number")
        if self.verse_end is not None and self.verse_start is None:
            raise ValueError("A verse range requires a start verse")

    @property
    def is_whole_chapter(self) -> bool:
        return self.chapter is not None and self.verse_start is None

    @property
    def is_whole_book(self) -> bool:
        return self.chapter is None

    def __str__(self) -> str:
        s = self.book
        if self.chapter is None:
            return s
        s += f" {self.chapter}"
        if self.verse_start is None:
            return s
        s += f":{self.verse_start}"
        if self.verse_end is not None and self.verse_end != self.verse_start:
            s += f"-{self.verse_end}"
        return s


_REFERENCE_RE = re.compile(
    r"^\s*(?P<book>.*?)\s+"
    r"(?P<chapter>\d+)"
    r"(?:\s*:\s*(?P<vstart>\d+)"
    r"(?:\s*[-–—]\s*(?P<vend>\d+))?"
    r")?\s*$"
)

_BOOK_ONLY_RE = re.compile(r"^\s*(?P<book>[A-Za-z][A-Za-z .]*?)\s*$")


def parse_reference(text: str) -> Reference:
    """Parse a reference like 'John 3:16', 'Ps 23', '1 Cor 13:4-7'.

    Raises ValueError on unparseable input.
    """
    if not text or not text.strip():
        raise ValueError("Empty Bible reference")
    cleaned = text.strip().replace("–", "-").replace("—", "-")

    m = _REFERENCE_RE.match(cleaned)
    if m:
        book = normalize_book_name(m.group("book"))
        chapter = int(m.group("chapter"))
        vstart = m.group("vstart")
        vend = m.group("vend")
        if vstart is None:
            return Reference(book=book, chapter=chapter)
        verse_start = int(vstart)
        verse_end = int(vend) if vend is not None else verse_start
        if verse_end < verse_start:
            raise ValueError(f"Invalid verse range in reference: {text!r}")
        if chapter < 1 or verse_start < 1:
            raise ValueError(f"Invalid reference: {text!r}")
        return Reference(
            book=book, chapter=chapter, verse_start=verse_start, verse_end=verse_end
        )

    m2 = _BOOK_ONLY_RE.match(cleaned)
    if m2:
        try:
            book = normalize_book_name(m2.group("book"))
        except ValueError:
            pass
        else:
            return Reference(book=book)

    raise ValueError(
        f"Could not parse Bible reference: {text!r}. "
        "Examples: 'John 3:16', 'Ps 23', '1 Cor 13:4-7'."
    )

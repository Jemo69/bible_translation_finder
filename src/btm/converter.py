import re
import xml.etree.ElementTree as ET
from typing import Optional

BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]

BOOK_ALIASES = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers", "DEU": "Deuteronomy",
    "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth", "1SA": "1 Samuel", "2SA": "2 Samuel",
    "1KI": "1 Kings", "2KI": "2 Kings", "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra",
    "NEH": "Nehemiah", "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah", "JER": "Jeremiah", "LAM": "Lamentations",
    "EZK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos",
    "OBA": "Obadiah", "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk",
    "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts",
    "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians",
    "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians", "1TH": "1 Thessalonians", "2TH": "2 Thessalonians",
    "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John", "2JN": "2 John",
    "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
    # OSIS format abbreviations
    "EXOD": "Exodus", "JOSH": "Joshua", "JUDG": "Judges", "RUTH": "Ruth",
    "1SAM": "1 Samuel", "2SAM": "2 Samuel", "1KGS": "1 Kings", "2KGS": "2 Kings",
    "1CHR": "1 Chronicles", "2CHR": "2 Chronicles", "EZRA": "Ezra", "NEH": "Nehemiah",
    "ESTH": "Esther", "JOB": "Job", "PS": "Psalms", "PROV": "Proverbs",
    "ECCL": "Ecclesiastes", "SONG": "Song of Solomon", "ISA": "Isaiah", "JER": "Jeremiah",
    "LAM": "Lamentations", "EZEK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea",
    "JOEL": "Joel", "AMOS": "Amos", "OBAD": "Obadiah", "JONAH": "Jonah",
    "MIC": "Micah", "NAH": "Nahum", "HAB": "Habakkuk", "ZEPH": "Zephaniah",
    "HAG": "Haggai", "ZECH": "Zechariah", "MAL": "Malachi",
    "MATT": "Matthew", "MARK": "Mark", "LUKE": "Luke", "JOHN": "John",
    "ACTS": "Acts", "ROM": "Romans",
    "1COR": "1 Corinthians", "2COR": "2 Corinthians", "GAL": "Galatians",
    "EPH": "Ephesians", "PHIL": "Philippians", "COL": "Colossians",
    "1THESS": "1 Thessalonians", "2THESS": "2 Thessalonians",
    "1TIM": "1 Timothy", "2TIM": "2 Timothy", "TITUS": "Titus",
    "PHLM": "Philemon", "HEB": "Hebrews", "JAS": "James",
    "1PET": "1 Peter", "2PET": "2 Peter", "1JOHN": "1 John", "2JOHN": "2 John",
    "3JOHN": "3 John", "JUDE": "Jude", "REV": "Revelation",
    # More variants
    "GEN": "Genesis", "DEUT": "Deuteronomy", "NUM": "Numbers",
    "SONG OF SOL": "Song of Solomon", "SONGOFSOL": "Song of Solomon",
    "PS": "Psalms", "PSS": "Psalms",
    # Singular / common spelling variants
    "PSALM": "Psalms", "PROVERB": "Proverbs",
    "SONG OF SONGS": "Song of Solomon",
    "CANTICLES": "Song of Solomon", "CANTICLE OF CANTICLES": "Song of Solomon",
    "1 SAMUEL": "1 Samuel", "2 SAMUEL": "2 Samuel",
    "1 KINGS": "1 Kings", "2 KINGS": "2 Kings",
    "1 CHRONICLES": "1 Chronicles", "2 CHRONICLES": "2 Chronicles",
    "1 CORINTHIANS": "1 Corinthians", "2 CORINTHIANS": "2 Corinthians",
    "1 THESSALONIANS": "1 Thessalonians", "2 THESSALONIANS": "2 Thessalonians",
    "1 TIMOTHY": "1 Timothy", "2 TIMOTHY": "2 Timothy",
    "1 PETER": "1 Peter", "2 PETER": "2 Peter",
    "1 JOHN": "1 John", "2 JOHN": "2 John", "3 JOHN": "3 John",
}


def book_alias_to_name(raw: str) -> str:
    raw_upper = raw.strip().upper()
    raw_title = raw.strip().title()
    if raw_title in BIBLE_BOOKS:
        return raw_title
    if raw_upper in BOOK_ALIASES:
        return BOOK_ALIASES[raw_upper]
    if raw_title.startswith("Song Of "):
        return "Song of Solomon"
    return raw_title


def _safe_sort_key(value: str):
    """Sort key for chapter/verse numbers.

    Handles plain integers ("1", "12"), ranges ("1-2"), and
    suffixed variants ("1a", "3b"). Non-numeric values sort last.
    """
    s = str(value).strip()
    if not s:
        return (1, 0, "")
    # Leading integer part (handles "3-4", "1a", etc.)
    num_str = ""
    for ch in s:
        if ch.isdigit():
            num_str += ch
        else:
            break
    if num_str:
        try:
            return (0, int(num_str), s)
        except ValueError:
            pass
    return (1, 0, s)


def _clean_verse_text(text: str) -> str:
    """Collapse whitespace in verse text."""
    import re as _re

    return _re.sub(r"\s+", " ", (text or "")).strip()


def make_opensong_element(book_name: str, chapters: dict) -> ET.Element:
    bible = ET.Element("bible")
    book_num = BIBLE_BOOKS.index(book_name) + 1 if book_name in BIBLE_BOOKS else 0
    b = ET.SubElement(bible, "b", {"n": str(book_num), "name": book_name})
    for cnum in sorted(chapters.keys(), key=_safe_sort_key):
        c = ET.SubElement(b, "c", {"n": str(cnum)})
        verses = chapters[cnum]
        for vnum in sorted(verses.keys(), key=_safe_sort_key):
            v = ET.SubElement(c, "v", {"n": str(vnum)})
            v.text = verses[vnum]
    return bible


def convert_usfx_to_opensong(xml_content: str) -> Optional[str]:
    """Convert USFX XML to OpenSong XML string.

    USFX structure (eBible / open-bibles):
      <usfx><book id="GEN">...<c id="1"/>...<v id="1"/>text<ve/>...
    Footnotes (<f>), cross-refs (<x>), and formatting (<wj>, <nd>, ...)
    are stripped; only verse text is kept.
    """
    # Strip BOM if present (some Zefania/USFX files start with one)
    if xml_content.startswith("\ufeff"):
        xml_content = xml_content.lstrip("\ufeff")
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse USFX XML: {e}")

    books_data: dict[str, dict[str, dict[str, str]]] = {}

    # USFX may or may not use namespaces; match by local name.
    def _local(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    for book_elem in root.iter():
        if _local(book_elem.tag) != "book":
            continue
        book_id = (book_elem.get("id") or "").strip()
        if not book_id or book_id in ("FRT", "BAK", "INT", "CNC", "GLO", "TDX", "NDX"):
            continue
        bname = book_alias_to_name(book_id)
        if bname not in BIBLE_BOOKS:
            continue
        chapters = _extract_usfx_book(book_elem)
        if chapters:
            # Merge (NT-only or partial books are fine)
            if bname in books_data:
                for cnum, verses in chapters.items():
                    books_data[bname].setdefault(cnum, {}).update(verses)
            else:
                books_data[bname] = chapters

    if not books_data:
        return None

    root_os = ET.Element("bible")
    for bname in BIBLE_BOOKS:
        if bname in books_data:
            chapters = books_data[bname]
            book_num = BIBLE_BOOKS.index(bname) + 1
            b = ET.SubElement(root_os, "b", {"n": str(book_num), "name": bname})
            for cnum in sorted(chapters.keys(), key=_safe_sort_key):
                c = ET.SubElement(b, "c", {"n": str(cnum)})
                verses = chapters[cnum]
                for vnum in sorted(verses.keys(), key=_safe_sort_key):
                    v = ET.SubElement(c, "v", {"n": str(vnum)})
                    v.text = verses[vnum]

    return ET.tostring(root_os, encoding="unicode")


def _extract_usfx_book(book_elem: ET.Element) -> dict:
    """Recursively walk a USFX <book> element collecting chapters/verses.

    USFX marks chapters/verses with empty milestones:
      <c id="1"/> ... <v id="1"/>verse text<ve/> ...
    Verse text may be split across paragraphs and contain inline
    formatting (<wj>, <nd>, <add>, ...). Footnotes (<f>), cross-refs
    (<x>), and front-matter (<toc>, <h>, <id>, ...) are excluded, but
    text *after* them (their tail) is kept.
    """
    chapters: dict[str, dict[str, str]] = {}
    current_chapter: Optional[str] = None
    current_verse: Optional[str] = None
    parts: list[str] = []

    SKIP_TAGS = {"f", "x", "note", "figure", "toc", "h", "id", "ide", "rem"}

    def _local(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    def _flush():
        nonlocal current_verse, parts
        if current_chapter is not None and current_verse is not None and parts:
            text = _clean_verse_text("".join(parts))
            if text:
                chapters.setdefault(current_chapter, {})
                existing = chapters[current_chapter].get(current_verse)
                chapters[current_chapter][current_verse] = (
                    f"{existing} {text}".strip() if existing else text
                )
        current_verse = None
        parts = []

    def _walk(elem: ET.Element, in_skip: bool):
        nonlocal current_chapter, current_verse, parts
        local = _local(elem.tag)
        now_skip = in_skip or (local in SKIP_TAGS)
        if local == "c" and not in_skip:
            _flush()
            cid = (elem.get("id") or "").strip()
            if cid:
                current_chapter = cid
                chapters.setdefault(current_chapter, {})
        elif local == "v" and not in_skip:
            _flush()
            vid = (elem.get("id") or "").strip()
            if current_chapter is not None and vid:
                current_verse = vid
                parts = []
        elif local == "ve" and not in_skip:
            _flush()
        else:
            if (
                not now_skip
                and current_chapter is not None
                and current_verse is not None
                and elem.text
            ):
                # Don't double-count text of child verse/chapter markers;
                # those elements' own text is usually None anyway.
                if local not in ("c", "v", "ve", "book"):
                    parts.append(elem.text)
                elif local in ("p", "q", "wj", "nd", "add", "em", "bd", "it", "sc"):
                    parts.append(elem.text)
        for child in list(elem):
            _walk(child, now_skip)
            if (
                not now_skip
                and current_chapter is not None
                and current_verse is not None
                and child.tail
            ):
                # Tail after footnotes should be kept; tail after <f>/<x>
                # is verse text continuing outside the note.
                parts.append(child.tail)
        # Handle the book element's own text (usually whitespace)
        if elem is book_elem and elem.text:
            pass

    # Seed: iterate children of book so <c>/<v> markers are visited in order.
    if book_elem.text and False:  # book-level text is never verse text
        pass
    for child in list(book_elem):
        _walk(child, False)
        # Tail of top-level children outside any verse is ignored unless
        # we are inside a verse (handled inside _walk via child.tail).
    _flush()
    # Drop empty chapters (e.g. front-matter <c> with no verses)
    return {c: v for c, v in chapters.items() if v}


def convert_zefania_to_opensong(xml_content: str) -> Optional[str]:
    if xml_content.startswith("\ufeff"):
        xml_content = xml_content.lstrip("\ufeff")
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse Zefania XML: {e}")

    ns = {"ns": "http://www.w3.org/2001/XMLSchema-instance"}
    books_data = {}

    for biblebook in root.iter("BIBLEBOOK"):
        bname_raw = biblebook.get("bname", "")
        bname = book_alias_to_name(bname_raw)
        chapters = {}

        for chapter in biblebook.iter("CHAPTER"):
            cnum = chapter.get("cnumber", "")
            verses = {}
            for verse in chapter.iter("VERS"):
                vnum = verse.get("vnumber", "")
                vtext = (verse.text or "").strip()
                if vtext:
                    verses[vnum] = vtext
            if verses:
                chapters[cnum] = verses

        if chapters:
            books_data[bname] = chapters

    if not books_data:
        return None

    root_os = ET.Element("bible")
    for bname in BIBLE_BOOKS:
        if bname in books_data:
            chapters = books_data[bname]
            book_num = BIBLE_BOOKS.index(bname) + 1 if bname in BIBLE_BOOKS else 0
            b = ET.SubElement(root_os, "b", {"n": str(book_num), "name": bname})
            for cnum in sorted(chapters.keys(), key=_safe_sort_key):
                c = ET.SubElement(b, "c", {"n": str(cnum)})
                verses = chapters[cnum]
                for vnum in sorted(verses.keys(), key=_safe_sort_key):
                    v = ET.SubElement(c, "v", {"n": str(vnum)})
                    v.text = verses[vnum]

    return ET.tostring(root_os, encoding="unicode")


def _extract_osis_verse_text(p_element, ns, tag):
    """Extract verse text from an OSIS p element.
    Supports both sID/eID marker style and direct <verse>OSIS style.
    Returns dict of {verse_num: text}.
    """
    result = {}
    current_vnum = None
    parts = []
    for elem in p_element.iter():
        if elem.tag == tag("verse"):
            if elem.get("sID"):
                if current_vnum is not None and parts:
                    result[current_vnum] = "".join(parts).strip()
                current_vnum = elem.get("n", "")
                parts = [elem.tail or ""]
            elif elem.get("eID"):
                if current_vnum is not None and parts:
                    result[current_vnum] = "".join(parts).strip()
                current_vnum = None
                parts = []
            else:
                # Direct <verse>text</verse> style
                if current_vnum is not None and parts:
                    result[current_vnum] = "".join(parts).strip()
                # Extract verse number from osisID (e.g. "Gen.1.2" -> "2")
                vn_raw = elem.get("osisID", "") or elem.get("n", "")
                if vn_raw:
                    vn = vn_raw.split(".")[-1]
                else:
                    vn = str(len(result) + 1)
                text = elem.text or ""
                current_vnum = vn
                parts = [text, elem.tail or ""] if elem.tail else [text]
        elif current_vnum is not None:
            text = elem.text or ""
            tail = elem.tail or ""
            if text:
                parts.append(text)
            if tail:
                parts.append(tail)
    if current_vnum is not None and parts:
        result[current_vnum] = _clean_verse_text("".join(parts))
        # Clean any previously stored values as well
        for _k in list(result.keys()):
            result[_k] = _clean_verse_text(result[_k])
    return result


def osisID_chapter_num(osis_id: str) -> str:
    """Extract chapter number from osisID like 'Gen.1'"""
    if "." in osis_id:
        return osis_id.split(".")[-1]
    return osis_id


def convert_osis_to_opensong(xml_content: str) -> Optional[str]:
    if xml_content.startswith("\ufeff"):
        xml_content = xml_content.lstrip("\ufeff")
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse OSIS XML: {e}")

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    def tag(name):
        return f"{ns}{name}" if ns else name

    books_data = {}
    for div in root.iter(tag("div")):
        dtype = div.get("type", "")
        if dtype != "book":
            continue
        bname_raw = div.get("osisID", "")
        if "." in bname_raw:
            bname_raw = bname_raw.split(".")[0]
        bname = book_alias_to_name(bname_raw)

        chapters = {}
        current_chapter = None
        current_verses = {}
        in_chapter = False

        for child in div:
            if child.tag == tag("chapter"):
                if child.get("sID"):
                    if current_chapter is not None and current_verses:
                        chapters[current_chapter] = current_verses
                    current_chapter = child.get("n", osisID_chapter_num(child.get("osisID", "")))
                    current_verses = {}
                    in_chapter = True
                    # Extract verses from chapter children (sID style)
                    chapter_verses = _extract_osis_verse_text(child, ns, tag)
                    for vn, vt in chapter_verses.items():
                        if vt:
                            current_verses[vn] = vt
                elif child.get("eID"):
                    if current_chapter is not None and current_verses:
                        chapters[current_chapter] = current_verses
                    current_chapter = None
                    in_chapter = False
                else:
                    # Self-closing <chapter osisID="Gen.1"/> style with direct verse children
                    if current_chapter is not None and current_verses:
                        chapters[current_chapter] = current_verses
                    current_chapter = osisID_chapter_num(child.get("osisID", ""))
                    current_verses = {}
                    in_chapter = True
                    # Extract verses from chapter's children
                    chapter_verses = _extract_osis_verse_text(child, ns, tag)
                    for vn, vt in chapter_verses.items():
                        if vt:
                            current_verses[vn] = vt
                continue

            # Handle verses inside <p> elements (direct div children)
            if child.tag == tag("p"):
                chapter_verses = _extract_osis_verse_text(child, ns, tag)
                for vn, vt in chapter_verses.items():
                    if vt:
                        if vn in current_verses:
                            current_verses[vn] += " " + vt
                        else:
                            current_verses[vn] = vt

        if current_chapter is not None and current_verses:
            chapters[current_chapter] = current_verses

        if chapters:
            books_data[bname] = chapters

    if not books_data:
        return None

    root_os = ET.Element("bible")
    for bname in BIBLE_BOOKS:
        if bname in books_data:
            chapters = books_data[bname]
            book_num = BIBLE_BOOKS.index(bname) + 1 if bname in BIBLE_BOOKS else 0
            b = ET.SubElement(root_os, "b", {"n": str(book_num), "name": bname})
            for cnum in sorted(chapters.keys(), key=_safe_sort_key):
                c = ET.SubElement(b, "c", {"n": str(cnum)})
                verses = chapters[cnum]
                for vnum in sorted(verses.keys(), key=_safe_sort_key):
                    v = ET.SubElement(c, "v", {"n": str(vnum)})
                    v.text = verses[vnum]

    return ET.tostring(root_os, encoding="unicode")


def convert_to_opensong(xml_content: str, source_format: str) -> Optional[str]:
    if source_format == "zefania":
        return convert_zefania_to_opensong(xml_content)
    elif source_format == "usfx":
        return convert_usfx_to_opensong(xml_content)
    elif source_format == "osis":
        return convert_osis_to_opensong(xml_content)
    else:
        raise ValueError(f"Unsupported source format: {source_format}")

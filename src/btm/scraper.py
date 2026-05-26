import csv
import io
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from typing import Optional

import requests
from bs4 import BeautifulSoup

EBIBLE_TRANSLATIONS_CSV = "https://ebible.org/Scriptures/translations.csv"
EBIBLE_USFX_PATTERN = "https://ebible.org/{trans_id}/{trans_id}_usfx.zip"
OPEN_BIBLES_RAW = "https://raw.githubusercontent.com/seven1m/open-bibles/master/{filename}"


def fetch_ebible_catalog() -> list[dict]:
    resp = requests.get(EBIBLE_TRANSLATIONS_CSV, timeout=30)
    resp.raise_for_status()
    content = resp.content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def search_ebible_catalog(query: str = "", language: str = "") -> list[dict]:
    catalog = fetch_ebible_catalog()
    results = []
    query_lower = query.lower()
    for entry in catalog:
        title = (entry.get("title", "") or "")
        eng_title = (entry.get("English Title", "") or "")
        lang = (entry.get("languageName", "") or "")
        lang_eng = (entry.get("languageNameInEnglish", "") or "")
        trans_id = (entry.get("translationId", "") or "")

        if query and query_lower not in title.lower() and query_lower not in eng_title.lower() and query_lower not in trans_id.lower():
            continue
        if language and language.lower() not in lang.lower() and language.lower() not in lang_eng.lower():
            continue

        results.append({
            "id": trans_id,
            "language": lang,
            "language_english": lang_eng,
            "title": title,
            "english_title": eng_title,
            "copyright": entry.get("Copyright", ""),
            "redistributable": entry.get("Redistributable", "").strip() == "True",
            "testament": "OT" if int(entry.get("OTbooks", "0") or "0") > 0 else "",
        })
        if int(entry.get("NTbooks", "0") or "0") > 0:
            results[-1]["testament"] += (" + " if results[-1]["testament"] else "") + "NT"

    return results


def download_ebible_usfx(source_url: str) -> Optional[str]:
    resp = requests.get(source_url, timeout=120)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    xml_content = None
    try:
        with zipfile.ZipFile(tmp_path, "r") as zf:
            all_files = zf.namelist()
            usfx_files = [n for n in all_files if n.endswith("_usfx.xml") or n.endswith(".usfx")]
            xml_files = [n for n in all_files if n.endswith(".xml") and "book" not in n.lower() and "metadata" not in n.lower()]
            if usfx_files:
                xml_filename = usfx_files[0]
            elif xml_files:
                xml_filename = xml_files[0]
            else:
                xml_files = [n for n in all_files if "." not in n.replace("/", "")]
                xml_filename = xml_files[0] if xml_files else None
            if xml_filename:
                xml_content = zf.read(xml_filename).decode("utf-8")
    finally:
        os.unlink(tmp_path)

    return xml_content


def download_open_bibles(filename: str) -> Optional[str]:
    url = OPEN_BIBLES_RAW.format(filename=filename)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text


def get_ebible_translation_details(translation_id: str) -> Optional[dict]:
    catalog = fetch_ebible_catalog()
    for entry in catalog:
        eid = entry.get("translationId", "")
        if eid == translation_id:
            return {
                "id": eid,
                "language": entry.get("languageName", ""),
                "title": entry.get("title", ""),
                "copyright": entry.get("Copyright", ""),
                "redistributable": entry.get("Redistributable", "").strip() == "True",
            }
    return None


# USFM book codes and chapter counts for TPT (51 books)
TPT_BOOKS = {
    "GEN": 50, "JOS": 24, "JDG": 21, "RUT": 4,
    "PSA": 150, "PRO": 31, "SNG": 8,
    "ISA": 66, "JER": 52, "LAM": 5, "EZK": 48, "DAN": 12,
    "HOS": 14, "JOL": 3, "AMO": 9, "OBA": 1, "JON": 4,
    "MIC": 7, "NAM": 3, "HAB": 3, "ZEP": 3, "HAG": 2, "ZEC": 14, "MAL": 4,
    "MAT": 28, "MRK": 16, "LUK": 24, "JHN": 21, "ACT": 28,
    "ROM": 16, "1CO": 16, "2CO": 13, "GAL": 6, "EPH": 6,
    "PHP": 4, "COL": 4, "1TH": 5, "2TH": 3, "1TI": 6, "2TI": 4,
    "TIT": 3, "PHM": 1, "HEB": 13, "JAS": 5, "1PE": 5, "2PE": 3,
    "1JN": 5, "2JN": 1, "3JN": 1, "JUD": 1, "REV": 22,
}
_BIBLE_ORDER = {
    "Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 4, "Deuteronomy": 5,
    "Joshua": 6, "Judges": 7, "Ruth": 8, "1 Samuel": 9, "2 Samuel": 10,
    "1 Kings": 11, "2 Kings": 12, "1 Chronicles": 13, "2 Chronicles": 14, "Ezra": 15,
    "Nehemiah": 16, "Esther": 17, "Job": 18, "Psalms": 19, "Proverbs": 20,
    "Ecclesiastes": 21, "Song of Solomon": 22, "Isaiah": 23, "Jeremiah": 24, "Lamentations": 25,
    "Ezekiel": 26, "Daniel": 27, "Hosea": 28, "Joel": 29, "Amos": 30,
    "Obadiah": 31, "Jonah": 32, "Micah": 33, "Nahum": 34, "Habakkuk": 35,
    "Zephaniah": 36, "Haggai": 37, "Zechariah": 38, "Malachi": 39,
    "Matthew": 40, "Mark": 41, "Luke": 42, "John": 43, "Acts": 44,
    "Romans": 45, "1 Corinthians": 46, "2 Corinthians": 47, "Galatians": 48,
    "Ephesians": 49, "Philippians": 50, "Colossians": 51, "1 Thessalonians": 52, "2 Thessalonians": 53,
    "1 Timothy": 54, "2 Timothy": 55, "Titus": 56, "Philemon": 57, "Hebrews": 58,
    "James": 59, "1 Peter": 60, "2 Peter": 61, "1 John": 62, "2 John": 63,
    "3 John": 64, "Jude": 65, "Revelation": 66,
}
TPT_VERSION_ID = "1849"
TPT_BASE_URL = "https://www.bible.com/bible/{version_id}/{usfm}"
TPT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def _parse_tpt_chapter(html: str) -> dict:
    """Parse verse text from bible.com chapter page HTML using BeautifulSoup."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return {}
    data = json.loads(m.group(1))
    content = data.get("props", {}).get("pageProps", {}).get("chapterInfo", {}).get("content", "")
    if not content:
        return {}

    soup = BeautifulSoup(content, "html.parser")
    verses = {}
    for verse_div in soup.find_all("span", class_=re.compile(r"verse v\d+")):
        cls = verse_div.get("class", [])
        vnum = None
        for c in cls:
            m2 = re.match(r"v(\d+)", c)
            if m2:
                vnum = m2.group(1)
                break
        if not vnum:
            continue

        # Remove footnote elements entirely (they have class "note")
        for note in verse_div.find_all("span", class_="note"):
            note.decompose()

        # Remove label elements (verse number)
        for label in verse_div.find_all("span", class_="label"):
            label.decompose()

        full_text = verse_div.get_text(separator=" ", strip=True)
        full_text = re.sub(r"\s+", " ", full_text).strip()
        if full_text:
            verses[vnum] = full_text

    return verses


def download_youversion_tpt() -> Optional[str]:
    """Download The Passion Translation (TPT) from YouVersion bible.com.
    Returns XML string in OpenSong format.
    """
    all_books = {}
    session = requests.Session()
    session.headers.update({"User-Agent": TPT_USER_AGENT})

    for usfm_code, chapters in TPT_BOOKS.items():
        book_verses = {}
        for ch in range(1, chapters + 1):
            url = TPT_BASE_URL.format(version_id=TPT_VERSION_ID, usfm=f"{usfm_code}.{ch}")
            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
                verses = _parse_tpt_chapter(resp.text)
                if verses:
                    book_verses[str(ch)] = verses
            except Exception:
                pass
        if book_verses:
            all_books[usfm_code] = book_verses

    if not all_books:
        return None

    # Convert to OpenSong XML
    from .converter import book_alias_to_name, make_opensong_element
    books_data = {}
    for usfm_code, chapters in all_books.items():
        bname = book_alias_to_name(usfm_code)
        if bname:
            books_data[bname] = chapters

    if not books_data:
        return None

    root = ET.Element("bible", {"name": "The Passion Translation"})
    for bname in sorted(books_data.keys(), key=lambda x: _BIBLE_ORDER.get(x, 999)):
        book_num = _BIBLE_ORDER.get(bname, 0)
        chapters = books_data[bname]
        b = ET.SubElement(root, "b", {"n": str(book_num), "name": bname})
        for cnum in sorted(chapters.keys(), key=lambda x: int(x)):
            verses = chapters[cnum]
            c = ET.SubElement(b, "c", {"n": str(cnum)})
            for vnum in sorted(verses.keys(), key=lambda x: int(x.split("-")[0])):
                v = ET.SubElement(c, "v", {"n": str(vnum)})
                v.text = verses[vnum]

    return ET.tostring(root, encoding="unicode")

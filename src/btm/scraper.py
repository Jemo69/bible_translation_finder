import csv
import hashlib
import io
import json
import os
import re
import string
import tempfile
import time
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


# USFM book codes and chapter counts
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

NIV_BOOKS = {
    "GEN": 50, "EXO": 40, "LEV": 27, "NUM": 36, "DEU": 34,
    "JOS": 24, "JDG": 21, "RUT": 4, "1SA": 31, "2SA": 24,
    "1KI": 22, "2KI": 25, "1CH": 29, "2CH": 36, "EZR": 10,
    "NEH": 13, "EST": 10, "JOB": 42, "PSA": 150, "PRO": 31,
    "ECC": 12, "SNG": 8, "ISA": 66, "JER": 52, "LAM": 5,
    "EZK": 48, "DAN": 12, "HOS": 14, "JOL": 3, "AMO": 9,
    "OBA": 1, "JON": 4, "MIC": 7, "NAM": 3, "HAB": 3,
    "ZEP": 3, "HAG": 2, "ZEC": 14, "MAL": 4,
    "MAT": 28, "MRK": 16, "LUK": 24, "JHN": 21, "ACT": 28,
    "ROM": 16, "1CO": 16, "2CO": 13, "GAL": 6, "EPH": 6,
    "PHP": 4, "COL": 4, "1TH": 5, "2TH": 3, "1TI": 6, "2TI": 4,
    "TIT": 3, "PHM": 1, "HEB": 13, "JAS": 5, "1PE": 5, "2PE": 3,
    "1JN": 5, "2JN": 1, "3JN": 1, "JUD": 1, "REV": 22,
}

YOUVERSION_BOOKS = {
    "tpt": TPT_BOOKS,
    "niv": NIV_BOOKS,
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
TPT_BASE_URL = "https://www.bible.com/bible/{version_id}/{usfm}"
TPT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def _solve_pow(base: str, target: str) -> Optional[str]:
    """Solve Fastly's 2-character SHA-256 proof-of-work."""
    for c1 in string.ascii_letters + string.digits:
        for c2 in string.ascii_letters + string.digits:
            if hashlib.sha256((base + c1 + c2).encode("ascii")).hexdigest() == target:
                return c1 + c2
    return None


def _solve_fastly_challenge(session: "requests.Session", page_html: str) -> bool:
    """Solve a Fastly Client Challenge page for this session.
    Returns True if the challenge was solved (a follow-up request should succeed).
    """
    marker = "script.js?reload=true"
    i = page_html.find(marker)
    if i < 0:
        return False
    dir_slash = page_html.rfind("/", 0, page_html.rfind("/", 0, i))
    script_path = page_html[dir_slash:i + len(marker)]
    prefix = "/" + script_path.split("/", 2)[1]
    script_resp = session.get("https://www.bible.com" + script_path, headers={"Referer": "https://www.bible.com/"}, timeout=30)
    script_resp.raise_for_status()
    m2 = re.search(r'init\(\[[^]]*?\],\s*"([^"]+)"', script_resp.text, re.DOTALL)
    if not m2:
        return False
    token = m2.group(1)
    m3 = re.search(r'init\((\[[^]]*?\]),\s*"', script_resp.text, re.DOTALL)
    if not m3:
        return False
    try:
        challenges = json.loads(m3.group(1))
    except ValueError:
        return False
    data = []
    for ch in challenges:
        if ch.get("ty") != "pow":
            return False
        d = ch["data"]
        answer = _solve_pow(d["base"], d["hash"])
        if not answer:
            return False
        data.append({
            "ty": "pow",
            "base": d["base"],
            "answer": answer,
            "hmac": d["hmac"],
            "expires": d["expires"],
        })
    resp = session.post(
        "https://www.bible.com" + prefix + "/fst-post-back",
        json={"token": token, "data": data},
        timeout=30,
    )
    resp.raise_for_status()
    return True


def _youversion_get(session: "requests.Session", url: str) -> "requests.Response":
    """GET a bible.com URL, solving the Fastly Client Challenge if served."""
    resp = session.get(url, timeout=30)
    if b"Client Challenge" in resp.content[:4000]:
        if not _solve_fastly_challenge(session, resp.text):
            raise ValueError("Unable to solve bible.com client challenge")
        time.sleep(1)
        resp = session.get(url, timeout=30)
    return resp


def _parse_youversion_chapter(html: str) -> dict:
    """Parse verse text from bible.com chapter page HTML (server-rendered).

    Verses are <span> elements with a data-usfm attribute like "GEN.1.1",
    containing label, content, and note child spans. Note text is excluded.
    """
    soup = BeautifulSoup(html, "html.parser")
    verses: dict[str, list[str]] = {}
    for verse_span in soup.find_all("span", class_=re.compile(r"__verse")):
        usfm = verse_span.get("data-usfm", "")
        if not usfm:
            continue
        parts = []
        for content in verse_span.find_all("span", class_=re.compile(r"__content")):
            if content.find_parent("span", class_=re.compile(r"__note")):
                continue
            text = content.get_text()
            if text:
                parts.append(text)
        full_text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if not full_text:
            continue
        vnum = usfm.split(".")[-1]
        verses.setdefault(vnum, []).append(full_text)
    return {vnum: " ".join(parts) for vnum, parts in verses.items()}


def download_youversion(version_id: str, books: dict, bible_name: str) -> Optional[str]:
    """Download a Bible version from YouVersion bible.com.
    Returns XML string in OpenSong format.
    """
    all_books = {}
    session = requests.Session()
    session.headers.update({"User-Agent": TPT_USER_AGENT})
    failed: list[str] = []

    for usfm_code, chapters in books.items():
        book_verses = {}
        for ch in range(1, chapters + 1):
            url = TPT_BASE_URL.format(version_id=version_id, usfm=f"{usfm_code}.{ch}")
            verses = None
            for attempt in range(3):
                try:
                    resp = _youversion_get(session, url)
                    resp.raise_for_status()
                    verses = _parse_youversion_chapter(resp.text)
                except Exception:
                    pass
                if verses:
                    break
                time.sleep(2)
            if verses:
                book_verses[str(ch)] = verses
            else:
                failed.append(f"{usfm_code}.{ch}")
            time.sleep(0.3)
        if book_verses:
            all_books[usfm_code] = book_verses

    if failed:
        print(f"  Warning: {len(failed)} chapters failed: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")

    if not all_books:
        return None

    # Convert to OpenSong XML
    from .converter import book_alias_to_name
    books_data = {}
    for usfm_code, chapters in all_books.items():
        bname = book_alias_to_name(usfm_code)
        if bname:
            books_data[bname] = chapters

    if not books_data:
        return None

    root = ET.Element("bible", {"name": bible_name})
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

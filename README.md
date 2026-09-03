# Bible Translation Maker

A Python package to **find Bible verses and get Bible verses** — 98 translations across 39 languages, with an offline catalog and on-demand downloads.

Build an API server, a local GUI, or a terminal UI on top of one shared library:

```python
import btm

print(btm.get_verse("John 3:16").text)
print(btm.get_passage("Ps 23:1-3", translation="LSG").text)   # French Louis Segond
print(btm.get_verse("John 3:16", translation="KOUGO").text)   # Japanese Colloquial

for hit in btm.find("everlasting", translation="KJV", limit=5):
    print(hit.reference, "-", hit.text)
```

## Installation

Requires Python 3.10+.

```bash
pip install bible-translation-maker
```

From source:

```bash
git clone https://github.com/Jemo69/bible-translation-maker.git
cd bible-translation-maker
pip install -e ".[dev]"  # or: uv sync
```

## Library usage

```python
import btm

# One-shot lookups (first call downloads + caches the translation)
verse = btm.get_verse("John 3:16-17")          # first verse of the range
passage = btm.get_passage("1 Cor 13:4-7", translation="WEB")
chapter = btm.get_chapter("Genesis", 1, translation="LUT1912")
hits = btm.find("shepherd", translation="KJV", limit=10)  # btm.search works too

# Hold a translation open for repeated queries (best for servers)
bible = btm.load("KJV")
bible.get_verse("John", 3, 16).text
bible.search("grace", books=["Romans", "Ephesians"])

# Browse the catalog offline — no network needed
btm.find_translations("japanese")              # KOUGO, SHINKAI, JFB
btm.find_translations(language="Korean")
btm.list_translations(include_copyrighted=False)
```

References accept full names and abbreviations (`"Gen 1:1"`, `"Ps 23"`, `"1 Cor 13:4-7"`, `"Jude"`).

### Where data lives

Downloads are cached as OpenSong XML in `~/.local/share/bible-translation-maker`
(override with the `BTM_DATA_DIR` env var or `btm.load("KJV", data_dir=...)`).
Any device with this package regenerates the same files on first use — the
`output/` directory is just a local cache and is not part of the repo.

## CLI usage

```bash
btm list                       # freely available translations
btm list --all                 # include copyrighted stubs
btm search japanese            # local catalog + eBible.org
btm get "John 3:16" -t KJV     # look up a passage (downloads on first use)
btm find love -t WEB --limit 5 # search verse text
btm download KJV -o ./output   # fetch + convert one translation
btm batch --ids KJV,WEB,LSG    # fetch several at once
```

## Translations

98 entries across 39 languages, including:

| Language | Translations |
|---|---|
| English | KJV, WEB, ASV, BBE, DARBY, DRA, YLT, OEB-US/CW, WEBBE, BSB, FBV, LSV, GNV, NET, RV, WMB, ULB, T4T, Webster, JPS, Brenton, NIV*, TPT*, + stubs (ESV, NLT, NKJV, CSB, NASB, NRSV) |
| Spanish | Reina Valera 1909/1602/Gómez, BES, PDDPT, VBL, BLL |
| German | Luther 1912, Elberfelder |
| French | Ostervald, Louis Segond 1910, FOB, Darby |
| Portuguese | Almeida, Bíblia Livre, BPM |
| Russian | Synodal |
| Chinese | CUV Traditional/Simplified, CUV-89 Simplified/Traditional |
| Japanese | Colloquial (口語訳), Shinkaiyaku 1965 NT, Freedom Bible |
| Korean | Korean Revised Version |
| Italian | Riveduta 1927, Diodati 1885 |
| Dutch | Statenvertaling, 1917 |
| Arabic | Van Dyke |
| Hindi | IRV Hindi |
| Greek | Byzantine Majority NT, SBLGNT, Septuagint |
| Hebrew | Westminster Leningrad Codex, Modern Hebrew |
| Latin | Clementine Vulgate |
| Others | Finnish, Swedish, Norwegian, Danish, Polish (Gdańska, UBG), Czech (Kralická), Hungarian (Károli), Croatian, Latvian, Albanian, Romanian, Ukrainian (Kulish), Bulgarian, Swahili, Tagalog, Vietnamese, Thai (x2), Turkish (x2), Indonesian, Māori, Cherokee, Patep |

Sources: [open-bibles](https://github.com/seven1m/open-bibles) (OSIS/Zefania/USFX),
[eBible.org](https://ebible.org) (USFX, all entries marked redistributable there),
[bible.com](https://bible.com) (`*` personal-use scraping).

Need one of the 1,500+ eBible.org translations not listed here? Every catalog
entry follows the same `https://eBible.org/Scriptures/{id}_usfx.zip` pattern:

```python
from btm.library import Library
from btm.bible import Bible
import requests, zipfile, io
from btm import converter

tid = "swhonen"  # any eBible.org translationId
raw = requests.get(f"https://eBible.org/Scriptures/{tid}_usfx.zip", timeout=120).content
name = [n for n in zipfile.ZipFile(io.BytesIO(raw)).namelist() if n.endswith("_usfx.xml")][0]
xml = zipfile.ZipFile(io.BytesIO(raw)).read(name).decode("utf-8")
bible = Bible.from_opensong_xml(converter.convert_to_opensong(xml, "usfx"), translation=tid)
print(bible.get_verse("John", 3, 16).text)
```

## License

Code is MIT (see `LICENSE`). Bible *texts* belong to their respective
copyright holders — see each translation's `copyright` field and respect its
terms. NIV/TPT downloads via bible.com are for personal use only;
ESV/NLT/NKJV/CSB/NASB/NRSV ship as stub files only.

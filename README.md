# bible_translation_finder

A versatile Python library and CLI tool to **look up scriptures, search verse texts, and download/convert Bible translations as OpenSong XML** files ready to drop into [FreeShow](https://freeshow.app), [OpenSong](https://opensong.org), and other lyrics-presentation software.

```bash
pip install bible_translation_finder
```

You can import either `btf` or `btm`:
```python
import btf  # or: import btm
```

---

## Table of Contents

- [Installation](#installation)
- [Using as a Python Library (For Apps)](#using-as-a-python-library-for-apps)
  - [1. Verse and Passage Lookups](#1-verse-and-passage-lookups)
  - [2. Full-Text Scripture Search](#2-full-text-scripture-search)
  - [3. Downloading OpenSong XML for Presentation Apps](#3-downloading-opensong-xml-for-presentation-apps)
  - [4. In-Memory XML Streaming (No Disk Writes)](#4-in-memory-xml-streaming-no-disk-writes)
  - [5. Exporting and Saving `Bible` Objects](#5-exporting-and-saving-bible-objects)
  - [6. Managing Collections with `Library`](#6-managing-collections-with-library)
  - [7. Catalog Discovery & Online eBible.org Search](#7-catalog-discovery--online-ebibleorg-search)
  - [8. Web API / FastAPI Example](#8-web-api--fastapi-example)
- [Using as a CLI (`btm`)](#using-as-a-cli-btm)
  - [Command Reference](#command-reference)
  - [Practical CLI Recipes](#practical-cli-recipes)
  - [Configuration & Environment Variables](#configuration--environment-variables)
- [Curated Catalog (98 Translations, 39 Languages)](#curated-catalog-98-translations-39-languages)
- [OpenSong XML Format](#opensong-xml-format)
- [License](#license)

---

## Installation

From PyPI:
```bash
pip install bible_translation_finder
```

From source:
```bash
git clone https://github.com/Jemo69/bible_translation_finder.git
cd bible_translation_finder
pip install -e ".[dev]"      # or: uv sync
```

Requires Python 3.10+.

---

## Using as a Python Library (For Apps)

Both `import btf` and `import btm` are supported and provide identical interfaces.

### 1. Verse and Passage Lookups

Fetch single verses, verse ranges, or whole chapters. If a translation has not been downloaded yet, it will automatically download and cache it locally on first use:

```python
import btf

# Look up a single verse
v = btf.get_verse("John 3:16", translation="KJV")
print(v.reference)    # "John 3:16"
print(v.text)         # "For God so loved the world..."
print(v.translation)  # "KJV"

# Look up a passage or range
passage = btf.get_passage("Ps 23:1-3", translation="WEB")
print(f"{passage.reference} ({passage.translation}):")
for verse in passage.verses:
    print(f"  {verse.verse} {verse.text}")

# Look up an entire chapter
ch = btf.get_chapter("Genesis", 1, translation="KJV")
print(f"Genesis 1 contains {len(ch)} verses.")
```

Supported reference formats include standard book names and common abbreviations (e.g. `"John 3:16"`, `"1 Cor 13:4-7"`, `"Ps 23"`, `"Gen 1:1"`, `"Jude"`).

### 2. Full-Text Scripture Search

Perform fast substring searches across any loaded Bible translation:

```python
import btf

# Search for verses containing a phrase
hits = btf.find("shepherd", translation="KJV", limit=5)
for hit in hits:
    print(f"{hit.reference}: {hit.text}")

# Limit search to specific books or toggle case sensitivity
bible = btf.load("WEB")
prophets_hits = bible.search("righteousness", books=["Isaiah", "Jeremiah"], limit=10)
```

### 3. Downloading OpenSong XML for Presentation Apps

Download full Bibles converted to OpenSong XML directly into your app's scripture directory (e.g., FreeShow, OpenSong):

```python
import btf

# Download a single translation to a directory
xml_path = btf.download("KJV", output_dir="./bibles")
print(f"Wrote XML to: {xml_path}")

# Download several translations at once
btf.batch(["KJV", "WEB", "LSG", "KOUGO"], output_dir="./bibles")

# Download ALL freely available translations in the catalog (70+ bibles)
btf.batch(output_dir="./bibles")
```

### 4. In-Memory XML Streaming (No Disk Writes)

If your app generates responses dynamically or pipes XML into an API without touching the filesystem, use `fetch_xml()`:

```python
import btf

# Returns the complete OpenSong XML as a string
xml_data = btf.fetch_xml("KJV")
print(xml_data[:120])  # '<?xml version="1.0" encoding="UTF-8"?>\n<bible><b n="1" name="Genesis">...'
```

### 5. Exporting and Saving `Bible` Objects

You can inspect, mutate, or serialize loaded `Bible` instances back to OpenSong XML:

```python
import btf

bible = btf.load("WEB")

# Export to XML string
xml_str = bible.to_opensong_xml()

# Save to any file path
bible.save("/path/to/custom_web.xml")
```

### 6. Managing Collections with `Library`

The `Library` class manages a local storage directory (`~/.local/share/bible-translation-finder` by default):

```python
import btf

# Initialize with default or custom storage path
lib = btf.Library(data_dir="./custom_storage")

# Check what is already downloaded
print("Cached:", [t["abbreviation"] for t in lib.downloaded()])
if lib.is_downloaded("KJV"):
    print("KJV XML path:", lib.file_for("KJV"))

# Query via the library instance
verse = lib.get_verse("Romans 8:28", translation="KJV")
print(verse)

# Batch download into the managed directory
lib.batch(["WEB", "ASV", "BBE"])
```

Top-level convenience equivalents are also available:
```python
import btf

print(btf.downloaded())
print(btf.is_downloaded("KJV"))
print(btf.file_for("KJV"))
```

### 7. Catalog Discovery & Online eBible.org Search

Browse translations offline by language or search the 1,500+ digital Bibles hosted on eBible.org:

```python
import btf

# Browse curated local catalog (offline)
japanese_bibles = btf.find_translations("japanese")
korean_bibles   = btf.find_translations(language="Korean")

# List all 39 supported languages
languages = btf.list_languages()

# Search the live eBible.org catalog (1,500+ translations)
ebible_results = btf.search_ebible("swahili")

# Unified search across local catalog and eBible.org
all_results = btf.search_translations("spanish", include_ebible=True)
```

### 8. Web API / FastAPI Example

Integrating `bible_translation_finder` into an API server (e.g. FastAPI):

```python
from fastapi import FastAPI, HTTPException
import btf

app = FastAPI(title="Scripture API")

@app.get("/verse")
def read_verse(ref: str, trans: str = "KJV"):
    try:
        v = btf.get_verse(ref, translation=trans)
        return {"reference": v.reference, "text": v.text, "translation": v.translation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/passage")
def read_passage(ref: str, trans: str = "KJV"):
    try:
        p = btf.get_passage(ref, translation=trans)
        return {
            "reference": p.reference,
            "translation": p.translation,
            "verses": [{"verse": v.verse, "text": v.text} for v in p.verses],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download-xml/{trans_id}")
def export_xml(trans_id: str):
    try:
        xml_content = btf.fetch_xml(trans_id)
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

## Using as a CLI (`btm`)

When installed, the package provides the `btm` executable.

### Command Reference

| Command | Usage | Description |
|---|---|---|
| `btm get` | `btm get "<ref>" [-t <trans>]` | Look up a single verse or passage |
| `btm find` | `btm find "<query>" [-t <trans>] [--limit <n>]` | Search verse text in a translation |
| `btm list` | `btm list [--all]` | Display formatted table of available translations |
| `btm search`| `btm search "<query>"` | Search local catalog and live eBible.org |
| `btm download`| `btm download <id> [-o <dir>] [--force]` | Download & convert a translation to OpenSong XML |
| `btm batch` | `btm batch [--ids <ids>] [-o <dir>] [--force]` | Download multiple translations (defaults to all free) |
| `btm downloaded`| `btm downloaded` | List translations currently cached in the data dir |

### Practical CLI Recipes

#### 1. Look up verses from the terminal
```bash
# Get a single verse (defaults to KJV)
btm get "John 3:16"

# Get a passage from another translation
btm get "Ps 23:1-3" -t WEB
btm get "1 Cor 13:4-8" -t LSG
```

#### 2. Search scriptures
```bash
btm find "shepherd" -t KJV --limit 5
btm find "everlasting life" -t WEB
```

#### 3. Setup FreeShow or OpenSong with one command
Point the output directory straight to your software's Bibles directory:
```bash
# Download 3 translations into your FreeShow scriptures folder
btm batch --ids KJV,WEB,LSG -o ~/Documents/FreeShow/Bibles

# Or download all 70+ freely redistributable translations at once
btm batch -o ./bibles
```

#### 4. Search and browse translations
```bash
# List all freely available translations
btm list

# List all 98 catalog translations, including copyrighted stubs
btm list --all

# Search local catalog and query eBible.org
btm search "tagalog"
```

#### 5. Check what is cached
```bash
btm downloaded
```

### Configuration & Environment Variables

- **`--data-dir <path>`**: Override the storage cache location for any command:
  ```bash
  btm --data-dir /tmp/my_bibles download KJV
  ```
- **`BTM_DATA_DIR`**: Set an environment variable to persistently change the default cache directory:
  ```bash
  export BTM_DATA_DIR="$HOME/my_bibles"
  ```

---

## Curated Catalog (98 Translations, 39 Languages)

Curated entries include:

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
| Others | Finnish, Swedish, Norwegian, Danish, Polish (Gdańska, UBG), Czech (Kralická), Hungarian (Károli), Croatian, Latvian, Albanian, Romanian, Ukrainian (Kulish), Bulgarian, Swahili, Tagalog, Vietnamese, Thai (×2), Turkish (×2), Indonesian, Māori, Cherokee, Patep |

Sources: [open-bibles](https://github.com/seven1m/open-bibles) (OSIS/Zefania/USFX),
[eBible.org](https://ebible.org) (USFX), [bible.com](https://bible.com) (`*` personal-use scraping).

---

## OpenSong XML Format

Files generated by this package follow the standard OpenSong Bible structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bible>
  <b n="1" name="Genesis">
    <c n="1">
      <v n="1">In the beginning God created the heaven and the earth.</v>
      <v n="2">And the earth was without form, and void...</v>
    </c>
  </b>
</bible>
```

- Each book includes the canonical index (`n`) and standard name (`name`).
- Cleaned of footnotes and cross-reference markup for presentation use.
- Chapters and verse numbers are numerical and sorted in canonical order.

---

## License

Code is licensed under the [MIT License](LICENSE). Bible *texts* belong to their respective copyright holders — see each translation's `copyright` field and respect its terms. NIV and TPT downloads via bible.com are for personal use only; ESV, NLT, NKJV, CSB, NASB, NRSV ship as stub files only.


# bible_translation_finder

A Python package to **download Bible translations as OpenSong XML** files that you can drop into [FreeShow](https://freeshow.app), [OpenSong](https://opensong.org), and other lyrics-display software.

```bash
pip install bible_translation_finder
```

```python
import btf

# List the 98 translations in the curated catalog
btf.list_translations()                         # freely available
btf.list_translations(include_copyrighted=True) # all 98

# Browse offline (no network)
btf.find_translations("japanese")                # KOUGO, SHINKAI, JFB
btf.find_translations(language="Korean")

# Download one translation into a directory
btf.download("KJV", output_dir="./bibles")       # /bibles/kjv_eng_kjv.xml
btf.download("KOUGO", output_dir="./bibles")     # Japanese Colloquial
btf.download("LSG", output_dir="./bibles")       # Louis Segond 1910

# Download many at once
btf.batch(["KJV", "WEB", "LSG", "KOUGO"], output_dir="./bibles")

# Or use a managed data directory
lib = btf.Library()                             # ~/.local/share/bible-translation-finder
lib.download("KJV")
print(lib.file_for("KJV"))                      # cached OpenSong XML path
print([t["abbreviation"] for t in lib.downloaded()])
```

The resulting XML is OpenSong `<bible><b><c><v>` format — load it into FreeShow, OpenSong, or any other Bible-aware lyrics app.

## Installation

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

## CLI

```bash
btm list                          # freely available translations
btm list --all                    # include copyrighted stubs
btm search japanese               # local catalog + eBible.org
btm download KJV -o ./bibles      # fetch + convert one translation
btm batch --ids KJV,WEB,LSG -o ./bibles
btm batch -o ./bibles             # every freely available translation
btm downloaded                    # what's already in the data dir
btm --data-dir /path/to/dir ...   # override the cache directory
```

## Translations

98 curated entries across 39 languages, including:

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
[eBible.org](https://ebible.org) (USFX; all entries marked redistributable there),
[bible.com](https://bible.com) (`*` personal-use scraping).

Need one of the 1,500+ eBible.org translations not listed here? Every catalog
entry follows the same `https://eBible.org/Scriptures/{id}_usfx.zip` pattern —
the `Library` is just a thin wrapper around `_scraper.download_ebible_usfx` and
`convert_to_opensong`, so any translation can be fetched the same way.

## License

Code is MIT (see `LICENSE`). Bible *texts* belong to their respective copyright
holders — see each translation's `copyright` field and respect its terms. NIV
and TPT downloads via bible.com are for personal use only; ESV, NLT, NKJV, CSB,
NASB, NRSV ship as stub files only.

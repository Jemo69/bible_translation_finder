First release as a Python package: `pip install bible_translation_finder`

**Library API** — `import btm` in any API server, GUI, or TUI:
- `btm.get_verse("John 3:16")`, `get_passage("Ps 23:1-3")`, `get_chapter("Genesis", 1)`, `find("grace", limit=10)`
- `Bible`, `Passage`, `Verse`, `Reference`, `Library` classes; translations download on first use and cache locally

**Translations: ~30 → 98 entries, 39 languages** — incl. Japanese Colloquial, Shinkaiyaku 1965 NT, Freedom Bible, Korean RV, CUV simp/trad, Louis Segond 1910, Elberfelder, Reina Valera Gómez, Diodati 1885, Van Dyke Arabic, Hindi IRV, Greek/Hebrew/Latin sources, plus BSB, FBV, LSV, NET, ULB and more in English

**Fixes** — implemented the missing USFX converter (most downloads were broken), OSIS duplicate-text bug, Psalm alias, `btm` entry point

**CLI** — new `btm get` / `btm find`; kept `list`, `search`, `download`, `batch`

Note: Bible texts belong to their holders — NIV/TPT personal-use only; ESV/NLT/NKJV/CSB/NASB/NRSV ship as stubs.

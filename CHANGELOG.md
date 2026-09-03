# Changelog

## v0.2.0

First release as a Python package. `pip install bible-translation-maker`,
then `import btm` in an API server, GUI, or TUI.

### Library API (new)

- `btm.get_verse("John 3:16")`, `get_passage("Ps 23:1-3")`,
  `get_chapter("Genesis", 1)`, `find("grace", limit=10)` (`search` alias)
- `Bible`, `Passage`, `Verse`, `Reference`, and `Library` classes
- Reference parsing: full names and abbreviations, ranges (`1 Cor 13:4-7`),
  whole chapters (`Ps 23`) and books (`Jude`)
- Translations download on first use into `~/.local/share/bible-translation-maker`
  (override with `BTM_DATA_DIR`), then load from local cache

### Translations: ~30 → 98 entries, 39 languages

- English: + BSB, FBV, LSV, Geneva 1599, NET, RV 1895, WMB, ULB, T4T,
  Webster, JPS Tanakh, Brenton Septuagint, KJV Cambridge Paragraph Bible
- Japanese: Colloquial (口語訳), Shinkaiyaku 1965 NT, Freedom Bible
- Plus Korean, Chinese (Simplified/Traditional, CUV-89), Louis Segond 1910,
  Elberfelder, Reina Valera Gómez, Diodati 1885, Van Dyke Arabic, Hindi IRV,
  Greek (Byzantine/SBL/LXX), Hebrew (WLC/Modern), Vulgate, and more across
  Europe, Africa, and Asia

### Fixes

- Implemented the missing USFX converter (most downloads were broken)
- Fixed OSIS verse text being duplicated, `Psalm` singular alias dropping
  a whole book, BOM handling, and the `btm` entry point

### CLI

- New: `btm get "John 3:16" -t KJV`, `btm find love -t WEB`
- Kept: `list`, `search`, `download`, `batch`

### Notes

- Bible texts belong to their holders; NIV/TPT are personal-use only,
  ESV/NLT/NKJV/CSB/NASB/NRSV ship as stubs.
- `output/` is a regenerable local cache and is no longer tracked in git.

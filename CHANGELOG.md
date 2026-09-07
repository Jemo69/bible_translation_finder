# Changelog

## v0.3.0

Brings together full Scripture querying/lookup capabilities with the OpenSong XML download and conversion pipeline.

- **Restored verse lookup & query API**: `get_verse()`, `get_passage()`, `get_chapter()`, `load()`, and domain classes (`Bible`, `Passage`, `Verse`, `Reference`).
- **Restored full-text search**: `find()` / `search()`.
- **Restored CLI query commands**: `btm get <ref>` and `btm find <query>`.
- **OpenSong XML export & download**: `download()`, `batch()`, `fetch_xml()`, `Bible.to_opensong_xml()`, `Bible.save()`, and CLI `btm download` / `btm batch` / `btm downloaded`.
- **Dual module support**: Both `import btf` and `import btm` are supported.
- **USFX converter fix**: Handles direct book children without `<p>` wrappers (e.g. Cherokee New Testament).


## v0.2.0

First release as a Python package. `pip install bible_translation_finder`.

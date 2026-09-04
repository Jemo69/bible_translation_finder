# Changelog

## v0.3.0

Tightened the package to its real purpose: downloading and converting Bible
translations to OpenSong XML. The earlier verse-lookup and search helpers
(`btm.get_verse`, `btm.find`, `Bible`/`Passage`/`Verse`/`Reference`) are gone.

- New top-level API: `btf.download(id, output_dir=...)`, `btf.batch(ids, ...)`,
  `btf.Library`, `btf.list_translations`, `btf.find_translations`
- New CLI: `btm download`, `btm batch`, `btm downloaded`, plus a
  `--data-dir` global flag and a `download` subcommand that defaults to the
  current directory (so you can pipe straight into your FreeShow folder)
- `batch` with no `--ids` now downloads every freely available translation

## v0.2.0

First release as a Python package. `pip install bible_translation_finder`.

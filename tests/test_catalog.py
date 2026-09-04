import xml.etree.ElementTree as ET

from btm import catalog, converter, library


def test_catalog_size():
    assert len(catalog.get_catalog()) >= 80


def test_no_duplicate_ids_or_abbrevs():
    entries = catalog.get_catalog()
    ids = [t["id"] for t in entries]
    abbrevs = [t["abbreviation"].lower() for t in entries]
    assert len(ids) == len(set(ids)), "duplicate translation ids"
    assert len(abbrevs) == len(set(abbrevs)), "duplicate abbreviations"


def test_required_keys():
    required = {
        "id", "abbreviation", "name", "language", "language_code",
        "copyright", "freely_available", "source_url", "source_format",
        "source_type", "popularity_rank",
    }
    for t in catalog.get_catalog():
        assert required <= set(t.keys()), f"{t.get('id')} missing keys"


def test_free_entries_have_source():
    for t in catalog.get_freely_available():
        assert t["source_type"] in ("open-bibles", "ebible", "youversion"), t["id"]
        if t["source_type"] in ("open-bibles", "ebible"):
            assert t["source_url"], t["id"]
            assert t["source_format"] in ("osis", "usfx", "zefania"), t["id"]


def test_ebible_urls_wellformed():
    for t in catalog.get_catalog():
        if t["source_type"] == "ebible" and t["source_url"]:
            assert t["source_url"].startswith("https://eBible.org/Scriptures/"), t["id"]
            assert t["source_url"].endswith("_usfx.zip"), t["id"]


def test_japanese_coverage():
    abbrs = {t["abbreviation"] for t in catalog.search_catalog("", language="Japanese")}
    assert {"KOUGO", "SHINKAI", "JFB"} <= abbrs


def test_major_languages_present():
    langs = set(catalog.list_languages())
    for expected in [
        "English", "Spanish", "German", "French", "Portuguese", "Russian",
        "Chinese (Traditional)", "Chinese (Simplified)", "Japanese", "Korean",
        "Italian", "Dutch", "Arabic", "Hindi", "Greek (Koine)", "Hebrew", "Latin",
    ]:
        assert expected in langs, f"missing language {expected}"


def test_lookup_helpers():
    assert catalog.get_translation("eng-kjv")["abbreviation"] == "KJV"
    assert catalog.get_by_abbreviation("kjv")["id"] == "eng-kjv"
    assert catalog.get_by_abbreviation("KOUGO")["language"] == "Japanese"
    assert catalog.get_by_abbreviation("nope") is None


def test_search_catalog_offline():
    hits = catalog.search_catalog("luther")
    assert any(t["abbreviation"] == "LUT1912" for t in hits)
    hits = catalog.search_catalog("", language="Korean")
    assert len(hits) >= 1


def test_library_lists_downloaded(tmp_path):
    lib = library.Library(tmp_path)
    lib.download("KJV", overwrite=True)
    assert lib.is_downloaded("KJV")
    assert any(t["abbreviation"] == "KJV" for t in lib.downloaded())


def test_library_download_stub_for_copyrighted(tmp_path):
    lib = library.Library(tmp_path)
    path = lib.download("ESV")  # ESV has no free source → stub
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "[Placeholder" in text
    assert "ESV" in text


def test_download_to_specific_output_dir(tmp_path):
    out = tmp_path / "out"
    path = library.download("KJV", output_dir=out, overwrite=True)
    assert path.exists()
    assert path.parent == out

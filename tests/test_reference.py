import pytest

from btm.reference import Reference, normalize_book_name, parse_reference


def test_normalize_full_names():
    assert normalize_book_name("Genesis") == "Genesis"
    assert normalize_book_name("  psalms ") == "Psalms"
    assert normalize_book_name("Song of Solomon") == "Song of Solomon"


def test_normalize_abbreviations():
    assert normalize_book_name("Gen") == "Genesis"
    assert normalize_book_name("gen") == "Genesis"
    assert normalize_book_name("Ps") == "Psalms"
    assert normalize_book_name("1 Cor") == "1 Corinthians"
    assert normalize_book_name("1cor") == "1 Corinthians"
    assert normalize_book_name("Jn") == "John"
    assert normalize_book_name("Rev") == "Revelation"
    assert normalize_book_name("JHN") == "John"  # USFM code
    assert normalize_book_name("Psalm") == "Psalms"  # singular variant


def test_unknown_book():
    with pytest.raises(ValueError):
        normalize_book_name("Hezekiah")


def test_parse_single_verse():
    r = parse_reference("John 3:16")
    assert r == Reference(book="John", chapter=3, verse_start=16, verse_end=16)
    assert str(r) == "John 3:16"


def test_parse_abbrev():
    r = parse_reference("gen 1:1")
    assert r.book == "Genesis" and r.chapter == 1 and r.verse_start == 1


def test_parse_range():
    r = parse_reference("1 Cor 13:4-7")
    assert (r.book, r.chapter, r.verse_start, r.verse_end) == ("1 Corinthians", 13, 4, 7)
    assert str(r) == "1 Corinthians 13:4-7"


def test_parse_en_dash_range():
    r = parse_reference("Ps 23:1–3")
    assert (r.book, r.chapter, r.verse_start, r.verse_end) == ("Psalms", 23, 1, 3)


def test_parse_whole_chapter():
    r = parse_reference("Ps 23")
    assert r.book == "Psalms" and r.chapter == 23 and r.verse_start is None
    assert r.is_whole_chapter
    assert str(r) == "Psalms 23"


def test_parse_whole_book():
    r = parse_reference("Jude")
    assert r.book == "Jude" and r.chapter is None
    assert r.is_whole_book


def test_parse_numbered_book():
    r = parse_reference("2 John 1:3")
    assert r.book == "2 John"


def test_invalid():
    with pytest.raises(ValueError):
        parse_reference("")
    with pytest.raises(ValueError):
        parse_reference("John 3:18-16")  # reversed range
    with pytest.raises(ValueError):
        parse_reference("not a reference 999")

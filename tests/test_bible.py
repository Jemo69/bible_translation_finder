"""Tests for the Bible query API using a small synthetic OpenSong file."""

import pytest

from btm.bible import Bible

SAMPLE_XML = """<bible>
  <b n="1" name="Genesis">
    <c n="1">
      <v n="1">In the beginning God created the heaven and the earth.</v>
      <v n="2">And the earth was without form, and void.</v>
    </c>
    <c n="2">
      <v n="1">Thus the heavens and the earth were finished.</v>
    </c>
  </b>
  <b n="19" name="Psalms">
    <c n="23">
      <v n="1">The LORD is my shepherd; I shall not want.</v>
      <v n="2">He maketh me to lie down in green pastures.</v>
    </c>
  </b>
  <b n="43" name="John">
    <c n="3">
      <v n="16">For God so loved the world, that he gave his only begotten Son.</v>
      <v n="17">For God sent not his Son into the world to condemn the world.</v>
    </c>
  </b>
</bible>"""

# Legacy style: book name in `n`, no `name` attribute (as in output/*.xml).
LEGACY_XML = """<bible>
  <b n="Genesis">
    <c n="1">
      <v n="1">In the beginning God created the heaven and the earth.</v>
    </c>
  </b>
</bible>"""


@pytest.fixture()
def bible():
    return Bible.from_opensong_xml(SAMPLE_XML, translation="TEST")


def test_book_names(bible):
    assert bible.book_names == ["Genesis", "Psalms", "John"]


def test_get_verse(bible):
    v = bible.get_verse("John", 3, 16)
    assert v.text.startswith("For God so loved")
    assert v.reference == "John 3:16"
    assert v.translation == "TEST"


def test_get_verse_by_abbrev(bible):
    assert bible.get_verse("Gen", 1, 1).text.startswith("In the beginning")
    assert bible.get_verse("Ps", 23, 1).text.startswith("The LORD is my shepherd")


def test_get_verse_missing(bible):
    with pytest.raises(KeyError):
        bible.get_verse("John", 3, 99)
    with pytest.raises(KeyError):
        bible.get_verse("Jude", 1, 1)


def test_get_passage_range(bible):
    p = bible.get_passage("John 3:16-17")
    assert len(p) == 2
    assert "begotten Son" in p.verses[0].text
    assert p.reference == "John 3:16-17"


def test_get_passage_chapter(bible):
    p = bible.get_passage("Ps 23")
    assert len(p) == 2
    assert "shepherd" in p.text


def test_get_chapter(bible):
    p = bible.get_chapter("Genesis", 1)
    assert len(p) == 2


def test_search(bible):
    hits = bible.search("shepherd")
    assert len(hits) == 1 and hits[0].reference == "Psalms 23:1"
    hits = bible.search("GOD", limit=10)  # case-insensitive by default
    assert len(hits) >= 2
    hits = bible.search("God", case_sensitive=True)
    assert all("God" in h.text for h in hits)


def test_search_limit(bible):
    hits = bible.search("the", limit=2)
    assert len(hits) == 2


def test_search_empty_query(bible):
    with pytest.raises(ValueError):
        bible.search("  ")


def test_contains(bible):
    assert "John 3:16" in bible
    assert "Jude 1:1" not in bible


def test_verse_count(bible):
    assert bible.verse_count() == 7
    assert len(bible) == 7


def test_legacy_book_attribute_style():
    b = Bible.from_opensong_xml(LEGACY_XML, translation="LEG")
    assert b.get_verse("Genesis", 1, 1).text.startswith("In the beginning")


def test_bad_xml():
    with pytest.raises(ValueError):
        Bible.from_opensong_xml("<notbible/>")
    with pytest.raises(ValueError):
        Bible.from_opensong_xml("<bible></bible>")  # no books

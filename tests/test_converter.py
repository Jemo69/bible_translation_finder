import xml.etree.ElementTree as ET

from btm import converter


def test_safe_sort_key():
    keys = ["10", "2", "1", "1-2", "3a"]
    assert sorted(keys, key=converter._safe_sort_key) == ["1", "1-2", "2", "3a", "10"]


def test_usfx_basic():
    usfx = """<?xml version="1.0" encoding="UTF-8"?>
<usfx><languageCode>eng</languageCode>
<book id="GEN"><c id="1"/><p><v id="1"/>In the beginning God created.<ve/>
<v id="2"/>And the earth was waste.<ve/></p></book>
<book id="FRT"><c id="1"/><p><v id="1"/>Front matter, skipped.<ve/></p></book>
</usfx>"""
    out = converter.convert_to_opensong(usfx, "usfx")
    assert out is not None
    root = ET.fromstring(out)
    books = root.findall("b")
    assert len(books) == 1 and books[0].get("name") == "Genesis"
    verses = books[0].findall("c")[0].findall("v")
    assert [v.get("n") for v in verses] == ["1", "2"]
    assert verses[0].text == "In the beginning God created."


def test_usfx_footnotes_excluded():
    usfx = """<usfx><book id="GEN"><c id="1"/><p><v id="1"/>God<f caller="+">Hebrew Elohim.</f> created.<ve/></p></book></usfx>"""
    out = converter.convert_to_opensong(usfx, "usfx")
    root = ET.fromstring(out)
    text = root.findall("b")[0].findall("c")[0].findall("v")[0].text
    assert text == "God created."
    assert "Elohim" not in text


def test_usfx_formatting_kept():
    usfx = """<usfx><book id="PSA"><c id="23"/><p><v id="1"/>The <nd>Lord</nd> is my <wj>shepherd</wj>.<ve/></p></book></usfx>"""
    out = converter.convert_to_opensong(usfx, "usfx")
    root = ET.fromstring(out)
    assert root.findall("b")[0].get("name") == "Psalms"
    text = root.findall("b")[0].findall("c")[0].findall("v")[0].text
    assert text == "The Lord is my shepherd."


def test_zefania_psalm_singular():
    zef = """<XMLBIBLE><BIBLEBOOK bnumber="19" bname="Psalm" bsname="Ps">
<CHAPTER cnumber="23"><VERS vnumber="1">The LORD is my shepherd.</VERS></CHAPTER>
</BIBLEBOOK></XMLBIBLE>"""
    out = converter.convert_to_opensong(zef, "zefania")
    root = ET.fromstring(out)
    assert root.findall("b")[0].get("name") == "Psalms"


def test_convert_to_opensong_bad_format():
    try:
        converter.convert_to_opensong("<x/>", "kjv")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_real_usfx_file():
    import pathlib

    p = pathlib.Path("/tmp/web.usfx.xml")
    if not p.exists():
        return
    out = converter.convert_to_opensong(p.read_text(encoding="utf-8"), "usfx")
    root = ET.fromstring(out)
    assert len(root.findall("b")) == 66

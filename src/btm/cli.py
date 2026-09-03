import os
import sys
from pathlib import Path
from typing import Optional

from . import catalog
from . import converter
from . import scraper


def format_table(rows: list[list[str]], headers: list[str]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    lines = []
    header = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header)
    lines.append("-+-".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(" | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def cmd_list(args):
    translations = catalog.get_catalog()
    if not getattr(args, "all", False):
        translations = [t for t in translations if t["freely_available"]]
    rows = []
    for t in sorted(translations, key=lambda x: x.get("popularity_rank", 99)):
        avail = "Yes" if t["freely_available"] else "No (copyrighted)"
        rows.append([
            t["abbreviation"],
            t["name"],
            t["language"],
            avail,
            t.get("source_format", "") or "",
        ])
    print(f"Found {len(rows)} translations in catalog:")
    print()
    print(format_table(rows, ["Abbrev", "Name", "Language", "Available", "Format"]))


def cmd_search(args):
    query = args.query
    # Offline catalog search first (fast, no network).
    local = catalog.search_catalog(query)
    if local:
        rows = [[t["abbreviation"], t["name"], t["language"]] for t in local[:30]]
        print(f"Found {len(local)} translations in the local catalog (showing up to 30):")
        print()
        print(format_table(rows, ["Abbrev", "Name", "Language"]))
        print()
    # Then the full eBible.org online catalog.
    try:
        results = scraper.search_ebible_catalog(query=query)
    except Exception as e:
        print(f"Online eBible.org search failed: {e}")
        print("Tip: every local result above can be fetched with 'btm download <Abbrev>'.")
        return
    rows = []
    for r in results[:50]:
        rows.append([r["id"], r["title"], r["language"], r["copyright"][:40]])
    if not rows:
        print("No further results on eBible.org.")
        return
    print(f"Found {len(results)} translations on eBible.org (showing up to 50):")
    print()
    print(format_table(rows, ["ID", "Title", "Language", "Copyright"]))


def cmd_get(args):
    """Print one passage: btm get "John 3:16" --translation KJV."""
    from .library import Library

    lib = Library(getattr(args, "data_dir", None) or None)
    try:
        bible = lib.load(args.translation)
    except KeyError as e:
        print(e)
        return
    except FileNotFoundError as e:
        print(e)
        return
    try:
        passage = bible.get_passage(args.reference)
    except (ValueError, KeyError) as e:
        print(f"Error: {e}")
        return
    print(f"{passage.reference} ({bible.translation})")
    for v in passage.verses:
        print(f"{v.verse} {v.text}")


def cmd_find(args):
    """Search verse texts: btm find love --translation WEB --limit 10."""
    from .library import Library

    lib = Library(getattr(args, "data_dir", None) or None)
    try:
        bible = lib.load(args.translation)
    except (KeyError, FileNotFoundError) as e:
        print(e)
        return
    try:
        hits = bible.search(args.query, limit=args.limit)
    except ValueError as e:
        print(f"Error: {e}")
        return
    if not hits:
        print("No matches found.")
        return
    print(f"Found {len(hits)} match(es) in {bible.translation}:")
    for v in hits:
        print(f"  {v.reference} — {v.text[:160]}")


def cmd_download(args):
    trans_id = args.translation_id
    output_dir = args.output or "output"

    t = catalog.get_translation(trans_id)
    if t is None:
        all_trans = catalog.get_catalog()
        for ct in all_trans:
            if ct["abbreviation"].lower() == trans_id.lower() or ct.get("id", "").lower() == trans_id.lower():
                t = ct
                break

    if t is None:
        print(f"Translation '{trans_id}' not found in catalog.")
        print("Use 'list' to see available translations or 'search' to find more.")
        return

    if not t["freely_available"]:
        print(f"Warning: {t['name']} ({t['abbreviation']}) is copyrighted.")
        print(f"Copyright: {t['copyright']}")
        print("Cannot automatically download copyrighted translations.")
        resp = input("Do you still want to create a stub file? (y/N): ")
        if resp.lower() != "y":
            return
        xml_content = None
    else:
        print(f"Downloading {t['name']} ({t['abbreviation']})...")
        xml_content = _download_translation(t)

    _output_opensong(t, xml_content, output_dir)


def cmd_batch(args):
    output_dir = args.output or "output"
    include_copyrighted = args.include_copyrighted or False

    translations = catalog.get_catalog()
    if include_copyrighted:
        targets = translations
    else:
        targets = [t for t in translations if t["freely_available"]]

    if args.ids:
        id_list = [x.strip().lower() for x in args.ids.split(",")]
        targets = [t for t in translations if t["abbreviation"].lower() in id_list or t["id"].lower() in id_list]

    for t in targets:
        print(f"\nProcessing {t['abbreviation']} - {t['name']}...")
        if not t["freely_available"]:
            print(f"  Skipping (copyrighted): {t['copyright']}")
            _output_opensong(t, None, output_dir)
            continue

        try:
            xml_content = _download_translation(t)
            _output_opensong(t, xml_content, output_dir)
        except Exception as e:
            print(f"  Error: {e}")


def _download_translation(t: dict) -> Optional[str]:
    source_type = t.get("source_type")
    source_url = t.get("source_url")
    source_format = t.get("source_format")

    if source_type == "youversion":
        version_id = t.get("youversion_id")
        books = scraper.YOUVERSION_BOOKS.get(t.get("youversion_books"))
        if not version_id or not books:
            raise ValueError(f"No YouVersion config for {t['abbreviation']}")
        print(f"  Downloading from YouVersion (bible.com)...")
        print(f"  {sum(books.values())} chapters, this takes several minutes...")
        opensong_xml = scraper.download_youversion(version_id, books, t["name"])
        return opensong_xml
    elif source_type == "open-bibles" and source_url:
        filename = source_url.rstrip("/").split("/")[-1]
        xml_content = scraper.download_open_bibles(filename)
    elif source_type == "ebible" and source_url:
        xml_content = scraper.download_ebible_usfx(source_url)
    else:
        raise ValueError(f"No download method for {t['abbreviation']}")

    if xml_content:
        print(f"  Converting to OpenSong format...")
        result = converter.convert_to_opensong(xml_content, source_format)
        return result
    return None


def _output_opensong(t: dict, opensong_xml: Optional[str], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{t['abbreviation'].lower()}_{t['id'].replace('-', '_')}.xml"
    filepath = os.path.join(output_dir, filename)

    if opensong_xml:
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        full_content = xml_declaration + opensong_xml
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"  Wrote: {filepath}")
    else:
        stub = _make_stub(t)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(stub)
        print(f"  Wrote stub: {filepath}  (contains placeholder only)")


def _make_stub(t: dict) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!--",
        f"  Translation: {t['name']} ({t['abbreviation']})",
        f"  Language: {t['language']}",
        f"  Copyright: {t['copyright']}",
        "",
        "  This is a STUB file. The full Bible text for this translation",
        "  is copyrighted and not freely redistributable.",
        "",
        "  To obtain this Bible translation, please contact the copyright holder",
        f"  or purchase a licensed copy from an authorized retailer.",
        "",
        "  For OpenSong format, you may be able to download from:",
        "  - https://opensong.org/downloads/",
        "  - https://freely-given.org/Software/BibleDropBox/Formats/OpenSongBibles.html",
        "-->",
        "<bible>",
    ]
    for book in converter.BIBLE_BOOKS:
        lines.append(f'  <b n="{book}">')
        lines.append(f'    <c n="1">')
        lines.append(f'      <v n="1">[Placeholder - {t["abbreviation"]} Bible text not included]</v>')
        lines.append(f'    </c>')
        lines.append(f'  </b>')
    lines.append("</bible>")
    return "\n".join(lines)


def run_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Bible Translation Maker - find Bible verses and convert translations to OpenSong XML"
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List available translations in the catalog")
    p_list.add_argument("--all", action="store_true", help="Show all translations including copyrighted")

    p_search = sub.add_parser("search", help="Search for translations (local catalog + eBible.org)")
    p_search.add_argument("query", help="Search query (translation name, language, or ID)")

    p_get = sub.add_parser("get", help='Look up a passage, e.g. btm get "John 3:16"')
    p_get.add_argument("reference", help='Bible reference, e.g. "John 3:16", "Ps 23:1-3"')
    p_get.add_argument("-t", "--translation", default="KJV", help="Translation abbreviation or id (default: KJV)")
    p_get.add_argument("--data-dir", default=None, help="Library data directory (default: ~/.local/share/bible-translation-finder)")

    p_find = sub.add_parser("find", help="Search verse text, e.g. btm find love --translation WEB")
    p_find.add_argument("query", help="Text to search for")
    p_find.add_argument("-t", "--translation", default="KJV", help="Translation abbreviation or id (default: KJV)")
    p_find.add_argument("--limit", type=int, default=20, help="Maximum matches (default: 20)")
    p_find.add_argument("--data-dir", default=None, help="Library data directory")

    p_download = sub.add_parser("download", help="Download a specific translation")
    p_download.add_argument("translation_id", help="Translation ID or abbreviation (e.g., 'KJV', 'eng-web')")
    p_download.add_argument("-o", "--output", default="output", help="Output directory")

    p_batch = sub.add_parser("batch", help="Download multiple translations")
    p_batch.add_argument("--ids", help="Comma-separated list of IDs/abbreviations (e.g., 'KJV,WEB,ASV')")
    p_batch.add_argument("-o", "--output", default="output", help="Output directory")
    p_batch.add_argument("--include-copyrighted", action="store_true", help="Include copyrighted translations (stubs)")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "get":
        cmd_get(args)
    elif args.command == "find":
        cmd_find(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "batch":
        cmd_batch(args)
    else:
        parser.print_help()

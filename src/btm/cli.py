"""Command-line interface for bible_translation_finder."""

import argparse
import os
import sys
from typing import Optional

from . import catalog, converter, scraper
from .library import Library, batch as batch_download, default_data_dir, download as download_one


def format_table(rows, headers):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    lines = []
    lines.append(" | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)))
    lines.append("-+-".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(" | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def cmd_list(args):
    lib = Library(getattr(args, "data_dir", None) or default_data_dir())
    translations = lib.list_translations(include_copyrighted=getattr(args, "all", False))
    rows = []
    for t in translations:
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
    local = catalog.search_catalog(query)
    if local:
        rows = [[t["abbreviation"], t["name"], t["language"]] for t in local[:30]]
        print(f"Found {len(local)} translations in the local catalog (showing up to 30):")
        print()
        print(format_table(rows, ["Abbrev", "Name", "Language"]))
        print()
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


def cmd_download(args):
    output_dir = args.output
    try:
        path = download_one(
            args.translation_id,
            output_dir=output_dir,
            data_dir=getattr(args, "data_dir", None),
            overwrite=getattr(args, "force", False),
        )
    except KeyError as e:
        print(e)
        print("Use 'list' to see available translations or 'search' to find more.")
        sys.exit(1)


def cmd_batch(args):
    output_dir = args.output
    if args.ids:
        translations = [x.strip() for x in args.ids.split(",") if x.strip()]
    else:
        # Default: all freely available translations
        translations = [t["abbreviation"] for t in catalog.get_freely_available()]
    batch_download(
        translations,
        output_dir=output_dir,
        data_dir=getattr(args, "data_dir", None),
        overwrite=getattr(args, "force", False),
    )


def cmd_downloaded(args):
    lib = Library(args.data_dir or default_data_dir())
    have = lib.downloaded()
    if not have:
        print("No translations have been downloaded yet.")
        return
    rows = [[t["abbreviation"], t["name"], t["language"], str(lib.file_for(t["abbreviation"]))] for t in have]
    print(f"Downloaded {len(have)} translation(s):")
    print()
    print(format_table(rows, ["Abbrev", "Name", "Language", "Path"]))


def _download_translation(t: dict) -> Optional[str]:
    """Legacy helper used by the converter pipeline tests."""
    from . import cli as _cli
    from .library import _fetch_opensong_xml
    return _fetch_opensong_xml(t)


def _output_opensong(t: dict, opensong_xml: Optional[str], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{t['abbreviation'].lower()}_{t['id'].replace('-', '_')}.xml"
    filepath = os.path.join(output_dir, filename)

    if opensong_xml:
        content = '<?xml version="1.0" encoding="UTF-8"?>\n' + opensong_xml
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Wrote: {filepath}")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(_make_stub(t))
        print(f"  Wrote stub: {filepath}  (contains placeholder only)")


def _make_stub(t: dict) -> str:
    from .library import _make_stub as _impl
    return _impl(t)


def run_cli():
    parser = argparse.ArgumentParser(
        prog="btm",
        description="bible_translation_finder - download Bible translations as OpenSong XML for use in FreeShow, OpenSong, and other lyrics-display software",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Where downloaded XML files are stored (default: ~/.local/share/bible-translation-finder)",
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List available translations in the catalog")
    p_list.add_argument("--all", action="store_true", help="Show all translations including copyrighted")

    p_search = sub.add_parser("search", help="Search for translations (local catalog + eBible.org)")
    p_search.add_argument("query", help="Search query (translation name, language, or ID)")

    p_download = sub.add_parser("download", help="Download a specific translation to a directory")
    p_download.add_argument("translation_id", help="Translation ID or abbreviation (e.g. 'KJV', 'eng-web')")
    p_download.add_argument("-o", "--output", default=".", help="Output directory (default: current directory)")
    p_download.add_argument("--force", action="store_true", help="Re-download even if the file already exists")

    p_batch = sub.add_parser(
        "batch",
        help="Download many translations at once (default: every freely available translation)",
    )
    p_batch.add_argument("--ids", help="Comma-separated list of abbreviations or IDs (e.g. 'KJV,WEB,LSG')")
    p_batch.add_argument("-o", "--output", default=".", help="Output directory (default: current directory)")
    p_batch.add_argument("--force", action="store_true", help="Re-download even if files already exist")

    p_downloaded = sub.add_parser("downloaded", help="List translations already downloaded to the data directory")

    args = parser.parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "downloaded":
        cmd_downloaded(args)
    else:
        parser.print_help()

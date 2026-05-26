# Bible Translation Maker

Download Bible translations from multiple sources and convert them to OpenSong XML format for use with [OpenSong](https://opensong.org/) worship presentation software.

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd bible-translation-maker
uv sync
```

## Usage

### List available translations

```bash
python main.py list          # freely available only
python main.py list --all    # include copyrighted (stub-only)
```

### Search eBible.org catalog

```bash
python main.py search "king james"
python main.py search "spanish"
```

### Download a translation

```bash
python main.py download KJV
python main.py download eng-web -o ./my_bibles
```

### Batch download

```bash
python main.py batch --ids KJV,WEB,ASV
```

Translation IDs: KJV, WEB, ASV, BBE, DARBY, DRA, YLT, OEB-US, OEB-CW, WEBBE, RV1909, BES, LUT1912, ALM, OST, RUS, CUV, BSB, FBV, LSV, GNV, TPT, PTP, NIV (stub), ESV (stub), NLT (stub), NKJV (stub), CSB (stub), NASB (stub), NRSV (stub).

## Output

Files are saved in OpenSong XML format:

```xml
<bible>
  <b n="1" name="Genesis">
    <c n="1">
      <v n="1">In the beginning God created the heaven and the earth.</v>
    </c>
  </b>
</bible>
```

## Supported Sources

| Source | Formats | Translations |
|---|---|---|
| [Open Bibles](https://github.com/seven1m/open-bibles) (GitHub) | OSIS, Zefania | KJV, WEB, ASV, BBE, DARBY, DRA, YLT, OEB-US, OEB-CW, WEBBE, RV1909, BES, LUT1912, ALM, OST, RUS, CUV, BSB, FBV, LSV, GNV, PTP |
| [eBible.org](https://ebible.org) | USFX | 50,000+ translations via catalog search |
| [YouVersion](https://bible.com) | Web scrape | The Passion Translation (TPT) |

## License

This tool is for personal use. Respect the copyright terms of each translation — copyrighted works (NIV, ESV, etc.) produce stub files only.

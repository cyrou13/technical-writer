#!/usr/bin/env python3
"""Build the pandoc reference document from an approved Avicenna deliverable.

`pandoc --reference-doc=<file>` takes the styles, the page setup, the headers and
footers (logo included) from that file and ignores its body, so an approved
deliverable of another CINA product is the shortest path to one house style
across the whole binder.

What this script produces from it:

* the body emptied, the section properties kept — the reference document carries
  formatting, never content;
* the header's product name, document title, document number and version
  replaced by the tokens `{{PRODUCT}}`, `{{DOCTITLE}}`, `{{DOCID}}` and
  `{{VERSION}}`, which every exporter substitutes for its own document
  (`docx_reference_for()` in `tools/_lib.py`);
* the style set completed with pandoc's own (Compact, Body Text, Table, ...): a
  paragraph naming a style the document lacks breaks table rendering;
* headings flush with the margin (the exporters number them in the text), each
  chapter on a new page in capitals; tables with single borders and a grey bold
  header row;
* four paragraph styles for the requirement idiom of the source document — the
  identifier on a grey band, the title in italic navy, the text in blue, the
  version line — emitted from Markdown through pandoc `custom-style` divs.

Table width and centring cannot come from a reference document (pandoc writes an
automatic, left-aligned width); `_lib.finish_docx()` sets them after pandoc runs.

Usage:
    python tools/make_reference_docx.py --from <approved.docx> [--out docs/templates/avicenna-reference.docx]
    python tools/make_reference_docx.py --requirements-only   # requirement styles only, in place

The output is committed: the build must not depend on a file that lives in
someone's downloads directory.
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "templates" / "avicenna-reference.docx"

#: Header cells to tokenise: (regex over the run text, replacement).
HEADER_TOKENS: tuple[tuple[str, str], ...] = (
    (r"CINA-[A-Za-z]+", "{{PRODUCT}}"),
    (r"Software Requirements Specifications?|Project Master Plan", "{{DOCTITLE}}"),
    (r"AV-DP-[A-Z0-9-]+(?: - [A-Z-]+)?", "{{DOCID}}"),
    (r"Version: ?\d*", "Version: {{VERSION}}"),
)

#: The requirement idiom of the source document, as named paragraph styles.
#: Values are (style id, style name, paragraph properties, run properties).
REQUIREMENT_STYLES: tuple[tuple[str, str, str, str], ...] = (
    # The style name equals the id: pandoc maps `custom-style="RequirementId"` by
    # NAME; any other name makes it append a second, empty style with the same
    # id, which Word applies instead of this one.
    # Properties as in the approved Avicenna SRS: the body and the version line
    # carry no spacing of their own (a blank line separates them, written by
    # `_lib.finish_docx()` with the closing rule), the version line is black.
    ("RequirementId", "RequirementId",
     '<w:keepNext/><w:shd w:fill="C0C0C0" w:val="clear"/><w:spacing w:after="120" w:before="360"/><w:jc w:val="left"/>',
     '<w:b/><w:bCs/><w:color w:val="000080"/>'),
    ("RequirementTitle", "RequirementTitle",
     '<w:keepNext/><w:spacing w:after="120" w:before="120"/><w:ind w:left="284"/><w:jc w:val="left"/>',
     '<w:i/><w:iCs/><w:color w:val="000080"/>'),
    ("RequirementBody", "RequirementBody",
     '<w:keepNext/><w:keepLines/><w:spacing w:after="0" w:before="0"/><w:jc w:val="both"/>',
     '<w:color w:val="0000FF"/>'),
    ("RequirementVersion", "RequirementVersion",
     '<w:keepNext/><w:spacing w:after="0" w:before="0"/><w:jc w:val="both"/>',
     '<w:color w:val="000000"/>'),
)

def _heading(level: int, *, before: int, indent: int, page_break: bool, rpr: str) -> tuple[str, str]:
    """A heading style: the exporters number their headings in the text ("2.1 Introduction"),
    so the style carries no list numbering; the hanging indent keeps a wrapped title
    aligned under its first word."""
    ppr = (
        "<w:keepNext/>" + ("<w:pageBreakBefore/>" if page_break else "")
        + f'<w:spacing w:before="{before}" w:after="120"/><w:ind w:left="{indent}" w:hanging="{indent}"/>'
        '<w:jc w:val="left"/>'
    )
    return ppr, rpr


#: Styles whose paragraph and run properties are REPLACED (style id → (pPr, rPr)).
#: The headings of the source document carry a left indent of one to three
#: list levels, meant for a hand-typed number; without it every heading sits
#: away from the margin.
RESTYLED: dict[str, tuple[str, str]] = {
    "Normal": ('<w:spacing w:after="120"/><w:jc w:val="both"/>', ""),
    "Heading1": _heading(1, before=240, indent=432, page_break=True,
                         rpr='<w:b/><w:bCs/><w:caps/><w:sz w:val="28"/><w:szCs w:val="28"/>'),
    "Heading2": _heading(2, before=360, indent=576, page_break=False,
                         rpr='<w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/>'),
    "Heading3": _heading(3, before=240, indent=720, page_break=False,
                         rpr='<w:b/><w:bCs/><w:i/><w:iCs/><w:sz w:val="22"/><w:szCs w:val="22"/>'),
    # pandoc's table-cell paragraph style: 9 pt, tight, left-aligned.
    "Compact": ('<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/>',
                '<w:sz w:val="18"/><w:szCs w:val="18"/>'),
}

#: pandoc's table style, in the look of the source document's tables: single
#: black borders, bold header row on a grey band, 9 pt body.
TABLE_STYLE = (
    '<w:style w:type="table" w:styleId="Table"><w:name w:val="Table"/><w:basedOn w:val="TableNormal"/>'
    '<w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:tblPr><w:tblBorders>'
    '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tblBorders>'
    '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
    '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
    '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:bCs/></w:rPr>'
    '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/></w:tcPr></w:tblStylePr></w:style>'
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def tokenise_header(xml: str) -> str:
    """Replace the header's document-identifying runs by substitution tokens."""

    def one(match: re.Match[str]) -> str:
        text = match.group(1)
        for pattern, token in HEADER_TOKENS:
            new, n = re.subn(f"^{pattern}$", token, text)
            if n:
                return match.group(0).replace(f">{text}<", f">{new}<")
        return match.group(0)

    out = re.sub(r"<w:t[^>]*>([^<]*)</w:t>", one, xml)
    # The version digit sits in a run of its own next to "Version: ".
    return re.sub(r"(\{\{VERSION\}\}</w:t></w:r>.*?<w:t[^>]*>)\d+(</w:t>)", r"\1\2", out, flags=re.S)


def empty_body(xml: str) -> str:
    """Keep the section properties, drop everything else from the body."""
    sect = re.search(r"<w:sectPr\b.*?</w:sectPr>", xml, re.S)
    head = xml.split("<w:body>", 1)[0]
    tail = "</w:body></w:document>"
    return f"{head}<w:body>{sect.group(0) if sect else ''}{tail}"


def pandoc_default_styles() -> str:
    """The styles.xml of pandoc's own reference document.

    pandoc gives every paragraph it writes one of ITS style names (Compact in
    table cells, Body Text, Source Code, ...). A reference document that lacks
    them yields a .docx whose paragraphs name styles that do not exist — LibreOffice
    then renders every table as empty cells with the text spilled underneath.
    """
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise SystemExit("pandoc is required to build the reference document")
    data = subprocess.run([pandoc, "--print-default-data-file", "reference.docx"],
                          capture_output=True, check=True).stdout
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read("word/styles.xml").decode("utf-8")


def restyle(xml: str, style_id: str, ppr: str, rpr: str) -> str:
    """Replace the paragraph and run properties of one existing style."""
    m = re.search(rf'<w:style [^>]*w:styleId="{style_id}".*?</w:style>', xml, re.S)
    if not m:
        return xml
    block = re.sub(r"<w:pPr>.*?</w:pPr>|<w:pPr/>", "", m.group(0), flags=re.S)
    block = re.sub(r"<w:rPr>.*?</w:rPr>|<w:rPr/>", "", block, flags=re.S)
    props = (f"<w:pPr>{ppr}</w:pPr>" if ppr else "") + (f"<w:rPr>{rpr}</w:rPr>" if rpr else "")
    block = block.replace("</w:style>", props + "</w:style>")
    return xml.replace(m.group(0), block)


def add_styles(xml: str, defaults: str) -> str:
    """The source's styles, completed with pandoc's, restyled where the house look needs it.

    Order of precedence: a style of the source document is kept; a pandoc style
    the source lacks is copied from pandoc's defaults; RESTYLED and TABLE_STYLE
    then override both; the requirement idiom is appended.
    """
    have = set(re.findall(r'w:styleId="([^"]+)"', xml))
    add = [blk for blk in re.findall(r"<w:style .*?</w:style>", defaults, re.S)
           if re.search(r'w:styleId="([^"]+)"', blk).group(1) not in have]
    xml = xml.replace("</w:styles>", "".join(add) + "</w:styles>") if add else xml
    for sid, (ppr, rpr) in RESTYLED.items():
        xml = restyle(xml, sid, ppr, rpr)
    xml = re.sub(r'<w:style w:type="table" w:styleId="Table">.*?</w:style>', "", xml, flags=re.S)
    xml = xml.replace("</w:styles>", TABLE_STYLE + "</w:styles>")
    return requirement_styles(xml)


def requirement_styles(xml: str) -> str:
    """Write the requirement idiom into a styles part: one definition per style,
    named as its id, with the properties of REQUIREMENT_STYLES."""
    for sid, name, ppr, rpr in REQUIREMENT_STYLES:
        xml = re.sub(rf'<w:style\b(?=[^>]*w:styleId="{sid}")[^>]*>.*?</w:style>', "", xml, flags=re.S)
        xml = xml.replace(
            "</w:styles>",
            f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/>'
            f'<w:basedOn w:val="Normal"/><w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style></w:styles>',
        )
    return xml


def live_media(zin: zipfile.ZipFile) -> set[str]:
    """Media still referenced once the body is gone: the header's and footer's."""
    keep: set[str] = set()
    for name in zin.namelist():
        if not re.fullmatch(r"word/_rels/(header|footer)\d+\.xml\.rels", name):
            continue
        for target in re.findall(r'Target="([^"]+)"', zin.read(name).decode("utf-8")):
            if target.startswith("media/"):
                keep.add(f"word/{target}")
    return keep


EMPTY_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
)


def drop_font_embedding(xml: str) -> str:
    """Remove the embedded-font references from the font table.

    pandoc copies the reference document's font table and its relationships but
    not the font binaries themselves, which leaves every produced .docx pointing
    at parts that are not in the package — a defect a strict reader trips over.
    The typefaces of the house style are standard ones, so nothing is lost by
    naming them and embedding none.
    """
    return re.sub(r"<w:embed(Regular|Bold|Italic|BoldItalic)\b[^>]*/>", "", xml)


def build(source: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    defaults = pandoc_default_styles()
    with zipfile.ZipFile(source) as zin:
        keep = live_media(zin)
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename.startswith("word/media/") and info.filename not in keep:
                continue  # a figure of the source document's body, which we drop
            if info.filename.startswith("word/fonts/"):
                continue  # see drop_font_embedding
            data = zin.read(info.filename)
            if info.filename == "word/document.xml":
                data = empty_body(data.decode("utf-8")).encode("utf-8")
            elif info.filename == "word/fontTable.xml":
                data = drop_font_embedding(data.decode("utf-8")).encode("utf-8")
            elif info.filename == "word/_rels/fontTable.xml.rels":
                data = EMPTY_RELS.encode("utf-8")
            elif info.filename == "word/styles.xml":
                data = add_styles(data.decode("utf-8"), defaults).encode("utf-8")
            elif re.fullmatch(r"word/header\d+\.xml", info.filename):
                data = tokenise_header(data.decode("utf-8")).encode("utf-8")
            elif info.filename in ("word/comments.xml", "docProps/app.xml", "docProps/core.xml"):
                # Metadata and review threads of the source document: not ours.
                if info.filename == "word/comments.xml":
                    data = (
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        f'<w:comments xmlns:w="{W_NS}"/>'
                    ).encode("utf-8")
            zout.writestr(info, data)


def restyle_requirements(path: Path) -> None:
    """Rewrite the requirement styles of an existing reference document, every
    other part byte for byte."""
    with zipfile.ZipFile(path) as zin:
        entries = [(info, zin.read(info.filename)) for info in zin.infolist()]
    tmp = path.with_suffix(".docx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            if info.filename == "word/styles.xml":
                data = requirement_styles(data.decode("utf-8")).encode("utf-8")
            zout.writestr(info, data)
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from", dest="source", type=Path, help="an approved .docx to take the house style from")
    src.add_argument("--requirements-only", action="store_true",
                     help="rewrite only the requirement styles of --out, in place")
    ap.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = ap.parse_args(argv)
    if args.requirements_only:
        restyle_requirements(args.out)
        print(f"OK: requirement styles rewritten in {args.out}")
        return 0
    if not args.source.is_file():
        print(f"no such file: {args.source}", file=sys.stderr)
        return 2
    build(args.source, args.out)
    with zipfile.ZipFile(args.out) as z:
        headers = [n for n in z.namelist() if re.fullmatch(r"word/header\d+\.xml", n)]
        tokens = sorted({t for n in headers for t in re.findall(r"\{\{[A-Z]+\}\}", z.read(n).decode())})
    print(f"OK: wrote {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    print(f"    header tokens: {', '.join(tokens) or 'none found — check the source header'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

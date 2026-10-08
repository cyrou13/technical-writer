"""Unit tests of the scaffolded working-draft exporters (scaffold/tools)."""
from __future__ import annotations

import importlib
import struct
import sys
import zlib
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "scaffold" / "tools"
sys.path.insert(0, str(TOOLS))

import _lib  # noqa: E402


@pytest.fixture(scope="module")
def sdd_mod():
    return importlib.import_module("build_sdd_export")


@pytest.fixture(scope="module")
def srs_mod():
    return importlib.import_module("build_srs_export")


class _It:
    def __init__(self, i: int, parent: str | None = None) -> None:
        self.id, self.title, self.status = f"SDS-T-X-{i:03d}", f"Item {i}", "Draft"
        self.fm = {"links": {"parent": [parent] if parent else []}}


def test_sdd_decomposition_of_one_level_fans_out_in_rows_that_fit_the_page(sdd_mod):
    """§3.6: ten items under one root are drawn top-down in two rows of five (an invisible
    link ranks the second row), not as one column of ten that overflows the page."""
    root = _It(0)
    items = [root] + [_It(i, root.id) for i in range(1, 11)]
    ctx = type("C", (), {"sds": items})()
    fig = "\n".join(sdd_mod.build_decomposition_figure(ctx))
    assert "flowchart TB" in fig
    assert fig.count(" --> ") == 10 and fig.count(" ~~~ ") == 5
    assert "    N2 ~~~ N7" in fig and "    N6 ~~~ N11" in fig


def test_sdd_decomposition_of_a_deeper_tree_keeps_left_to_right(sdd_mod):
    a = _It(0)
    b = _It(1, a.id)
    c = _It(2, b.id)
    ctx = type("C", (), {"sds": [a, b, c]})()
    fig = "\n".join(sdd_mod.build_decomposition_figure(ctx))
    assert "flowchart LR" in fig and " ~~~ " not in fig


def _png(path: Path, w: int, h: int) -> Path:
    raw = b"".join(b"\x00" + b"\xff" * w for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


def test_a_tall_rendered_diagram_is_bounded_to_the_page_height(tmp_path):
    """pandoc fits a wide figure to the text width but never a tall one to the page
    height: a diagram taller than the page gets a height bound, a wide one none."""
    assert _lib._figure_size(_png(tmp_path / "tall.png", 88, 279)) == "{height=20cm}"
    assert _lib._figure_size(_png(tmp_path / "wide.png", 157, 83)) == ""


def test_ots_hazard_contribution_renders_one_table_row_per_way():
    """SDD §5.3: the structured hazard contribution reads as a sentence, a table
    (contribution, components, containment) and a closing note; free text still passes."""
    md = _lib.render_hazard_contribution({
        "intro": "Two ways.\n", "note": "Nothing else.",
        "ways": [{"failure": "Wrong value", "components": "numpy,\n  scipy", "containment": "Phantom test"},
                 {"failure": "Bad object", "components": "pydicom", "containment": "Output tests"}]})
    assert md.splitlines()[0] == "Two ways."
    assert "| Contribution | Components | Containment |" in md
    assert "| Wrong value | numpy, scipy | Phantom test |" in md and md.endswith("Nothing else.")
    assert _lib.render_hazard_contribution("  Free text. ") == "Free text."


def test_the_scaffold_ots_example_parses_to_the_structured_form():
    data = _lib.parse_yaml((TOOLS.parent / "docs" / "ots.yaml").read_text(encoding="utf-8"))
    hc = data["hazard_contribution"]
    assert isinstance(hc, dict) and len(hc["ways"]) == 3
    assert all(set(w) == {"failure", "components", "containment"} for w in hc["ways"])
    assert data["components"] == []


def test_srs_conventions_print_the_structure_and_example_not_a_format_string(srs_mod):
    """§1.4 as in the approved reference SRS: brand sentence from the product config,
    the four-part structure and an example in the four Requirement* styles, the legend."""
    config = {"product": {"suite": "ACME", "application": "XYZ",
                          "suite_scope": "several image-processing applications",
                          "designation": "computes the maps"},
              "documents": {"sdd": "DOC-007-SDD"}}
    ctx = type("C", (), {"config": config})()
    md = "\n".join(srs_mod.build_conventions(ctx))
    assert md.startswith("ACME is the brand name of the ACME software suite, made of several "
                         "image-processing applications. In the context of this project and document, "
                         "ACME-XYZ refers to the ACME application that computes the maps.")
    assert "{CAT}" not in md and "```" not in md
    for style, text in (("RequirementId", "Requirement identifier"), ("RequirementTitle", "Requirement title"),
                        ("RequirementBody", "Requirement description"), ("RequirementVersion", "Last modification"),
                        ("RequirementId", "SRS-XXX-NN-AAA-000"), ("RequirementVersion", "V1.0")):
        assert f'::: {{custom-style="{style}"}}\n{text}\n:::' in md
    assert md.index("Last modification") < md.index("Example:") < md.index("SRS-XXX-NN-AAA-000") < md.index("Where:")
    assert "- XXX is the name of the software suite (ACME);" in md
    assert "- NN is the name of the image processing application (XYZ);" in md
    assert "- AAA is an abbreviation for a subset of functions." in md
    assert "left to the Software Design Description (DOC-007-SDD)." in md


def test_requirement_id_band_is_one_exact_line():
    import make_reference_docx as ref

    ppr = dict((sid, p) for sid, _n, p, _r in ref.REQUIREMENT_STYLES)["RequirementId"]
    assert 'w:line="240" w:lineRule="exact"' in ppr


def _risk(cat: str, **fm: object) -> _lib.Item:
    return _lib.Item(id=f"{cat}-T-001", category=cat, path=Path(f"{cat}-T-001.md"),
                     fm={"status": "Draft", **fm})


def test_risk_cell_caps_cover_the_production_and_use_related_registers():
    """The S05.7 caps apply to RSK, PRSK and URSK; a use error takes the sequence cap."""
    long_hazard = " ".join(["word"] * 9)
    assert any("hazard: 9 words" in o for o in _lib.risk_cell_offenders([_risk("PRSK", hazard=long_hazard)]))
    ursk = _risk("URSK", hazard="Wrong map", use_error=" ".join(["w"] * 26), hazardous_situation="Reader misled")
    offenders = _lib.risk_cell_offenders([ursk])
    assert offenders == ["word-cap: URSK-T-001 use_error: 26 words (cap 1–25)"]
    assert _lib.risk_cell_offenders([_risk("SRS", hazard=long_hazard)]) == []


def test_document_approvals_override_the_default_signatories_role_by_role():
    config = {"approvals": {"written_by": {"name": "A"}, "approved_by": {"name": "C"}},
              "document_approvals": {"sdd": {"written_by": {"name": "B"}}}}
    sdd = _lib.with_document_approvals(config, "sdd")["approvals"]
    assert sdd["written_by"] == {"name": "B"} and sdd["approved_by"] == {"name": "C"}
    assert _lib.with_document_approvals(config, "srs")["approvals"]["written_by"] == {"name": "A"}
    assert config["approvals"]["written_by"] == {"name": "A"}, "the input is not mutated"


def test_the_benefit_level_is_computed_and_compared_with_the_highest_residual():
    risk = importlib.import_module("build_risk_export")
    config = {"risk_management": {"benefit_level": {"probability": "Probable", "magnitude": "Serious"}}}
    bl, sentence = risk.benefit_level(config)
    assert bl == 12 and sentence.endswith("BL = 4 × 3 = 12.")
    ctx = type("C", (), {"config": config})()
    rsk = [_risk("RSK", residual_severity="Serious", residual_probability="Occasional")]
    assert "The benefit level 12 exceeds the highest residual risk level, RL 9." in risk.benefit_risk_lines(ctx, rsk)
    assert risk.benefit_level({"risk_management": {"benefit_level": {"probability": None}}}) == (None, "")


# ---------------------------------------------------------------------------
# Text handed to pandoc: dollars and figure captions
# ---------------------------------------------------------------------------


def test_a_bare_dollar_is_escaped_outside_code():
    """pandoc reads "$...$" as TeX math: two "$" in one table row merge its cells."""
    md = "| A | +X/$$7001 | +Y/$$7002 |\n\n`a $b`\n\n```\ncost $5\n```\nalready \\$ escaped"
    out = _lib.escape_dollars(md)
    assert "| A | +X/\\$\\$7001 | +Y/\\$\\$7002 |" in out
    assert "`a $b`" in out and "cost $5" in out
    assert "already \\$ escaped" in out


def test_pandoc_input_escapes_dollars_and_keeps_the_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(_lib, "_mmdc_path", lambda: None)
    md = tmp_path / "doc.md"
    md.write_text("Price $5 and $6.\n", encoding="utf-8")
    src, is_temp = _lib.pandoc_input(md, tmp_path / "figures")
    assert is_temp and src.read_text(encoding="utf-8") == "Price \\$5 and \\$6.\n"
    assert md.read_text(encoding="utf-8") == "Price $5 and $6.\n"


def _fence(source: str) -> str:
    return f"```mermaid\n{source}```\n"


def test_every_diagram_gets_one_numbered_caption_with_a_title(tmp_path, monkeypatch):
    """Figure N: title — N counted over the figures of the document; the caption the
    exporter wrote under the fence is consumed, else the section heading is the title."""
    import hashlib

    monkeypatch.setattr(_lib, "_mmdc_path", lambda: "/nonexistent/mmdc")
    figs = tmp_path / "figures"
    figs.mkdir()
    sources = ["flowchart LR\n  A --> B\n", "flowchart LR\n  C --> D\n"]
    for src in sources:
        _png(figs / f"fig-{hashlib.sha1(src.encode()).hexdigest()[:12]}.png", 10, 5)
    md = ("# 2. GENERAL ARCHITECTURE\n\n![Figure 1: Existing picture](x.png)\n\n" + _fence(sources[0])
          + "\n## 3.6 Decomposition\n\n" + _fence(sources[1])
          + "\n*Figure 3: Decomposition of the system.*\n\nNext paragraph.\n")
    out = _lib.render_mermaid_for_pandoc(md, figs)
    assert "![Figure 2: General architecture](" in out
    assert "![Figure 3: Decomposition of the system](" in out
    assert "*Figure 3:" not in out and "Next paragraph." in out


def test_a_cited_figure_takes_the_number_it_is_rendered_with():
    md = ("```mermaid\nA\n```\n\nFigure {f} shows it.\n\n```mermaid\nB\n```\n\n*Figure {f}: Title.*\n")
    out = _lib.number_figure_placeholder(md, "{f}")
    assert "Figure 2 shows it." in out and "*Figure 2: Title.*" in out


# ---------------------------------------------------------------------------
# Front matter: cover signature table, revision history, no chapter rules
# ---------------------------------------------------------------------------

EXPORTERS = ("build_srs_export", "build_sdd_export", "build_stp_export", "build_stdr_export",
             "build_str_export", "build_risk_export", "build_use_export")
_COVER_CONFIG = {"approvals": {
    "written_by": [{"name": "Ann Writer", "role": "R&D Engineer"}, {"name": "Bob Second"}],
    "verified_by": {"name": "Carl Check", "role": "R&D Manager"}}}


def _cover(config: dict | None = None) -> str:
    return "\n".join(_lib.document_cover(config if config is not None else _COVER_CONFIG, title="T",
                                         identifier="DOC-1", version_label="V01", date="2026-01-01"))


def test_the_cover_prints_each_name_with_its_function_under_it():
    """One row per signatory, the role label bold on the first row of its role, the
    function in its own paragraph under the name; date and signature left blank."""
    md = _cover()
    assert "| First/Last Name" in md and "| Date (MM/DD/YYYY) |" in md and "| Signature |" in md
    assert "## Signatures" not in md and "**Written by**" in md
    assert _lib.cover_rows(md) == [("Written by", "Ann Writer", "R&D Engineer"), ("", "Bob Second", ""),
                                   ("Verified by", "Carl Check", "R&D Manager"),
                                   ("Approved by", "[TODO approvals.approved_by]", "")]
    assert "2026-01-01 |" not in md.split("+=")[1], "no date is pre-filled in the signature boxes"


def test_a_highlighted_marker_does_not_break_the_cover_grid():
    md = _cover({}) + "\nBody [TODO fill] here.\n"
    out = _lib.highlight_markers(md)
    grid = [ln for ln in out.splitlines() if ln.startswith(("+", "|")) and "**Version:**" not in ln]
    assert len({len(ln) for ln in grid if ln.startswith(("+", "| "))}) == 1, "grid rows stay aligned"
    assert "[TODO approvals.written_by]" in out and "Body [\\[TODO fill\\]]{.mark} here." in out


def test_the_revision_history_has_the_house_header_no_heading_and_no_rule():
    lines = _lib.build_revision_history({"revision_history": [
        {"version": "V01", "date": "2026-01-01", "parts": "All", "reason": "Initial creation."}]})
    assert lines[0] == "| **Version:** | **Date:** | **Part(s):** | **Reason:** |"
    assert "| V01 | 2026-01-01 | All | Initial creation. |" in lines
    assert not any(ln.startswith("#") or ln == "---" for ln in lines)


@pytest.mark.parametrize("name", EXPORTERS)
def test_no_exporter_keeps_its_own_cover_revision_history_or_chapter_rules(name):
    src = (TOOLS / f"{name}.py").read_text(encoding="utf-8")
    assert "## Signatures" not in src and "## Revision history" not in src
    assert '"---"' not in src, "no horizontal rule between chapters"
    assert "document_cover(" in src and "return revision_history(ctx.config)" in src


def test_the_cover_renders_as_a_signature_table_in_the_docx(tmp_path):
    import shutil
    import subprocess
    import zipfile

    if not shutil.which("pandoc"):
        pytest.skip("pandoc not installed")
    md = tmp_path / "c.md"
    md.write_text(_cover(), encoding="utf-8")
    subprocess.run(["pandoc", str(md), "-o", str(tmp_path / "c.docx")], check=True)
    xml = zipfile.ZipFile(tmp_path / "c.docx").read("word/document.xml").decode()
    table = xml[xml.index("<w:tbl>"):xml.index("</w:tbl>")]
    import re

    assert len(re.findall(r"<w:tr[ >]", table)) == 5 and "Ann Writer" in table and "R&amp;D Engineer" in table


# ---------------------------------------------------------------------------
# References: one contiguous numbering per document
# ---------------------------------------------------------------------------


def test_references_are_numbered_contiguously_and_citations_follow():
    md = ("As stated in [R5] and \\[R9\\].\n\n| # | Document |\n|---|---|\n"
          "| [R5] | Plan |\n| [R9] | Report |\n\nSee [R9].\n")
    out = _lib.number_references(md)
    assert "| [R1] | Plan |" in out and "| [R2] | Report |" in out
    assert "As stated in [R1] and \\[R2\\]." in out and "See [R2]." in out
    assert _lib.reference_label_map("| [R1] | A |\n| [R2] | B |\n") == {}
    assert _lib.reference_label_map("| [R0] | A |\n| [R3] | B |\n") == {"R0": "R0", "R3": "R1"}


@pytest.mark.parametrize("name", EXPORTERS)
def test_every_exporter_numbers_its_references_per_document(name):
    assert "number_references(" in (TOOLS / f"{name}.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Conventions: brand sentence and identifier structure
# ---------------------------------------------------------------------------

_PRODUCT = {"product": {"suite": "ACME", "application": "XYZ", "suite_scope": "two applications",
                        "designation": "computes the maps"},
            "id_format": {"default": "{CAT}-{SUITE}-{APP}-{DOMAIN}-{NNN:03d}"}}


def test_the_identifier_convention_states_structure_example_and_fields():
    md = "\n".join(_lib.identifier_convention(_PRODUCT, ("RSK", "THR"), subject="each record",
                                              example_id="RSK-ACME-XYZ-IN-001", example_text="Wrong input"))
    assert "**CAT-SUITE-APP-DOMAIN-NNN**" in md and "{" not in md and "```" not in md
    assert md.index("structure:") < md.index("Example:") < md.index("Where:")
    assert "**RSK-ACME-XYZ-IN-001**: Wrong input" in md
    assert "- CAT is the category of the record (RSK for a design risk; THR for a cybersecurity threat);" in md
    assert "- SUITE is the name of the software suite (ACME);" in md
    assert "- APP is the name of the image processing application (XYZ);" in md
    assert md.rstrip().endswith("within its category and abbreviation.")
    single = "\n".join(_lib.identifier_convention({}, ("TC",), subject="a test case"))
    assert "**TC-DOMAIN-NNN**" in single and "- TC marks a test case;" in single and "Example:" not in single


@pytest.mark.parametrize("name", ("build_sdd_export", "build_stp_export", "build_stdr_export",
                                  "build_risk_export", "build_use_export"))
def test_every_document_that_defines_identifiers_states_brand_and_convention(name):
    src = (TOOLS / f"{name}.py").read_text(encoding="utf-8")
    assert "brand_sentence(ctx.config)" in src and "*identifier_convention(" in src
    assert "default_fmt" not in src, "the id_format string is never printed"


def test_the_stp_states_the_identifier_structure_an_example_and_its_fields():
    stp = importlib.import_module("build_stp_export")
    tc = _lib.Item(id="TC-ACME-XYZ-IO-001", category="TC", path=Path("t.md"),
                   fm={"status": "Draft", "title": "Reads the input", "objective": "Verify the reader"})
    ctx = type("C", (), {"config": _PRODUCT, "tc_items": [tc], "srs_items": [], "coverage": None,
                         "swf": lambda self, a: f"[{a}]"})()
    md = "\n".join(stp.build_tests_identification(ctx))
    assert "**TC-SUITE-APP-DOMAIN-NNN**" in md and "**TC-ACME-XYZ-IO-001**: Verify the reader" in md


# ---------------------------------------------------------------------------
# Risk register workbook and usability Annex 1
# ---------------------------------------------------------------------------


def test_stored_values_print_as_reader_labels():
    xl = importlib.import_module("build_risk_xlsx")
    assert xl.control_label("inherent_design") == "Inherent safety by design"
    assert xl.control_label("information_for_safety").startswith("Information for safety")
    assert xl.stride_label(["T", "dos"]) == "Tampering, Denial of service"
    assert xl.attacker_label("external_unauth") == "unauthenticated external attacker"
    assert xl.attacker_label("rogue_vendor") == "rogue vendor" and xl.control_label(None) == "—"


def test_an_asset_text_that_names_a_path_is_reported():
    xl = importlib.import_module("build_risk_xlsx")
    bad = _risk("PRSK", asset_at_risk="the signing key in prod/keys/release.pem")
    good = _risk("THR", asset="the release signing key")
    assert [o.split(":")[0] for o in xl.asset_offenders([bad, good])] == ["PRSK-T-001 asset_at_risk"]


def test_an_unperformed_evaluation_fails_the_clause_with_its_reason_and_a_performed_one_passes():
    use = importlib.import_module("build_use_export")
    row = {"clause": "5.9", "verdict": "P", "evaluation": "summative"}
    assert use.annex1_verdict({}, row, "See USE §3") == ("F", "See USE §3 — The summative evaluation is to be performed.")
    done = {"usability": {"evaluations": {"summative": True}}}
    assert use.annex1_verdict(done, row, "See USE §3") == ("P", "See USE §3")
    assert use.annex1_verdict({}, {"verdict": "NA"}, "—") == ("NA", "—")


def test_the_scaffold_checklist_ties_the_evaluation_clauses_to_their_evaluation():
    import csv

    rows = list(csv.DictReader((TOOLS.parent / "static" / "iec62366-annex1-checklist.csv").open(encoding="utf-8")))
    tied = {(r["clause"], r["evaluation"]) for r in rows if r["evaluation"]}
    assert tied == {("5.8", "formative"), ("5.9", "summative")}
    config = _lib.parse_yaml((TOOLS.parent / "dt-config.yaml").read_text(encoding="utf-8"))
    assert config["usability"]["evaluations"] == {"formative": False, "summative": False}


def test_the_post_market_plan_refuses_a_store_identifier():
    """The PMS plan cites risks and threats by their titles (T5)."""
    assert any(o.startswith("internal-id") for o in _lib.altitude_lint("Watch RSK-ACME-IN-001.", doc="PMS"))
    assert not any(o.startswith("internal-id") for o in _lib.altitude_lint("Watch wrong input.", doc="PMS"))

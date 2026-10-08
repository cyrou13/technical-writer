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

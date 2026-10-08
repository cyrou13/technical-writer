---
name: sds-generate
description: Generate Software Design Specification and architecture items (IEC 62304 §5.3-§5.4) from a TS/JS + Python codebase — module items with Design vs Design notes, the OTS registry, and the six required narrative sections of dt-clinical-context.md including the four cybersecurity architecture views. Invoke to produce items in docs/items/SDS/.
---

## OUTPUT LANGUAGE — STRICT

Any SDS item produced while applying this skill (frontmatter values,
body sections, `[TODO]`/`[GAP-62304]` markers) MUST be written in
**English**, regardless of the user's conversational language or any
global `CLAUDE.md` instruction.

# SDS — extracting design and architecture

## Modules to identify

In **multi-repo** mode (codemap mode = `multi-repo`), treat each
component separately and prefix `source:` / `module:` with the component
name (`front/src/auth`, `back/api/routes`).

- **TypeScript / JavaScript** — workspaces / packages, first-level folders
  under `src/`, modules published through an `index.ts`, Nest/Next
  feature folders.
- **Python** — top-level packages (`__init__.py`), layers if present
  (`domain/`, `application/`, `infrastructure/`, `interfaces/`).

One SDS item = **one module with one responsibility**. If
`## Responsibility` needs "and … and …", split.

## Body of an SDS item — Design vs Design notes

```markdown
<!-- Exported. -->
## Responsibility
<1–3 sentences>

<!-- Exported. -->
## Interfaces
### Inputs
### Outputs
### Dependencies
- SDS-<ID> for internal modules; `docs/ots.yaml` key for third-party components

<!-- Exported. -->
## Invariants
- <constraints the module maintains>

<!-- Exported. The normative DETAILED DESIGN: algorithm (formula, steps, model), data (structures, units), interfaces realised, every threshold — as a number owned here or by name from the registry. Present tense. -->
## Design
<what the module does and how, today — enough to re-implement it>

<!-- Rationale ONLY — alternatives discarded and the reasons. Rendered once in the SDD appendix, never inline. Nothing normative. No dates. -->
## Design notes
<alternatives discarded, why this design, known limits of the approach>

<!-- Internal. -->
## Notes
## Open questions
## History
```

The line between the two: **`## Design` says what the design is;
`## Design notes` says why.** "The deconvolution uses oSVD with a fixed
oscillation index" is Design. "Standard SVD was rejected because the
oscillation index drifts with noise" is Design notes. "Changed from
sSVD to oSVD after the noise sweep" is History, dated.

Two defects the reviewers found on both sides of that line:

- **Inverted split** — a decomposition chart, a containment contract, a
  refusal-rule list, an allowlist, an interval table sitting in
  `## Design notes` (so the normative design is in the rationale
  appendix and §3.7 says nothing). Anything that *specifies* is Design;
  the architecture chart lives in the body.
- **Thin design** — "features named, no formula": a motion-correction
  module with no algorithm and no bound, a denoiser with no filter, an
  AIF selector listing features but no weights, a QC module with
  "checks" but no thresholds. `## Design` states the algorithm, the
  data, the interfaces and the thresholds (or names the registry
  parameter that owns each); a reviewer must be able to re-implement
  the module from it.

Other single-truth rules of the SDD: **one declared-environment table**
(every environment variable the software reads, in one SDS or one
clinical-context anchor, referenced everywhere else — not "four
variables" here and "eight" there); **one run-state table** (the exit
statuses stated once, other sections reference it); a behaviour stated
once and referenced ("the study identifier is never minted" in one
place, not three phrasings). `references:` names the source of every
algorithm (SL-9).

## Parameters

An SDS quoting a constant (a regularisation floor, a buffer size, a
default, an ingest bound, a resource limit) **owns** it in `parameters:`
exactly as an SRS does (skill `items-store`): `source` is prose or a
dotted symbol, never a path; list values are lists. If an SRS already
owns the name, reference it by name in the text; never redeclare it,
never restate a different literal. The SDD renders **§3.8 as the whole
registry** (SRS and SDS parameters joined, with the owning item) — an
SDS whose constants live only in prose leaves §3.8 empty while the
numbers are scattered through the appendix.

## OTS / SOUP registry — `docs/ots.yaml`

Third-party components are **identified in the registry, not in prose**.
One entry per component:

```yaml
components:
  - component: numpy            # key used in interfaces.depends_on
    version: "1.26.4"
    supplier: NumPy developers
    role: array arithmetic for all map computations
    safety_relevant: true       # does a failure of this component reach a clinical output?
    functions_used:
      - numpy.linalg.svd
      - numpy.fft
    hazard_review: RSK-CTP-OTS-001   # RSK item reviewing the failure modes, or "none — not safety relevant"
    verification: TC-CTP-OTS-001     # TC (or suite) that exercises the functions_used
    eol_status: supported            # supported | maintenance | end-of-life | unknown
    sbom_ref: sbom/cyclonedx.json#numpy
```

The architecture-writer creates or updates the registry from the
dependency **locks** (exact versions); the security-analyst reads it for
supply-chain threats; the exporter renders the registry as the SDD's
SOUP table, below the `control_procedure` and `hazard_contribution`
narratives of the same file (`hazard_contribution` in the structured form
`intro` / `ways[failure, components, containment]` / `note`, rendered as a
sentence, a three-column table and the note). A version or supplier written in an item
body fails SL-3. The registry rules (SL-12):

- **one row per installed component at its exact version** — no range
  pin, no second row for one name; when pip and conda both carry a name
  the pip row is the component and `supersedes` says so ("conda numpy
  2.2.6: the pip wheel shadows it at import time");
- **`functions_used` from the actual imports** of the device code —
  grep the package; "clustering" is not a symbol, and a row claiming
  "no symbol imported" while an SDS says the module clusters with it is
  a contradiction;
- **`hazard_review` honest about scanner coverage** — pip-audit covers
  pip packages only; a conda-installed C library or an OS package says
  what controls it instead (digest-pinned image, rebuild at release);
- **the base image is one entry** (digest as version, OS packages as
  `functions_used`);
- **safety relevance justified per component** after the dash of
  `hazard_review` ("not on any device code path; imported by the test
  suite only") — a component another component aborts without is on
  the code path;
- **no second inventory in prose** — a dependencies paragraph in an SDS
  or a table in the clinical context is a defect; the SDD renders this
  file.

## Architecture views — `SDS-ARCH-*` items

- `SDS-ARCH-001` logical view (components ↔ responsibilities),
- `SDS-ARCH-002` deployment view (if Dockerfile / compose / k8s /
  serverless detected),
- `SDS-ARCH-003` data view (if a persistence layer exists).

Mermaid diagrams in `## Design` (never in `## Design notes`) when they
carry more than three nodes. A runtime diagram shows the **whole stage
chain** the SRS pipeline requirement lists — one name per class, no
stage skipped, the same numbering as the stage table.

## Narrative sections — `docs/dt-clinical-context.md`

The exporters inline `## <anchor>` sections of this file into the
deliverables. The SDD **requires** the six below with real content (SL-6);
`/doc-init` scaffolds them as empty headed sections and the
architecture-writer fills them.

| Anchor | Content |
|---|---|
| `general-system-architecture` | the component diagram and one paragraph per component |
| `run-states` | the state machine of the software: idle, receiving, processing, exporting, error, maintenance; entry and exit conditions; what is observable in each state |
| `architecture-rationale` | why the architecture is what it is — the module-level `## Design notes` roll up here; no dates |
| `security-global-view` | FDA 2023 premarket cybersecurity guidance, global system view: every network interface, port, protocol, trust boundary, authentication point, data store and its protection at rest and in transit, on one diagram |
| `security-multi-patient-view` | how data of one patient is isolated from another across the same instance: session scope, storage separation, identifiers, cleanup |
| `security-updateability-view` | how software and OTS updates are delivered, authenticated (signature), applied, rolled back; who can trigger an update; what the device does during one |
| `security-use-case-views` | one view per security-relevant use case (ingest a study, export results, administer, update), each showing the actors, the data crossing a boundary and the control that protects it |

Each THR item names the view it is drawn on in `architecture_view:`.

## Dependencies

`interfaces.depends_on` lists internal modules by SDS ID and OTS
components by their registry key. Nothing else — no version, no URL.

## Linking to SRS

For every SDS item fill `links.implements:` with the SRS IDs whose
`source:` files fall inside the module. A module implementing no SRS gets
a `[GAP-62304]` line in `## Open questions` (never in a normative
section): either the SRS is missing or the module is dead.

## Anti-patterns

- Describing code line by line — describe interfaces and invariants.
- Duplicating the SRS — SDS says *how*, SRS says *what*.
- "Utility module" with no responsibility — extract one or flag it.
- Naming a competitor or a code path as the subject of a sentence in
  `## Design`.
- A dated sentence anywhere but `## History`.

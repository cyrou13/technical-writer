# tools/ — what is scaffolded here, and what is not

`/doc-init` copies the scripts below into this folder (`/doc-init --update`
refreshes them):

| File | Role | Deliverable? |
|---|---|---|
| `build_docs.py` | working build: aggregates `docs/items/**` into `docs/generated/` (SRS, SDS, STD, traceability, risk / cyber / usability analyses, `_to_implement.md`, `coverage.json`); `--strict` fails on open markers, class A severities and unaccepted residuals | **No.** `docs/generated/` is an engineering view for the writers and the reviewer. |
| `_lib.py`, `build_srs_export.py`, `build_sdd_export.py`, `build_stp_export.py`, `build_stdr_export.py`, `build_str_export.py`, `build_risk_export.py`, `build_risk_xlsx.py`, `build_use_export.py` | the scaffolded **working-draft** generation of the exporters (`--strict`, `--md-only`): they render the deliverables into `docs/export/` (or straight into the submission tree when `submission.root` is set — see the plugin README) with yellow `<mark>[TODO]</mark>` markers for the QMS author and know nothing of the release gate | **Working drafts and `--internal` review copies only.** A `--release` export requires the reference exporters below. |
| `build_migrate.py`, `refresh_items.py`, `build_prompts.py`, `audit_mitigations.py` | `/doc-migrate`, `/doc-refresh-items`, `/doc-prompts`, `/doc-audit-mitigations` — migration audit, additive item refresh, coverage-gap prompts, code-vs-mitigation audit | **No.** |

`build_docs.py` is a stdlib-only snapshot kept deliberately simple. It is
**older than the reference copy** and knows nothing of the release gate:
it does not strip `## History`, does not check `parameters:`, `kind:`,
`docs/ots.yaml` or the clinical-context anchors, and its `--strict`
counts a `[TODO]` in `## Open questions` as an offender (a release
refuses open questions anyway).

The scaffolded `build_*_export.py` are in the same situation: they strip
nothing, lint nothing beyond `<mark>[TODO]</mark>` and `residual_acceptable`,
and print a per-item version. What they produce is a working draft, never
a signed deliverable.

## The reference exporters live in the CINA-CTP repository

The customer-facing deliverables are produced by exporters that are
**not part of this plugin** (the plugin ships the working-draft generation
above). They are maintained in the CINA-CTP
repository (`tools/`) and must be synced from there over the scaffolded
copies of the same name — never edited in a target project, never copied
into the plugin:

| Script | Produces |
|---|---|
| `_lib.py` | shared helpers: frontmatter parser (multi-line scalars, dotted keys), `strip_internal_sections`, `strip_empty_headings`, HTML-comment stripping, document-control and lint checks, `document_identifier` / `document_title`, `load_references` / `render_references_table`, risk scales from `classification.*_definitions`, TC statuses and run metadata of the bound run, Mermaid → figure rendering for pandoc |
| `build_srs_export.py` | Software Requirements Specification (one section per `kind`, each requirement a heading, references table, parameter registry §4.1) |
| `build_sdd_export.py` | Software Design Description (modules rendered once, whole parameter registry §3.8, OTS table from `docs/ots.yaml` deduplicated, the six narrative sections, threat records, rationale appendix, unresolved anomalies appendix) |
| `build_stp_export.py`, `build_stdr_export.py`, `build_str_export.py` | Software Test Plan / Description and Results / Report — each under its own `documents.<x>` identifier |
| `build_risk_export.py` | risk analysis report (Design / Production / Usability tabs, per-record controls and residual argument, threat records, scales, `.xlsx`) |
| `build_open_points.py` | the open-points register (`## Open questions` + markers) — `--internal` only |
| `build_rationale.py` | the SDD rationale appendix from the `## Design notes` sections |
| `bind_test_results.py` | binds a junit report to the TC items (`status`, `executed_at`) and writes `test_results_path` with the run metadata for the STDR / STR |

Sync: copy the scripts above from the CINA-CTP repository at the commit
you want to pin, and record that commit in your `dt-config.yaml`
(`exporters.synced_from`) or the project changelog. When the plugin's
skills and the exporters disagree, the exporters are the executable
truth and the skill is corrected.

## The contract the exporters implement

Stated in the skills `items-store` and `submission-readiness`; restated
here so a reader of `tools/` finds it:

1. **Sections.** Normative sections are rendered: SRS `## Description`,
   `## Acceptance criteria`; SDS `## Responsibility`, `## Interfaces`,
   `## Invariants`, `## Design`; TC `## Preconditions`, `## Steps`,
   `## Expected results`; the standard RSK / PRSK / THR / URSK / USC
   sections. `## Notes`, `## Open questions`, `## History` (and any
   legacy `## Changelog`) are never rendered. `## Design notes` is
   rendered once, in the SDD rationale appendix. HTML comments
   `<!-- … -->` are stripped before anything else.
2. **Frontmatter.** SRS `kind:` ∈ functional | performance | interface |
   platform | usability | safety | security | process — one exported
   section per kind in use. `parameters:` (`name`, `value`, `unit`,
   `settable`, `interval`, `source`) on SRS and SDS: one name = one
   value across the store. TC `test_id` must resolve to a test that
   exists; planned TC are never counted as coverage.
3. **Modes.** No flag → cover `WORKING DRAFT — generated <date>`, no
   open points. `--internal` → same cover plus the open-points register.
   `--release` → signed cover from `dt-config.yaml`, and the export is
   **refused** when any exported item's `updated` / `reviewed` postdates
   `document.date`, when `revision_history` lacks
   `document.version_label` at `document.date`, or when exported text
   carries `[TODO`, `[DRAFT`, `[GAP-`, an ISO date, a commit hash, a
   term of `lint.forbidden_terms` (competitor names), a tick-box, or —
   in the SRS — a code or test path.
4. **Registries.** Third-party components are identified in
   `docs/ots.yaml` only (`component`, `version`, `supplier`, `role`,
   `safety_relevant`, `functions_used`, `hazard_review`, `verification`,
   `eol_status`, `sbom_ref`). The SDD requires the six narrative anchors
   of `docs/dt-clinical-context.md`: `general-system-architecture`,
   `run-states`, `architecture-rationale`, `security-global-view`,
   `security-multi-patient-view`, `security-updateability-view`,
   `security-use-case-views`.
5. **Rendering.** Each item is rendered exactly once in its deliverable.
   The open-points register is never an appendix of a deliverable
   outside `--internal`.

## Round-2 behaviours — the reference contract

The second review (SRS, SDD, RAR, STP, STDR, STR) added the behaviours
below. They are what the reference exporters do, and what a target
project's writers must produce items for; the plugin skills
(`items-store`, `submission-readiness`) state them as rules TL-11…14,
SL-8…14, DEC-1/2.

1. **Parameter registry.** `parameters[].source` is prose or a dotted
   symbol; a file path is a release-lint offender. One owner per name
   (a second declaration, even equal, is refused); list values rendered
   in full; every frozen parameter described by the requirement that
   owns it. The registry is rendered in **SRS §4.1** and, joined with
   the SDS parameters and their owning items, in **SDD §3.8**.
2. **Requirement rendering.** Each requirement is a heading with one
   attribute row (kind, priority, verification); no per-item version —
   `document.version_label` is the only version. Kind sections list id,
   title and attributes only, never a summary derived from the body,
   and exist only for the kinds in use (§1.4 names them). §1.3 carries
   the **References** table: `dt-config.yaml: references[{id, citation}]`
   joined with the items' `references:` id lists; an id no entry defines
   is an offender. §1.3 also states where the RSK / THR / PRSK / URSK,
   TC and SDS ids are defined. Headings left empty by section stripping
   are removed.
3. **Criteria.** Acceptance criteria and expected results are behaviour
   with a number; a status word, a test / decision id as subject, a
   placeholder or an unquantified tolerance is an offender (TL-11).
4. **Terminology.** One glossary term per concept across SRS text,
   labeling anchors and report strings; the labeling term wins (TL-13,
   warning).
5. **SDD.** `## Design` is rendered inline as the normative detailed
   design; `## Design notes` once, in the rationale appendix, and the
   appendix says it specifies nothing; the architecture chart is in the
   body; one declared-environment table; one run-state table.
6. **Threat records.** Each THR renders `## Threat description`,
   `## Attack path and preconditions`, `## Level justification`,
   `## Controls` (SRS / SDS ids, each with the bound status of the TC
   that verifies it), `## Residual` (level + acceptance condition),
   `## CIA impact analysis`; a TC id under Controls is an offender. The
   four `security-*` anchors are required.
7. **Risk records.** The RAR renders `## Risk controls` and `## Residual
   risk justification` per record, each control with its title and
   bound TC status; a residual accepted with an unchanged index and an
   empty justification, or `information_for_safety` as the only control
   with a lowered index, is an offender; hazard text describing the
   pre-control state, a person or a host is an offender.
8. **Risk scales.** `classification.severity_definitions` /
   `probability_definitions` (harm-based sentences) are rendered in the
   RAR methodology; bare names → integers are an offender. The class
   argument table lists each RSK / PRSK once with initial and residual
   severity.
9. **OTS registry.** One row per installed component at exact version;
   when pip and conda both carry a name the pip row wins and
   `supersedes` says so; `functions_used` from actual imports;
   `hazard_review` honest about scanner coverage; the base image is one
   entry; `control_procedure` and `hazard_contribution` rendered above
   the table; a second inventory in prose is an offender.
10. **Unresolved anomalies appendix** (SDD Appendix C, STR): the
    `KNOWN_DEFECTS` literal of `tests/test_known_defects.py` (a named
    regression test must exist there), every TC bound
    `passed_with_skips` / `passed_with_xfail` / `skipped`, every risk
    item at `residual_acceptable: false`, and the
    `anomalies.open_actions_section` of `anomalies.open_actions_record`
    rendered verbatim. It is a dated record, the only exported text
    exempt from the date rule. The open-points register stays
    `--internal`.
11. **Test evidence.** The STDR groups cases by the DOMAIN token of the
    TC id, prints `type`, `verifies`, `mitigates`, the procedure, and
    per expected clause the per-test-function actual result;
    `executed_at` is stated as the suite start; the summary by type
    totals every case. `bind_test_results.py` statuses: `passed`,
    `passed_with_skips`, `passed_with_xfail`, `failed`, `skipped`,
    `not_run`, `manual_passed`, `manual_failed` — a skip or an xfail
    inside a case is never folded into `passed`. Its run metadata
    (`software_version` + `software_version_source`,
    `release_evidence_mode`, `hostname`, `platform`, `git_branch`,
    `git_dirty`, `python_version`, `pytest_version`, `numpy_version`,
    `run_started`) is printed in the STDR / STR; the cover of no
    deliverable prints a software version. The STR has anomalies /
    deviations, the disposition of every not-executed case and a
    conclusion. The STP names every uncovered requirement and states the
    coverage rule; a benchmark / release gate run has its own TC.
12. **Document identifiers.** `documents: {srs, sdd, rar, stp, stdr,
    str}` — each exporter prints and names its file by its own entry;
    the title is `document.title` with the document type substituted;
    `project_references` must agree with `documents`.
13. **Link stripping.** When a hash, an issue or a competitor reference
    is removed, the whole parenthetical or clause goes; "(open issue"
    left behind is an offender (TL-12).
14. **Labeling vs specification.** A warning naming an output the SRS
    forbids, or an intended use omitting the indication the thresholds
    encode, is reported by the `compliance-reviewer` at DECISION level
    for the product owner / RAQA (DEC-1/2); no tool and no writer edits
    the labeling anchors.

`/doc-build --release` runs the gate and refuses to call an exporter
when the store is not clean; the `compliance-reviewer` reports the
offenders first. Without the exporters in `tools/`, `/doc-build
--release` states that no deliverable can be produced.

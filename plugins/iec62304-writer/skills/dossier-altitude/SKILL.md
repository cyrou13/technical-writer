---
name: dossier-altitude
description: Règles de niveau de détail (« altitude ») et de forme des livrables du dossier technique, calées sur un dossier Avicenna approuvé (CINA-CSpine) et arbitrées document par document. À appliquer avant d'écrire ou d'exporter un item MAP/SRS/SDS/TC/RSK ou un livrable, et par les agents requirements-writer, architecture-writer, risk-analyst, test-evidence-collector et doc-updater.
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill is written in **English**.

## Why this skill exists

A docs-as-code pipeline drifts toward the code: every function, config key and
test becomes a sentence, and the technical file grows to several times the size
of an approved one without saying more to a reviewer. The rules below set the
altitude of each deliverable. They were arbitrated one document at a time
against an approved Avicenna technical file (reference: CINA-CSpine; review of
CINA-CTP V01, 2026-10-07). The reference sets form and altitude, not content: a
quantitative device keeps what makes it differ (rule marked *adapted*).

## Transverse rules (every deliverable)

- **No code in deliverable text.** No function, class, module or test name, no
  config key, no repository path, no CI job name, no internal ticket or
  decision code (`#152`, `I40`, `A1`). Values are written in clear with their
  unit ("3000 HU", "6 s"), never as the key that holds them.
- **No measured result outside a results document.** A plan, a glossary or a
  description never carries a verification figure (it goes stale at the next
  regeneration and reads as an unsupported claim). The Methods' verification
  sections and the clinical report are results documents; their figures are
  injected from the metrics files, never typed.
- **No TODO, no "evidence still owed", no draft banner in a release export.**
- **One source per information.** A topic is written once, in the document that
  owns it; the others refer to it.
  Keep a "topic → owner" table in the generator configuration: algorithms →
  Methods; threats → cyber risk assessment; parameters → SDD parameter table;
  glossary → PMAP; known anomalies → VDD; results → clinical report and Methods.
- **No internal identifiers outside the verification chain.** SRS-/TC-/RSK-/USC-/
  THR- identifiers appear only in SRS, SDD, test and risk documents and the
  traceability matrix — never in the user guide, usability file, integration
  guide, labels, model card or declarations.
- **Enforced by a blocking release lint**, outside generated annexes: backticks,
  repository paths, test names, configuration keys, TODO; word caps per field
  (requirement 30–80 words; test card ≤ 90 with expected ≤ 40; risk cells per the
  register caps); evidence lists in a body; internal identifiers in
  non-verification documents.
- **Word template (house).** A4; dates MM/DD/YYYY; no page break per chapter; H1
  in capitals numbered by Word; "** End of Document **"; no draft banner and no
  build date (draft state = version + empty signature table); signature table
  role / name and function / date / Signature; no title H1 or identifier block in
  the body (the header carries them).

## PMAP — Project Master Plan (MAP items)

The PMAP states stakeholder needs. A MAP requirement is atomic, ≤ ~50 words,
names no implementation and no process step.

Requirement set (each one a MAP item; children re-parented accordingly):

| Group | Requirements |
|---|---|
| Intended function | the device function (inputs → outputs), thresholds stated as fixed when they are; decision-support positioning (*adapted*: a quantitative device keeps an explicit "no diagnosis, not the sole basis" requirement) |
| Input data | one requirement "Description of the input imaging data", 6–10 bullets in clinical values: SOP class / orientation, temporal coverage and inter-phase interval (dynamic studies), slice thickness, z coverage, patient age. No config key. Parent of the SRS input/IO/timing requirements |
| Context of use | six atomic requirements: container packaging; folder-based exchange with the host platform, no data stored; PHI replicated unmodified into the outputs; image identified by name, tags and digest; log file; configurable output language (English for validation) |
| Configuration | clinical thresholds fixed and version-identified; only deployment parameters settable by the integrator. Never "JSON / environment / CLI" |
| Security | integrity and confidentiality of the processed data and results, per IEC 81001-5-1. No threat list (threats live in the security plan / threat model) |
| Accompanying documents | six requirements: SOUP/COTS list, CVE analysis, user guide content (list of its sections), localisation, labels, integration documentation |
| Regulatory | one requirement: device class and rule (MDR Annex VIII), software safety class (IEC 62304 §4.3). No approval codes, no rationale (it lives in the development plan) |
| Performance | processing time on the reference host, within the labelled input bounds |

Not in the PMAP:
- process requirements (reproducible build, pinned dependencies, release and
  update control, non-regression) → PMP / development plan;
- requirements that describe excluded or hidden functionality in negative
  ("any other output shall be unreachable…") → delete; the outputs requirement
  is enough;
- predicate argumentation ("why this predicate", "known differences") → the
  performance/comparison report and the 510(k) summary. §Predicate keeps the
  identification block only. A similar-devices table may stay (*adapted*: a
  crowded field), without analysis prose.

Sections:
- **Glossary**: 4–6 one-line definitions of the domain terms only, no figure;
  ≈ 10 abbreviations. The PMAP glossary is the single source; SUM, UEF, USE refer
  to it.
- **Device description** (target ≈ 370 words): form and integration, input,
  outputs, declared thresholds. Processing in 2–3 sentences (what is computed,
  not the step chain — that is the SDD and Methods).

## PMP — Project Management Plan

The PMP is a QMS plan in the house text; it follows the approved plan almost
word for word and adds only what the project really needs.

- **No list of deliverables.** Numbering follows the QMS document-identification
  instruction; the technical-file tree is the list. A hand-kept table in a signed
  plan drifts and becomes an audit finding.
- **Roles, not people's merits.** The team table states roles and names; no
  sentence describing one person as the designer of the software.
- **WBS task types** come from the QMS procedure; a new letter (e.g. cybersecurity,
  regulatory submissions) exists only once quality has confirmed it.
- **Machine learning.** Two sentences at most: the locked ML components, *each one
  named* (verify against the SRS/SDD off-the-shelf components — every network
  counts, not only the obvious one), and the rule that any change follows the
  device change process. Training data, AI regulation and governance belong to the
  model card(s), one per component.
- **Planning annex**: the Gantt only. Never date a design review that the
  review records (DHF) do not hold; align the dates on the minutes.
- **No tools section** when the development plan already holds the tool list.
- **Validation tasks** state exactly what is performed (e.g. standalone only, no
  reader study) — the same statement as the performance report; never leave the
  two documents contradicting each other.
- **Abbreviations** ≤ ~10; terms refer to the PMAP glossary.
- **Zero TODO at signature**: each open fact (task owner, supplier, target
  release) is resolved with the owner before export, or the sentence goes.

## Risk management (ISO 14971, IEC 62366-1, IEC 81001-5-1)

**Plan.**
- The acceptability scale is the house one, word for word, in plan, register and
  report alike: RL = probability × severity on the 5×5 matrix; 1–6 negligible,
  7–10 tolerable (≤ 30 % of hazards, reduced as low as possible), ≥ 11
  unacceptable; a caution ("could") for 1–6 and a warning ("should") for 7–10 in
  the instructions for use. Never invent another scale.
- A benefit-risk section with a Benefit Level scale (probability × magnitude of
  benefit) and the rule BL > RL; benefits come from the clinical evaluation.
- The software-safety-class justification lives in the report only.
- Security plan: C/I/A scales defined in four levels before use (never a count of
  register entries beside a level); activities named (SAST, SCA/SBOM, image scan,
  signing, security testing), never CI job names.

**Register (xlsx).**
- One risk per **functional hazard**, not per code module (approved file: 10 design,
  5 production, 9 usability, 7 cyber; a quantitative device may carry 12–15
  design risks). The code stage goes in the software-item column (SDD item name,
  never a file path).
- Process / QMS risks (empty test evidence, unreproducible evidence, build
  traceability) are not design hazards: production or QMS records.
- Always consider "validation data not representative of the intended population".
- The house 26-column template; the control measure is written in text (30–60
  words), never only a list of IDs or "(see linked items)". Caps: hazard ≤ 8 words,
  causes ≤ 20, sequence ≤ 25, situation ≤ 15; ≈ 165 words per row.
- The ISO/TR 24971 Annex A sheet answers every question (≈ 47) with the patient
  hazard and the register risk.

**Report.**
- No risk is rewritten in the report: team, update note, two P×S matrices
  (before / after control) listing the IDs; production and cyber details stay in
  the register and the cyber assessment. No test status, no file path. Target
  ≈ 22–25 pages.
- Residual evaluation in the house form: maximum RL after control, share of
  tolerable risks against 30 %, combined hazardous situations, IFU disclosures.
  A report is a conclusion, not a work-tracking table: close or rule every open
  residual before export.
- Safety claims section present. Neutral tone (no "argument stated so it can be
  attacked", no "evidence still owed"); counts drawn from the register.

**Cybersecurity documents (FDA §524B).** Threat model, cyber risk assessment,
cyber report, OTS/SBOM assessment and penetration test report are kept for a US
submission, but each threat is written once (the risk assessment); the others
hold a table or a reference; one references block. A penetration test report is
issued only from a performed test: an external provider, or an internal campaign
on the release image (method NIST SP 800-115, each trial and result recorded)
whose report states the testers' independence and has the protocol and results
reviewed by someone who did not develop the device; the cyber report then says
why no external test was performed.

## SRS — Software Requirements Specification

**Granularity.** One requirement per quantity or behaviour the user receives, not
per algorithm step. A quantitative device specifies each output quantity (≈ 9
for a perfusion device: preparation ×3, input-function selection ×1, maps ×2,
volumes ×3); the "how" is a one-line reference to the Methods document. Outputs
≈ 7 requirements, quality control ≈ 2 (technical-quality flag on the outputs;
stop without a plausible result on a non-recoverable failure). Each requirement
states what the user sees; engineering properties (display windows, page
self-identification, default consistency) belong to the SDD.

**What leaves the SRS.**
- Acceptance-criteria tables: they become the expected results of the test
  cases, summarised in the test description. A threshold that the user observes
  may stay in the requirement text.
- Per-requirement parameter tables and configuration chapters: the settable
  parameters fit one short "System environment" table; frozen parameters are not
  listed. Only deployment and presentation settings are settable in production
  (folders, language, series and pages emitted, log level); every processing
  setting is frozen in code with a named refusal.
- Process requirements (development, security lifecycle): one-line reference to
  the plans.
- Full traceability: the SRS carries SRS → user requirement only; risk, test and
  design links live in the traceability matrix.
- Per-area clinical preambles and the bibliography: one clinical introduction of
  ≈ 150 words; the bibliography goes to the Methods; only normative references
  stay. No drafting rules inside the deliverable.

**Cybersecurity.** 4–5 product requirements without values (bounded ingestion,
restricted decoding, no PHI in logs, no network interface, clinical parameters
not modifiable), 60–80 words each; numeric limits go to the SDD and the cyber
risk assessment. Never a bare reference to the security plan for a US filing.

**Always present.** Device Description (taken from the PMAP, never rewritten) with
an interface figure (device, host platform, PACS); a LOG requirement (levels
ERROR/WARNING/INFO/DEBUG, level settable); a product requirement that every
output DICOM object carries the UDI; a section on what the host platform must
provide; a one-line reference to the test plan for verification.

## SDD — Software Design Description

**Altitude.** Architecture and identified units, not developer documentation. For
a class B device, IEC 62304 §5.4.1 asks for units to be identified; per-unit
detailed design (§5.4.2–5.4.3) is class C only. Target 35–45 pages,
9,000–12,000 words; table of contents 3 levels; reference structure 1–5
(introduction, architecture, design, security, COTS/SOUP).

**Design chapter.** 8–10 software items in one table (item, description, SRS
requirements). The application-specific chapter is three tables — input checks,
processing units each pointing to its Methods section, outputs — plus one
specialisation figure, with the sentence "processing details and performance
verification: Methods". Never a function signature, a dataclass field or a
source path; class and method names only in tables.

**What leaves the SDD.**
- Design rationale with development results: ≈ 8 major decisions go to the
  Methods (one paragraph each, key figure); the rest to the internal engineering
  record.
- The full parameter register: only a ≈ 2-page table of clinically significant
  parameters and security limits stays.
- Known anomalies, expected failures, unaccepted residuals: VDD and risk file.
- Internal references (issue numbers, decision codes, test paths).

**Security and SOUP.** Threats as one table row each (component, scenario, risk,
mitigation, 40–60 words) referring to the cyber risk assessment, the single
detailed source; multi-patient, patchability and use-case views half a page each.
SOUP: direct dependencies only (≈ 12) with version constraint and role, then
"the authoritative list is the SBOM" and a reference to the OTS assessment.

**Inactive code.** When inactive code ships in the image, an appendix lists the
groups (reason, unreachability control) and a compact generated list of regions
(file and range per group), ≈ 3 pages.

## Test documentation — STP, STDR, STR

**Test plan (≈ 20 pages, ≈ 3,500 words).** Describes the test platform, not the
software factory: platform in 5 bullets, test datasets named functionally (one
line each), installation "Docker image from the registry, cf. VDD", personnel =
tester / technical manager / regulatory manager. Never a CI job name, a CI
variable or a repository path. Planned tests are objectives ("Verify that
<device> …", ≈ 15–25 words), requirement cells merged per group. Security testing
= one paragraph referring to the cyber risk assessment. Schedule = one sentence
(PMP); qualification = table Phase / Accountable / Organises / Executes /
Platform. From V02 the history lists test cases added / changed / renamed.

**Test description and report (body ≈ 60 pages).** One card per test case, 5
fields, ≤ 90 words: ID with status ☑ OK ☐ KO ☐ Not run; description; requirements;
analyst = a named person who reviews the run (never "automated"); execution mode
(run date, build, expected result in one functional sentence ≤ 40 words, N/N
passed). Never one expected clause per test function. Manual cards use the step
table # / Description / Expected / Observed. A table of named datasets is cited
by the cards. Verdict is binary (OK / KO / Not run); an expected failure is OK
with a known anomaly listed in the VDD. The rationale section states the verdict
rules and justifies each derogating test case. Clinical-validation and usability
cards reduce to ID, status and a reference to their report.

**Evidence.** A generated annex, separate document: run metadata and the matrix
test case → test module → passed / failed. No per-function list (it leaks
excluded code and buries the reader); the full JUnit is archived with the
release. Bound run = release build, clean tree, in the image, no unmapped
failure, no TODO.

**Automated test report (8–10 pages, ≤ 1,200 words).** Four chapters: CI
platform with a diagram and the repeatability / reproducibility properties;
local platforms in two sentences; results = acceptance criterion, a 3-row
synthesis, reference to the release package, conclusion. No per-module table,
no traceability, no package versions.

**Known anomalies.** Listed in the VDD only (IEC 62304 §5.8.2–5.8.3), with a
reference to the risk file — never in the SDD or the test report.

## Methods (algorithm description and verification)

**Algorithms.** Write values, never configuration keys ("10 mm", not
`motion_dl_deadband_px`). Each step ≈ 250 words: purpose, principle, what is
rejected; no "Specified by / Designed in" blocks, no parameter tables (trace lives
in SRS and SDD). About ten figures (workflow, examples of each major step, curves,
maps, a QC refusal). Output formatting is two sentences, not a method.

**Results belong here.** One "Performance verification" subsection per major
component (dataset, n, metric, result) and a pilot chapter with the main results
table and a conclusion, plus a reference to the clinical report for detail.
Figures are injected by the generator from the same metrics files the clinical
report reads — duplication without divergence; never typed by hand.

**Machine-learning components.** Every ML component (including one embedded in a
pre-processing step such as motion correction) gets Goals / Architecture (figure)
/ Training data (source, n, vendors, separation from test data) / Training
workflow / Performance verification. Facts come from the team that trained the
model: prepare the sections and a question list, never invent; open TODOs block
the submission.

**Data and ground truth.** A datasets table (source, n, vendors, use:
development / verification / validation, declared independence) and one
subsection per ground truth: who established it, how, qualification; ground
truthers and data providers in an annex. "Reference software", never a
competitor name.

## User manual, VDD, DICOM conformance, integration guide

**User manual.** The TF slot is a 3–6-page cover listing the User Guides by
market and language; each User Guide is a separate product-format document
written for the clinician, covering the PMAP labelling rubrics (intended use,
description, cautions and warnings, requirements for use, integration, security,
lifetime, legal, complaints, contact, performance summary), 12–15 pages.
Prerequisites are clinical acquisition criteria; processing time is one sentence;
exit codes, container hardening and ingestion limits belong to the integration
guide; third-party software = reference to the SBOM; never a "sources of this
manual" section or a repository path. Lifetime and performance are filled before
signature. Displayed-text quotations (warnings, reading the outputs) are kept.

**VDD (13–15 pages, ≤ 2,000 words).** Corrected issues = one sentence and a
reference to the test report; known anomalies = open ones only, one sentence each
with clinical effect and workaround, no ticket or test name; vulnerabilities =
three sentences (count, criticality, conclusion) and a reference to the OTS
assessment; configuration = settable options in prose. Never internal dataset
names, CI jobs, or anything from excluded code.

**DICOM conformance statement.** Refer to a common company DCS only when it is
verified to cover every IOD the device emits. Otherwise a standalone PS3.2
document ≤ 10–12 pages: one attribute table per IOD, no series-selection logic,
no private JSON schema, no special-case comments, no SRS reference.

**Integration guide.** Cover referring to the common container-integration
document plus a 3–5-page device addendum (resources, folders, ingestion limits,
exit codes, image digest and UDI, logs, permitted settings) when the device
follows the common contract; never an entry-point path, uid, base image, SRS/TC
column or verification table.

## Clinical and bench performance reports

**Clinical validation report (30–40 pages + image annex).** Skeleton: introduction
with explicit objectives; intended use quoted; methodology (material; data with
sources, inclusion/exclusion, protocol, independence from development; reference
standard; statistics in bullets); results (data distribution, primary endpoint,
secondary endpoints, stratification on ≥ 4 axes, discordant cases in an appendix
with a cause per case, processing time); affirmative conclusion. Numbered tables,
no teaching prose. Substantial-equivalence argument belongs to the 510(k) SE
section; engineering step reviews to the test report; image plates to an annex.

**Acceptance criteria.** Pre-specified, dated and signed before the validation
data are scored, derived from the predicate and literature, never from the
device's own results; applied to a cohort never used in development. Cohorts seen
during development are supporting evidence, declared as such. A pre-specification
date is never backdated. Add a reader study only when the claim or the predicate
needs one.

**Bench report.** Separate, ≈ 12 pages, device vocabulary, no code names; a
criterion that expects a bias states why. Counts reconcile across the test case,
the report and the tables; a statistic undefined on the data (e.g. ICC with zero
reference variance) is not printed.

## Usability, labels, lifetime, declarations, reviews, model card

**Usability engineering file (≈ 14 pages).** Short use specification in a/b/c
lists with resource requirements; 3–4 use scenarios of 5–6 steps, no internal
IDs; hazardous situations = one sentence referring to the risk table's usability
tab; UI specification by reference to the SRS. No task may imply a clinical
decision the device does not claim (e.g. treatment selection). Service or
traceability activities are not use scenarios. Summative protocol (≈ 14 pages)
organised by scenario with participants, cases, environment, data and criteria in
≈ 300 words, never development preconditions; it is conducted before submission.

**Labels.** Deliver the artwork (front, translated texts), not a specification.

**Expected lifetime.** One page: duration and a 3–5-sentence rationale tied to
the support windows of the base OS and interpreter, and to the corrective
releases that keep them supported. Check the base image's support end against
the claimed duration.

**Declarations (e.g. animal origin).** A signed letter, no TF apparatus.

**Design reviews.** A workbook, one tab per phase, header with an independent
reviewer and participants, checklist OK/KO/NA/Comments/Action, filled from
reviews actually held. Never prose about missing reviews.

**Model card.** One CHAI card at device level covering every ML component, with
key metrics including stratified (fairness) results; no gap-tracking preamble.

## Standards checklists (IEC 62304, 82304-1, 81001-5-1)

One row per "shall" sub-clause with the normative text; verdicts Yes/No (62304,
82304) and C/PC/NC/NA/NE (81001); a QMS-covered clause is "Yes" citing the
procedure; evidence = document number and section. No section describing how the
checklist is built, no open-points chapter, no "Open point:" in cells (gap
tracking stays internal; at issue there is no partial or open verdict). 81001
includes the normative Annexes F and G and a Gap/Notes prose column. Landscape,
Regulatory Affairs header.

## Requirement cartouche (rendering)

Every requirement (MAP and SRS) is rendered as the approved cartouche: the
identifier on a grey band (bold navy), the title in italic navy indented, the
text in blue without spacing, a blank line, the version line in black at body
size, then a 6-pt grey closing rule after the version line or after the tables
that follow it, and a blank line. The pandoc `custom-style` names must equal the
style names of the reference document (`RequirementId`, …): pandoc maps them by
name, and a mismatch makes it append an empty twin style that Word renders
instead.

## Changelog of the rules

- 2026-10-07 — transverse rules, PMAP, requirement cartouche (CINA-CTP review,
  decisions S00.1–S00.11).
- 2026-10-07 — PMP (decisions S01.1–S01.10).
- 2026-10-07 — Risk management (decisions S05.1–S05.16).
- 2026-10-07 — SRS (decisions S06.1–S06.8).
- 2026-10-07 — SDD (decisions S07.1–S07.5).
- 2026-10-07 — STP, STDR, STR (decisions S08.1–S10.2).
- 2026-10-07 — Methods (decisions S12.1–S12.4).
- 2026-10-07 — SUM, VDD, DCS, integration guide (decisions S13.1, S14.1, S15.1, S36.1).
- 2026-10-07 — clinical and bench performance reports (decisions S18.1–S18.4).
- 2026-10-07 — usability, labels, lifetime, declarations, reviews, model card (decisions S21.1–S37.1).
- 2026-10-07 — standards checklists and transverse rules T1–T7 (decisions S29.1, T1–T7); arbitration closed.

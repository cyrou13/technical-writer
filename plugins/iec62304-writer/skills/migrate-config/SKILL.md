# Skill: migrate-config

## Purpose

`/doc-migrate` audits the gap between a **target repo initialised with an older
version of the plugin** and the **current scaffold**.  It is distinct from
`/doc-init --update`, which re-copies tool scripts; this skill only deals with
the configuration and documentation files that are never auto-overwritten
because they carry user-edited content.

### Why a separate skill from `/doc-init --update`?

`/doc-init` handles the **initial scaffold** (create-if-absent semantics) and,
with `--update`, refreshes tool scripts.  Neither operation touches
`dt-config.yaml` or `docs/dt-clinical-context.md` — those files belong to the
user's QMS and must never be overwritten.

`/doc-migrate` fills the complementary need: after a plugin upgrade introduces
new top-level keys in `dt-config.yaml` (e.g. `external_resources`,
`test_results_path`) or new narrative anchors in `dt-clinical-context.md`
(e.g. `## end-users`, `## characteristics-affecting-safety`), the user needs a
safe, additive way to bring their existing files up to the current schema
**without losing any of their own content**.

---

## The four audit sections

### A — `dt-config.yaml` additive diff

Compares the top-level keys of the user's `dt-config.yaml` against the current
scaffold template.

- Keys **present in scaffold but absent** in user file → reported as ADD.
- Keys **present in user file** → preserved as-is, never touched.
- In `--apply` mode: missing keys are appended verbatim (copied from the
  scaffold, preserving all comments) below a datestamped separator comment.

**Implementation note:** the tool uses verbatim block-copy rather than
parse-then-emit YAML to avoid destroying comments and formatting that the user
may have added.  This is intentional and documented in the script.

### B — `docs/dt-clinical-context.md` additive diff

Compares `## <anchor>` headings in the user's clinical-context file against
the scaffold.

- Anchors **present in scaffold but absent** in user file → reported as ADD.
- Existing sections → never modified.
- In `--apply` mode: missing sections are appended at the end of the file,
  preceded by an HTML comment `<!-- Added by /doc-migrate on <date> -->`.

### C — Items frontmatter completeness (read-only)

For each item category (MAP, SRS, SDS, TC, RSK, PRSK, THR, USC, URSK):

1. Reads the current template `scaffold/docs/templates/<cat>-item.template.md`.
2. Extracts expected frontmatter keys via `parse_yaml`.
3. For each existing item under `docs/items/<CAT>/`, lists frontmatter keys
   that are present in the template but absent from the item.

**This section is strictly read-only.**  The tool never modifies items.
The user must edit items manually, or delegate to an agent:

```
@risk-analyst refresh RSK-AUTH-003   # re-generates a single item
```

The rationale: item frontmatter may be intentionally sparse (e.g. a MAP item
has no `severity` field).  The tool reports the gap; the human decides.

### D — `tools/build_*.py` script audit

For each `build_*.py` script present in the scaffold:

- **MISSING**: the script does not exist in the target repo's `tools/`.
  Recommendation: run `/doc-init --update` which copies all scripts.
- **OUTDATED**: the script exists but its byte size differs from the scaffold
  version (proxy for a content difference — avoids running `diff` on binary or
  large files).  Recommendation: run `/doc-init --update`.

---

## Additive-only semantics

The tool **never overwrites** existing content:

| File | Mode | Behaviour |
|---|---|---|
| `dt-config.yaml` | dry-run | Reports missing keys |
| `dt-config.yaml` | `--apply` | Appends missing keys only |
| `dt-clinical-context.md` | dry-run | Reports missing anchors |
| `dt-clinical-context.md` | `--apply` | Appends missing sections only |
| `docs/items/**/*.md` | always | Read-only, reports gaps |
| `tools/build_*.py` | always | Read-only, recommends `/doc-init --update` |

---

## Limits

- Section C identifies schema gaps but does not fill them.  If a template
  adds a required field (e.g. `initiating_causes` in `rsk-item.template.md`),
  the user or an agent must add it to each affected item.
- The script size comparison in section D is a heuristic, not a content diff.
  If two versions of a script have the same byte count but different content,
  the discrepancy will not be detected.  For authoritative refresh, always use
  `/doc-init --update`.
- YAML comment preservation in section A relies on verbatim block-copy from
  the scaffold.  Comments added by the user **above** existing keys are
  preserved (those lines are not touched).  Comments the user added
  **inside** a block that is being appended are not affected (the block did
  not exist yet).

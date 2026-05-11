---
id: USC-XXX-NNN
title: [TODO] short title ≤ 80 characters
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
persona: [TODO user role, e.g. radiologist, operator, admin]
environment: [TODO usage environment: reading room, clinical console, browser]
task: [TODO business task accomplished, e.g. validate a case]
frequency: Occasional       # Rare | Occasional | Frequent | Continuous
criticality: Medium         # Low | Medium | High (impact if the task fails)
source:
  - [TODO path/to/UI/component]
links:
  parent: []
---

## Persona

[TODO role, experience level, typical context]

## Preconditions

- [TODO system states required before the task]

## Normal usage sequence

1. [TODO step 1]
2. [TODO step 2]
3. [TODO final step = observable business effect]

## Foreseeable use errors

(Informal — those with impact become URSK items linked via
`links.use_scenario`.)

- [TODO error 1]
- [TODO error 2]

## Notes

[TODO additional context, user documentation references]

# Project Management Plan — narrative sections

<!--
The prose of the Project Management Plan (…-10-001-PMP), read by
tools/build_pmp_export.py (a reference exporter synced from the CINA-CTP
repository, see tools/README.md). One `## anchor` per block; the exporter places
each block under its chapter of the house PMP. `{PRODUCT}` is replaced by
`document.short_name`.

The facts of the plan (team, WBS, planning, suppliers, references, procedure
numbers) are NOT written here: they are the `project_management:` block of
dt-config.yaml, rendered from there.

The blocks below are the house text of the Avicenna PMP (CINA-CSpine, CINA-CTP).
Keep them unless your QMS says otherwise; replace every [TODO …] with the
project's own fact — the release gate refuses the document until you do.
-->


## document-overview

This document defines the management rules for the CINA software suite project, specifically {PRODUCT} intended to develop and market the {PRODUCT} device. These rules have to be applied by all the personnel of Avicenna.AI involved in the project.

This plan covers the following goals:

- Describe the organization and the processes to settle for the {PRODUCT} project.
- Ensure the coherence of all tasks and their corresponding responsibilities.
- Define the flows of information, communication, reporting and decision in Avicenna.AI structure.
- Describe the steps taken to control the following goals: technical performances, security and safety issues, costs and planning.

## abbreviations

| Abbreviation | Meaning |
|---|---|
| PMAP | Project Master Plan |
| PMP | Project Management Plan |
| SDP | Software Development Plan |
| SRS | Software Requirements Specification |
| WBS | Work Breakdown Structure |

[TODO complete the abbreviations the plan uses]


## glossary

**Validation (FDA):** Establishing documented evidence, which provides a high degree of assurance that a specific process will consistently produce a product meeting its predetermined specifications and quality attributes. Contrast with data validation.

**Verification, software (FDA):** In general, the demonstration of consistency, completeness, and correctness of the software at each stage and between each stage of the development life cycle.

**Waterfall model (IEEE):** A model of the software development process in which the constituent activities, typically a concept phase, requirements phase, design phase, implementation phase, test phase, installation and checkout phase, and operation and maintenance, are performed in that order, possibly with overlap but with little or no iteration. Contrast with incremental development; rapid prototyping; spiral model.


## conventions

N/A

## organization-intro

The section describes the organizational structure of the {PRODUCT} project, the responsibilities and the flows of internal information.

## team-relationships

Each member reports to the Project Manager.

Considering the size of the team, no other rule is issued for the information flow, except the diffusion of project documentation described in §4.2 of this document.

## wbs-intro

The Work Breakdown Structure of the {PRODUCT} project identifies all the tasks mandatory to the development of the {PRODUCT} product.

The structure is detailed to the third level in order to define the concept of generic task at higher levels. The codification of the tasks is composed of:

## wbs-rules

The codification is unique, coherent and stable in the timeframe of the project.

The WBS is described in the current document and submitted to configuration management. The WBS is updated as many times as necessary during the lifecycle of the project. Each update is approved according to the rules as stated in documentation management (see §4.2).

The follow-up of the project is assured by the tasks at the lowest level.

## resources

The resources necessary for the project are described in the software development plan [R2].

There is no particular resource needed for the project such as a calibrated measurement tool or a simulator. Hence, no specific identification of resources is needed for the project; the hardware and software resources are interchangeable COTS.

## end-user-involvement

In a general manner, users are involved since the early stages of the project, through members of the scientific board and the Chief Medical Officer.

- Before project launch: user's needs are collected to define the perimeter of future devices,
- Specifications and conception: if applicable mockups of the devices are presented to users to see if they meet their needs.
- Testing: selected end-users eventually test beta version of products.

## subcontractor-notes

[TODO what the project does NOT subcontract, and why (e.g. no annotation supplier when no human-established ground truth is used); delete this block if nothing]


## other-teams

N/A

## communication

The information flows between the project members are mainly handled by:

- Project documents diffusion (see §4.2),
- Mail messaging and other network vectors,
- Meetings and Reviews.

If time allows the Minutes of Meetings (MoM) will be prepared and reviewed by the parties before the meeting is considered as completed. If this is not possible, the MoM will be forwarded for review within 5 working days.

## reviews

The development process is organized into different phases and all of them end with a review as detailed in the Software Development Plan [R2].

Four types of reviews occur during the project:

- Launch review
- Design Reviews
- Tests Review
- Validation review

Launch Review is a formal, documented and systematic meeting during which the project team members get acquainted with the goals of the project. All information about the project shall be contained in the project management plan.

Design Reviews are formal, documented and systematic meetings during which the current design of a product (system, sub system etc.) is reviewed and compared with the requirements. Design Reviews are scheduled in the project planning. The objective of Design Reviews is to critically appraise the design and development in accordance with the requirement, and to confirm and approve technical aspects.

Test Reviews are formal, documented and systematic meetings during which the current design of a product is tested. Tests reviews are scheduled in the project planning.

Validation Review is a formal, documented and systematic meeting during which the Project manager validates the devices. This review contains also a part devoted to the return on experience on progress of the project and on the processes used during the project.

The validation review includes the Design transfer review.

## external-communication

Every member of the project team shall refer to the Chief Executive Officer before engaging a communication with a third party who is not involved in the project.

## software-configuration

Please refer to the Software Configuration Management Plan [R3].

## documentation-configuration

This section presents the documentation management rules for all documents sent or received during the {PRODUCT} project.

The documentation management aims to create, identify, approve, distribute, classify and archive the documents of the project.

## documentation-confidentiality

The documents or information of confidential nature are communicated to the members of the project only according to the needs of the project.

## tools-validation

The software tools used during the project that may affect the conformity of the product to its requirements are identified and validated in accordance with the QMS requirements for the validation of software used in the quality management system (ISO 13485 §4.1.6). [TODO where the list of tools, their intended use and the extent of their validation is kept, and under whose responsibility]


## development-management

Information related to:

- software development process,
- software development tools and their obsolescence management,
- software development rules and standards,

are detailed in the Software Development Plan [R2].

## life-cycle-model

The software life cycle model chosen for the project is the waterfall model. The life cycle is defined with compliance to the IEC 62304:2006/A1:2015 standard.

The waterfall model was chosen for the reasons below:

- No need of iteration: the results of the research phase are profitable enough to define the final product along a straightforward path.
- Short timeframe: the project is limited to less than one year. Iterations can introduce a delay which is not acceptable.
- Limited number of participants: the limited number of participants reduces the burden of the reviews. Hence, reviews happening during the waterfall cycle do not penalize the progress of the project.

## machine-learning-component

[TODO the machine-learning components of the device, if any: what each does, that it is locked, who manages its datasets, how a model change is handled, and the EU AI Act qualification (stated in the PMAP, not decided here). Write "N/A" if the device holds no learned model.]


## tests-intro

The test phase of the software is divided into 3 phases:

- Software Verification tests
- Software Validation tests
- Software Clinical evaluation

Verification and validation phases end with the validation review of devices.

## verification-tests

- Goal: Verification of {PRODUCT} in factory.
- Tasks: Execution of the tests described in the software test description document [R9], according to the conditions described in the software test plan [R8]. Redaction of the software tests report.
- Input data: Tests plans (STP and STDR), {PRODUCT} software (locked version after the end of the coding phase).
- Output data: Software Tests Description / Report (STDR), {PRODUCT} Version Delivery Document and Software Documentation as stated in VDD.
- Acceptance criteria: all the tests described in the Software Test Description must be successfully executed unless the project manager issues an exemption.

## validation-tests

- Goal: To confirm, through the provision of objective evidence, that all the requirements for the {PRODUCT} intended use have been fulfilled.
- Tasks: [TODO the validation activities and the report that describes them (e.g. standalone performance testing, reader study, usability summative evaluation)]
- Input data: [TODO protocols], {PRODUCT} software (locked version after design and verification), Version Delivery Document and Software Documentation as stated in VDD.
- Output data: [TODO the validation report(s)], summative usability evaluation and the software validation report.
- Acceptance criteria: [TODO the validation report] demonstrates that the software performs according to its intended use and that all the requirements for the {PRODUCT} intended use have been fulfilled.


## clinical-evaluation

- Goal: To confirm that the safety, performance and effectiveness of the software are supported by available data.
- Tasks: Execution of the clinical evaluation as described in the Clinical Evaluation Plan/Report [R11].
- Input data: clinical evaluation protocol, {PRODUCT} software (locked version after design and verification), Version Delivery Document and Software Documentation as stated in VDD.
- Output data: Clinical Evaluation Report.
- Acceptance criteria: The Clinical Evaluation Report demonstrates that the software performs according to its intended use and that the safety, performance and effectiveness of the software are supported by available data. Moreover, the risks associated with the use of the software are acceptable when weighted against the benefits in clinical practice.

This phase is in relation to the requirements for CE-marking under the Medical Device Regulation (MDR).

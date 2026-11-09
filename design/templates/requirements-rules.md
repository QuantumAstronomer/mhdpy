# Rules of the requirement documents

Each component of mhdpy is specified by its requirements before it is built (§2.5). This file explains each part of the skeleton `requirements.md` and the reason for it, how requirements are named and how tests and code cite them, and how a requirement document is agreed and changed. Section signs refer to CLAUDE.md, and plain numbers to the parts of this file. In the skeleton, braces mark values to fill in, and italic lines describe the prose that replaces them.

## 1. Files and identifiers

A component has one requirement document in `design/requirements/`, named by the component in lower case, with hyphens and without articles or commas, as `riemann-solvers.md`. The document is written once the briefs of the component's layer are decided, and before the component is built (§2.3).

A requirement is identified by the prefix of its component followed by a number of two digits, without a hyphen, as RIEM04. The prefix is a short mnemonic of capitals alone, chosen when the document is begun, named in its head and used by no other component, so that the number that follows it is never read as part of it. The number is given when the requirement is written, padded to two digits so that the identifiers sort in order, and is never reused. A prefix stays with its requirements: if a component is renamed or split, its requirements keep their identifiers, and a new component takes a new prefix. Every citation thus keeps the meaning that it had when it was written.

Documents cite a requirement by a link whose text is its identifier, to the anchor before it, as `[RIEM04](../requirements/riemann-solvers.md#riem04)`. A test names the requirements that it checks at the start of its docstring, as "Checks RIEM04 and RIEM05." (§2.5). Code names the requirements that a function implements in its docstring, as "Implements RIEM04.", and a single line that carries one in a comment beside it, as `## RIEM04`, so that the reasoning that the code leaves out is one search away (§3.2). Commit messages cite requirements by their identifiers alone.

## 2. The head and the scope

The title names the component. Three lines follow. The prefix gives the mnemonic of the requirements. The status reads "Draft." while the document is written, and "Agreed on {date}." once the author has agreed it, with the date of the latest agreement after a change (5). The line on briefs names, with links, the sub-decisions that the component implements.

The scope says what the component does and what it leaves to other components, its inputs and outputs, the terms that its requirements use, a tolerance such as round-off among them, and the components that it relies on. As the terms are defined once, each requirement can be short.

## 3. The requirements

The requirements are grouped by the functions or operations of the component, in the order in which their tests and code are written (§2.6), each group under a heading of its own. A last group, Verification, holds the requirements of [§1.3 of the overview](../overview.md#13-success-criteria) on the component as a whole: its order of convergence on smooth problems, its conservation to round-off where the boundaries permit, and the reference tests of its topic that it reproduces. A physics component is complete only once this group passes (§1.3 of the overview).

Each requirement is one paragraph, preceded by its anchor and opened by its identifier in bold. The first sentence is the statement: one requirement that a test can decide (§2.5). It uses "shall", which sets it apart from the reason that follows, as in ISO/IEC/IEEE 29148. Where the requirement holds only under a condition, the statement takes the matching pattern of EARS: "When {trigger}, the {component} shall {response}.", "While {state}, the {component} shall {response}.", or "If {unwanted condition}, then the {component} shall {response}." A requirement that always holds needs no pattern. A numerical statement names its tolerance or range, as an order of convergence between 1.9 and 2.1 or a flux equal to the physical flux to round-off, so that the test has a threshold to decide by. A requirement on speed takes its threshold from an experiment, less a margin for the spread between runs, and names the machine and the statistic, the median of repeated calls after a warm-up. Its test runs only on that machine.

The rest of the paragraph is the reason: why the requirement holds, in a few sentences, with links to the sub-decisions, experiments and topic sections that it rests on. It holds the reasoning that the code cites and leaves out, so that docstrings and comments can stay short (§3.2). Formulas stay in the topics and syntheses, which the reason links.

A requirement states only what a decided sub-decision chose, or what follows from it. Where it would contradict a decided sub-decision, the work stops and names the sub-decision, and a new brief supersedes it first (§2.4). Where it would make a choice that no sub-decision has made, such as between an error and a floor for a negative pressure, the choice becomes a sub-decision first, of its brief while that is open or of a new brief, as every architectural choice is made in a brief (§2.4).

## 4. Writing

Requirement documents follow §3.1, as the briefs do. A reason rests on the briefs, topics and syntheses that it links, which carry their own marks. A fact that it rests on and that none of them gives is marked **[GK]**. Sources cited directly, rather than through those documents, are listed at the end in the format of the topic summaries, a part left out otherwise.

## 5. Agreement and change

A requirement document is agreed with the author before its tests are written (§2.5), after which its tests and code follow one piece at a time (§2.6). Once agreed, a change of wording that keeps the meaning is made in place. A change of meaning withdraws the requirement and adds a new one with the next number. The withdrawn paragraph stays and opens with "Withdrawn on {date}, replaced by RIEM09." or, where nothing replaces it, with the reason. The tests and code that cite it move to its successor. Every change is agreed with the author, and the status line records the date of the latest agreement.

Which tests name which requirements is derived from the tests themselves, never kept by hand, so that no second list can drift. A small check, built with the tests of the first component, lists each requirement with its tests, the requirements that have none, and the tests that cite a withdrawn requirement.

## 6. Sources

**[GK]** The statements follow the characteristics of a good requirement in [ISO/IEC/IEEE 29148](#iso-29148) (2018), singular and verifiable among them, and its use of "shall". Their conditions follow the patterns of EARS, the Easy Approach to Requirements Syntax of [Mavin et al.](#mavin-et-al-2009) (2009).

- <a id="iso-29148"></a>ISO/IEC/IEEE 29148:2018, Systems and software engineering, life cycle processes, requirements engineering, second edition (2018), [iso.org/standard/72089.html](https://www.iso.org/standard/72089.html).
- <a id="mavin-et-al-2009"></a>Mavin, A., Wilkinson, P., Harwood, A. and Novak, M., Easy approach to requirements syntax (EARS), 17th IEEE International Requirements Engineering Conference, 317–322 (2009), [doi:10.1109/RE.2009.9](https://doi.org/10.1109/RE.2009.9).

# Overview of mhdpy

*A paragraph on what mhdpy is, for a newcomer, and on what this overview holds and for whom: the goals, the context of a run, the layers and how a step runs through them, what the layers share, and the briefs that build them. About 80 words with the line below.*

**Where the work stands.** *The stratum in progress and its next brief, as part 6 lists them.*

## 1. Goals

*The goals, scope and success criteria of mhdpy, moved from §1.1 to §1.3 of CLAUDE.md in step 7 of `design/overview/plan.md`, with a pointer to the priorities, which stay in §1.4 of CLAUDE.md. About 500 words.*

### 1.1 Goals

### 1.2 Scope

### 1.3 Success criteria

## 2. Context of a run

*What a user brings to mhdpy, a problem setup with its parameters, what a run does with it, and what comes out for analysis, on the development machine and a small server. About 150 words.*

## 3. Layers

*The diagram of the five strata, each with its components, and a key, written by `design/overview/layers.py` into `design/overview/layers.svg`, then a paragraph on how the strata are cut and built. One subsection to a stratum, set in step 5 of the plan: what the stratum holds, what it must provide to the strata above, and the tests that close it. About 1,250 words.*

## 4. One time step

*One step of the production run, with hydrodynamics, radiative cooling, thermal conduction and a passive scalar, traced down through the strata in numbered steps, each naming its stratum, with each choice of method left to its brief and linked to its topic. About 250 words.*

## 5. Crosscutting concepts

*What every stratum shares and no stratum holds, settled with the cut in step 5 of the plan, a sentence or two to a concept, each with the brief that settles it. About 300 words.*

## 6. Briefs

*One subsection to a stratum, in the order of part 3, with a table of its briefs in the order in which they are opened, then a line on its requirements and code. A brief not yet opened is listed by its subject, since it receives its identifier only when it is opened. About 300 words.*

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| *Identifier, once opened* | *Subject* | *Topics, linked* | *Not begun, open, or decided on {date}* | *What the brief changed, with a link to the sub-decision* |

*Requirements: each document of the stratum, with its status, draft or agreed on {date}. Code: not begun, in progress or complete.*

## 7. Glossary

*The terms that a newcomer meets, in alphabetical order, each with an anchor, a sentence of explanation and its topic linked. The first use of a term in the text links to its entry. About 250 words.*

## Sources

*The established practice that the overview follows and the references that it cites directly, as anchored entries in the format of the topic summaries.*

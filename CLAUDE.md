# mhdpy

This file sets out the purpose of mhdpy, the way of working, and the conventions of its documents, code and figures.

## 1. Purpose

Goals, scope and success criteria move to the overview of the layers (§2.3) once it is written. The priorities of §1.4 stay here.

### 1.1 Goals

mhdpy is a framework for astrophysical (magneto)hydrodynamical simulations in Python. It is a hobby project, by an author who used Athena, then a state-of-the-art MHD code, for a bachelor thesis. It serves educational and scientific work, from standard verification problems to production-scale runs of the size used in published studies. These aims can conflict, so §1.4 ranks them.

The main goal is **learning**. This means learning to write scientifically applicable code, whose physics is demonstrably correct and extensible. It also means learning to build a large, multi-layered software project robustly, in a form that others can pick up easily.

The second goal is **production-scale runs**. The project grew out of earlier work with production-grade MHD software, on simulations of the scale of [Armillotta, Fraternali and Marinacci (2016)](https://ui.adsabs.harvard.edu/abs/2016MNRAS.462.4157A/abstract). Those follow Galactic fountain clouds that lead to coronal condensation, which feeds star formation, on a grid of roughly $4096 \times 1024$ cells without mesh refinement.

### 1.2 Scope

The eventual scope is every physics module that state-of-the-art (magneto)hydrodynamics codes such as Athena++ implement, with a focus on astrophysics. It ranges from compressible hydrodynamics with general equations of state to Lagrangian particles for dust. This whole scope shapes the architecture from the start, also for parts that are built much later. The lower layers must accommodate those parts without significant redesign.

### 1.3 Success criteria

Success is judged by four criteria, each stated so that it can be checked rather than asserted. Learning is deliberately not among them. It is no property of the finished code, and is served by the way mhdpy is developed instead (§2).

**Correctness.** No physics module is complete before it is verified against problems with known solutions. For smooth problems, the measured order of convergence matches the formal order of the scheme. For problems with discontinuities, results are compared with exact or reference solutions. Conserved quantities are conserved to round-off wherever the boundary conditions permit. The test problems are those of the suites of state-of-the-art reference codes, and a capability counts as implemented once its reference tests are reproduced.

**Production capability.** mhdpy completes a research-scale run like those of Armillotta et al. (2016) on the development machine and on a small multi-core server, within a time still to be set. Such a run is two-dimensional, with hydrodynamics, radiative cooling, thermal conduction and a passive scalar for the metallicity. The cost of a run is set roughly by its total number of cell updates. The rate of cell updates per second is therefore the measure tracked during development.

**Extensibility.** New physics modules, such as another cooling function or a new Riemann solver, are added without changes to the framework. Every module beyond the hydrodynamics core tests this criterion, since it plugs in through the same interfaces.

**Usability.** mhdpy installs on macOS and Linux with a single `pip` or `uv` command. A newcomer then runs a standard test problem within minutes by following the documentation.

### 1.4 Priorities

The goals pull in different directions at times, and the decision briefs resolve such conflicts with one ranking. Correctness comes first. A wrong result has no value, however fast or readable the code behind it. Performance comes second, since production-scale runs are a clear target, and readability gives way where performance requires it. Readability comes third. The code must stay understandable to serve the learning goal, and code that is hard to understand is also hard to maintain and extend. Extensibility and usability come last: the interface gets less focus, although it is not ignored.

One exception overrides the ranking. Installation is as simple as possible, preferably a single `pip` or `uv` command. Every recommendation in a brief states where it falls in this ranking.

## 2. Way of working

The way of working guards against two ways of losing hold of the project: steps that bring more than can be absorbed before the next one begins, and code that comes prepared and is then followed rather than designed.

### 2.1 Roles

The author makes every decision. The assistant recommends, and explains the reasoning behind each recommendation, since learning is the main goal. Where the author's input is needed, or the assistant is unsure, it asks rather than assumes. It asks questionnaire-style, one decision per question, also about the points it reports for review.

The assistant writes the documents, such as briefs, requirements, syntheses, summaries and templates, and the experiments (§2.4). It changes the repository only when asked for that step, and an earlier request does not carry over. It keeps nothing in a private memory. Whatever has to last is written into the repository.

Nothing is committed or pushed without the author's explicit approval. For each commit, the assistant proposes a summary of the change, the files changed and the commit message exactly as it will be committed, and commits once the author approves. An approval holds for one commit only. A push needs an approval of its own.

### 2.2 Small steps

Each step is small enough to be understood before the next one begins. This holds for documents as much as for code. A step that brings more than can be absorbed is split.

### 2.3 Order of work

The reference material is digested first, in a synthesis per reference and then a summary per topic (§4.1), and the templates are designed next (§3.4). An overview then sets out the layers of the architecture and what each of them holds, drawing on both. This has to be clear from the start, since briefs of higher layers can change what a lower layer must provide. The layers are then built one at a time: the briefs of a layer, then its requirements, then its code, before the briefs of the next layer.

Redoing work is to be avoided. Building pieces without a use in the near future is worse, as it leaves unclear why they are built at all. A provision for a later layer is therefore built now only if it costs little. Larger provisions wait until their use is near.

### 2.4 Decision briefs

Every architectural choice is made in a decision brief, one topic at a time. A brief gives the background from the reference material (§4.1) and the options. Where the references leave a question open, experiments supply the evidence, each with the smallest code that answers its question. Experiments are not early versions of mhdpy. The recommendation is kept apart from the evidence and states where it falls in the ranking of §1.4. Interesting options that are not chosen are recorded for later. The author tends to trust the solutions of Athena++ as robust and performant.

A brief is worked through one sub-decision at a time. Each sub-decision is written, discussed and decided before the next one is written. A decided brief is frozen, and changing a decision takes a new brief that supersedes the old one. Work that conflicts with a decided brief stops and names the sub-decision concerned, rather than working around it.

### 2.5 Requirements first

Each component is specified by its requirements before it is built. A requirement is one statement that a test can decide. The tests are written after the requirements and before the code, and every test names the requirements it checks. The reasoning behind the code lives in the requirements it cites, so that docstrings and comments can stay short (§3.2).

### 2.6 Writing code

The author writes all code and tests of mhdpy, to understand them. The assistant prepares and explains each step.

Code comes in small pieces, one test or one function at a time, each explained before the next. The test code always comes first. Code is given as plain blocks ready to type, never as diffs or patches, and a changed function is given whole. Nothing is left for the author to fill in. The assistant first tries each step in a scratch copy, so that the code is known to work, and afterwards checks the author's version against it. The scratch copy lives in `.scratch/`, which git ignores.

Once a component is finished, and before the next one starts, the author explains it in a few sentences. The assistant then points out any gaps in that explanation.

### 2.7 Text

Texts read as prose, with lists only where they help, and without words added for the sake of length. This holds for documents, docstrings, commit messages and chat replies alike. Of §3.1, chat replies keep only the British spelling and the inline LaTeX. They address the author directly. The assistant reviews each text before showing it and removes whatever is superfluous or adds no value. The author guides this where needed.

## 3. Conventions

### 3.1 Writing

Documents use a passive, scientific voice and name neither the author nor the assistant. Where an agent is needed, the text says "the author". This file is the exception, as it names the assistant. Sentences are short, without contractions. Spelling is British: discretisation, licence, centred. Mathematics is typeset in inline LaTeX (`$...$`), never as Unicode symbols and without displayed equations. A fraction is written with a slash where that reads better in a sentence. In briefs, syntheses and summaries, anything not taken from the reference material is marked **[GK]**, for general knowledge.

### 3.2 Code

The author develops the code style as the code grows. It follows the PEPs, PEP 8 in particular, though not so strictly that the code stops feeling like the author's own. Automatic formatting and linting stay off for now, since they remove whitespace that helps legibility. The starting points are lines of at most 120 characters, `##` for comments to people and `#` for directives to tools, and strict type checking with pyright. The layout of docstrings is developed in the same way.

A comment that explains how a step works is a short line, not a paragraph. Docstrings may be longer, but do not explain over several paragraphs. The reasoning belongs to the requirements the code cites.

### 3.3 Figures

Colours are used in this order: black, red (`#cc0000`), darker reds (`#7a0000`, `#450000`), then greys (`#555555`, `#8c8c8c`, `#bdbdbd`), with a lighter red (`#e57373`) as a last resort. Black and grey show reference or lower-order results, red the main result. Series are solid lines, told apart by colour and marker. Reference slopes are thin, light-grey solid lines, labelled in grey at their right end. The frame is minimal: no top or right spines, a legend without frame, titles aligned left, and 150 dpi.

Figures are always redrawn, never copied. A plotting script of its own reads saved results, so that a change of style does not require the computation to run again.

### 3.4 Templates

The templates of briefs, requirement documents and experiments, the naming of their files and identifiers, and the style of commit messages are designed with the author, before the overview of the layers (§2.3).

## 4. Material and machine

### 4.1 References

`References/` holds the third-party material: the code and papers of Athena and Athena++, Pyro and Ulula, the papers of ZEUS, and Michael Zingale's text on computational astrophysical hydrodynamics (`CompHydroTutorial.pdf`). The folder is read-only, and each part keeps its own licence. The repository ignores the folder from its first commit, so that no commit can include third-party material.

Each folder of `References/` gets a synthesis of its own in `design/references/`, so that Athena and Athena++ share one synthesis. A synthesis is a full digest, readable without the source. It holds an overview of the reference and its scope, its numerical methods, its software architecture and a list of its sources. A reference without material for a section says so in one line. Papers are cited by arXiv identifier, DOI or ADS bibcode, with section and equation numbers, and code by its repository path at a recorded version. Gaps in a reference may be filled, and its claims checked, by web search. What is found is marked **[GK]** and cited, preferably by arXiv identifier, DOI or ADS bibcode. A synthesis is written in its own words, without passages, tables or figures copied from the source. The syntheses are written in the order Zingale's text, Pyro, ZEUS, Ulula and Athena, one source per step: one paper, or one part of a code. The syntheses of Pyro and ZEUS are written in parallel.

A second layer in `design/topics/` condenses the knowledge on one component, such as Riemann solvers or slope limiting, across all references. The topics are agreed with the author once the syntheses are done, and all topic summaries are written straight after them. A topic summary draws on the syntheses and carries over their citations. Where a synthesis falls short, the source is read again and that synthesis is completed first, so that the two layers agree. A topic summary compares the methods and assesses them, with the assessment marked **[GK]**. The choice between them is made in a brief (§2.4).

### 4.2 Development machine

An Intel MacBook with a Core i7-9750H (6 cores, 12 threads, x86-64) and 32 GB of memory, running macOS 26.7, without a CUDA GPU or MPI. Installed are uv, with Python 3.13, 3.14 and the free-threaded 3.14t, as well as git and Docker. Docker runs Linux x86-64 containers natively and arm64 containers through emulation.

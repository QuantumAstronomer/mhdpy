# Plan of the templates

This file records how the templates of §3.4 of CLAUDE.md are designed with the author: what the templates are, the way of working, the steps with their status, and the decisions taken in each step. Section signs refer to CLAUDE.md. The overview of the layers, which follows the templates (§2.3), is not begun here.

## Templates

Three kinds of document get a template: decision briefs and experiments (§2.4), and requirement documents (§2.5). Each template has two files. The skeleton holds the headings of the parts that a document of its kind must have, each with one line on what the part holds, and is copied to begin a document. The rules file explains each part at length, with the reasons for it. Both are kept in `design/templates/`. The naming of files and identifiers and the style of commit messages are conventions rather than templates. They are written into §3.4, as they apply to every file and every commit.

## Way of working

Each template is designed in seven stages, and each stage is agreed with the author before the next begins (§2.2).

1. Use. The author is asked how documents of the kind are written, read and consulted later, and what helped or hindered in reading the syntheses and summaries, so that the template follows the author's habits.
2. Practice. Established practice for documents of the kind is summarised, marked **[GK]**, with what suits mhdpy and what does not.
3. Structure. The template is shown first as an outline, its parts with one line each, and the parts are then decided one at a time.
4. Identifiers. The identifiers that the template introduces are fixed, with the way in which other documents and the code cite them.
5. Draft. The skeleton and its rules file are drafted in `.scratch/templates/`, where the author reads them in full.
6. Trial. The skeleton is filled once with a realistic case in `.scratch/templates/`, and what the trial exposes is corrected. A trial decides nothing and is never committed, so that no brief is anticipated.
7. Commit. The agreed files are written into the repository and committed.

Each decision is put to the author as a question with a recommendation and its reason, one decision to a question and two or three questions to a round, all on the same part (§2.1). Nothing is written into the repository before the author has agreed it. Each step ends in a commit of its own, which also updates the table below, and every commit and every push needs the author's approval.

## Steps

The layout comes first, as every template refers to paths. The brief follows, since experiments and requirements both depend on its sub-decisions, and then the experiment and the requirement document. The naming scheme gathers the identifiers that the three templates fix, and the style of commit messages follows it. A last step reads everything together for consistency.

| Step | Subject | Files | Status |
|---:|---|---|---|
| 1 | Way of working | `design/templates/plan.md` | done |
| 2 | Layout of folders and files | `design/templates/plan.md` | done |
| 3 | Decision briefs | `design/templates/brief.md`, `design/templates/brief-rules.md` | done |
| 4 | Experiments | `design/templates/experiment.md`, `design/templates/experiment-rules.md`, `.gitignore` | done |
| 5 | Requirement documents | `design/templates/requirements.md`, `design/templates/requirements-rules.md` | done |
| 6 | Naming of files and identifiers | CLAUDE.md §3.4 | done |
| 7 | Style of commit messages | CLAUDE.md §3.4 | done |
| 8 | Consistency of the whole | the files of steps 2 to 7 | |

## Decisions

Step 1. The author decided that each template has a skeleton and a rules file, that the conventions go into §3.4, that the structure of a template is shown as an outline first, that a round holds two or three questions, that each template is tried in `.scratch/` before it is committed, and that this file records the work.

Step 2. The author decided that the templates are kept in `design/templates/` and the briefs in `design/briefs/`, without folders for the layers, each brief as one document with a section for each sub-decision. The experiments of a brief are kept in `design/experiments/`, in a folder that bears the name of the brief, with a subfolder for each experiment that holds its document, scripts, results and figures. The requirement documents are kept apart, in `design/requirements/`, since a brief is frozen once decided, while a requirement document lives as long as its component and may draw on several briefs. The names of the folders and files are fixed with the templates and gathered in step 6. A folder for each brief, decided here at first, gave way in step 3 to a single file.

Step 3. The author reads a brief with the topic sections that it links, of which it repeats only the points that matter, and returns to it later for why a choice was made. In the summaries, length and too little on the consequences for mhdpy hindered. Each sub-decision therefore opens with its decision, written last, after the Y-statements of Zdun et al. (2013), and describes each option in prose by what it would mean for mhdpy. The options set aside stay beside their reasons, with what would bring them back, and a sub-decision runs to about 800 words. A decided sub-decision may be revised while its brief is open, a later brief may supersede single sub-decisions, and a superseded brief receives pointer lines as its only edits. A brief is one file, as `B07-riemann-solvers.md`, numbered in the order in which briefs are opened, with a folder of the same name beside it only for its diagrams, which are kept as SVG, drawn by hand or by script, and committed. Its sub-decisions are B7D1, B7D2 and so on. A trial on the order of the axes of the cell arrays (topic 36) led to three further rules: a fact that the reasoning rests on and the references do not give is marked **[GK]**, while the reasoning itself is not; an experiment is run before the recommendation that it serves; and the decision is written in two sentences.

Step 4. The author reads the result of an experiment rather than its code, and its plan comes to the author before any code is written. The record therefore opens with its answer, written last, after the pattern of the brief, and keeps its plan, of the question, an expectation where one can be argued and the method, unchanged once agreed, after the registered reports of Chambers (2013). Timings report the median with the minimum and maximum after a warm-up. Each script declares its environment after PEP 723 and runs with uv, follows §3.2 with strict pyright, and records the versions and the machine that produced its results. An experiment may import mhdpy only from a recorded commit. The layout and visuals of figures, a shared style sheet among them, are planned apart from the templates, as the author decided. Small results and the figures are committed, while raw output is kept out of git by a rule in `.gitignore`. An experiment is identified as B7E1 and kept in `design/experiments/B07-riemann-solvers/E1-cost-of-hllc/`, with its record in `README.md`. A trial in `.scratch/`, run for real on the cost of the order of the axes in NumPy, led to three further rules: plotting scripts relax the one check of pyright that the stubs of matplotlib defeat, results that the plan did not foresee are reported apart, and the question names the measure on which the sub-decision turns.

Step 5. The author opens a requirement document when writing a test or code, when reading code later and when judging a component done, and looks there for the statement with its reason, while formulas stay in the topics. Having written requirements formally before, the author chose statements with "shall", after ISO/IEC/IEEE 29148, in the patterns of EARS where a condition applies, each with its reason in the same paragraph. The requirements are grouped by function, with the verification of §1.3 last. Only the tests name their requirements, at the start of their docstrings, and a check derived from the tests, built with those of the first component, lists the requirements that have none. Code cites requirements in docstrings and, for a single line, in a `##` comment. A requirement is identified by a mnemonic prefix and a number, as RIEM-4, the prefix staying with its requirements, and its document is named by the component, as `riemann-solvers.md`. A change of meaning withdraws a requirement in favour of a new one. A trial on the state arrays of the trial brief led to three further rules: a reason may rest on an experiment, a choice that no sub-decision has made goes to a brief before a requirement states it, and a requirement on speed names the machine, the statistic and the margin of its threshold.

Step 6. The names that the three rules files fixed are gathered in §3.4 as a table of item, identifier and file, between a sentence on the templates and one on citing, and §3.4 is retitled Templates, names and commits, as the author decided.

Step 7. The style that the history practises is written into §3.4: a subject in the imperative of at most 72 characters, without a full stop or a prefix, and a body of prose wrapped at 72 columns in the voice of §3.1. The author decided that a subject names the identifier where a commit concerns one item, that every commit carries the Co-Authored-By line, and that a test is committed with the code that makes it pass, so that every commit passes its tests.

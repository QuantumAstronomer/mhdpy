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
| 2 | Layout of folders and files | `design/templates/plan.md` | in progress |
| 3 | Decision briefs | skeleton and rules file in `design/templates/` | |
| 4 | Experiments | skeleton and rules file in `design/templates/` | |
| 5 | Requirement documents | skeleton and rules file in `design/templates/` | |
| 6 | Naming of files and identifiers | CLAUDE.md §3.4 | |
| 7 | Style of commit messages | CLAUDE.md §3.4 | |
| 8 | Consistency of the whole | the files of steps 2 to 7 | |

## Decisions

Step 1. The author decided that each template has a skeleton and a rules file, that the conventions go into §3.4, that the structure of a template is shown as an outline first, that a round holds two or three questions, that each template is tried in `.scratch/` before it is committed, and that this file records the work.

Step 2, so far. The author decided that the templates are kept in `design/templates/`, that each brief has a folder of its own in `design/briefs/`, without folders for the layers, and that the experiments of a brief are kept in `design/experiments/`, in a folder that bears the name of the brief's folder. Open are where the requirement documents are kept, what the folder of a brief holds besides the brief, and how several experiments of one brief are arranged in their folder.

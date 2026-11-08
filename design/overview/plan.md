# Plan of the overview of the layers

This file records how the overview of the layers (§2.3) is written with the author: what the overview is, the way of working, the steps with their status, and the decisions taken in each step. Section signs refer to CLAUDE.md. The briefs of the layers, which the overview orders, are not opened here.

## The overview

The overview sets out the layers of the architecture of mhdpy and what each of them holds. It covers the whole scope of §1.2 from the start, since briefs of higher layers can change what a lower layer must provide (§2.3). For each layer it names the briefs that the layer needs and the order in which they are opened, as the layers are built one at a time: the briefs of a layer, then its requirements, then its code, before the briefs of the next. It draws on the syntheses in `design/references/`, on the topic summaries in `design/topics/`, above all those on the methods (1 to 27) and on the software architecture (35 to 42), and on the templates in `design/templates/`.

Two rules bear on its form. Every architectural choice is made in a decision brief, which is frozen once decided (§2.4), yet the overview must take up what later briefs change. The overview is therefore a living document rather than a brief, and makes no architectural choice of its own. It is kept in `design/overview.md`, and this plan and any diagrams in the folder `design/overview/`. Once it is written, the goals, scope and success criteria of §1.1 to §1.3 become its first part, while the priorities of §1.4 stay in CLAUDE.md.

## Way of working

Each step is agreed with the author before the next begins (§2.2). Each decision is put to the author as a question with a recommendation and its reason, one decision to a question and two or three questions to a round, all on the same part (§2.1). The structure of the overview is shown as an outline before any part is written, and the cut into layers before any layer is written in full. Each part is drafted in `.scratch/overview/`, where the author reads it in full, and nothing is written into the repository before the author has agreed it. Where a part would need an architectural choice, the choice is named and left to a brief rather than made, and no brief of any layer is opened. Each step ends in a commit of its own, which also updates the table below, and every commit and every push needs the author's approval.

## Steps

1. Way of working. This plan, the form of the overview and where it lives, and where the goals, scope and success criteria go.
2. Use. The author is asked how the overview will be read and consulted: at the start of a layer, while a brief is written, and when a brief changes what a layer must provide.
3. Practice. Established practice for layered architectures and their documents is summarised, marked **[GK]**, with what suits mhdpy and what does not.
4. Structure. The overview is shown as an outline, its parts with one line each, and the parts are then decided one at a time.
5. Cut into layers. The layers are shown as an outline, one line to a layer, drawn from the topics, and the cut is decided before any layer is written in full.
6. Contents of the layers. Each layer is written in a step of its own, numbered 6a, 6b and so on: what it holds, what it must provide to the layers above, the briefs that it needs in their order, and the tests that close it.
7. Goals. The goals, scope and success criteria of §1.1 to §1.3 become the first part of the overview. CLAUDE.md keeps in §1 the priorities and a line that links the overview, and the nine citations of §1.1 to §1.3 in seven files are pointed at the overview.
8. Consistency. The overview is read together with the templates and CLAUDE.md, every topic and every module of §1.2 is checked to have its layer, and the briefs of the first layer are listed.

| Step | Subject | Files | Status |
|---:|---|---|---|
| 1 | Way of working, form and place | `design/overview/plan.md` | done |
| 2 | Use | `design/overview/plan.md` | |
| 3 | Practice | `design/overview/plan.md` | |
| 4 | Structure of the overview | `design/overview/plan.md`, `design/overview.md` | |
| 5 | Cut into layers | `design/overview/plan.md`, `design/overview.md` | |
| 6 | Contents of the layers | `design/overview.md` | |
| 7 | Goals, scope and success criteria | `design/overview.md`, CLAUDE.md and the six other files that cite §1.1 to §1.3 | |
| 8 | Consistency of the whole | the files of steps 4 to 7 | |

## Decisions

Step 1. The author decided that the overview is a living document rather than a brief. Its cut into layers is agreed as the order of work, as the cut into topics was. Every architectural choice that the cut implies is named and left to a brief, and decided sub-decisions are linked as they come. The overview lives as long as the project, as a requirement document lives as long as its component, and is updated in place, with the author's agreement, whenever a brief changes what a layer must provide. The cut is thus agreed without the form of a brief, its options and the alternatives set aside. The overview is kept in `design/overview.md`, beside the folders that it maps, so that the document cited most has the shortest path. The folder `design/overview/` of the same name holds this plan and any diagrams, as a brief keeps its diagrams beside it. Once the overview is written, the goals, scope and success criteria of §1.1 to §1.3 become its first part, since the layers answer to them. CLAUDE.md keeps in §1 the priorities with a line that links the overview, so that every session still finds them.

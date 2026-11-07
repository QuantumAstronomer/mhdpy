# Rules of the decision briefs

Every architectural choice of mhdpy is made in a decision brief, one topic at a time (§2.4). This file explains each part of the skeleton `brief.md` and the reason for it, how briefs and their sub-decisions are named, and how a brief is written, decided, frozen and superseded. Section signs refer to CLAUDE.md, and plain numbers to the parts of this file. In the skeleton, braces mark values to fill in, and italic lines describe the prose that replaces them.

## 1. Files and identifiers

A brief is identified by the letter B and a number, given in the order in which briefs are opened and never reused, as B7. The number carries no meaning, so that no change of subject or layer can force it to change, and the letter keeps it apart from the numbers of the topics, which it need not match. The brief is one file at the top of `design/briefs/`, named by its identifier with the number padded to two digits, so that the files sort in order, then a hyphen and its subject in lower case, with hyphens and without articles or commas, as `B07-riemann-solvers.md`.

A brief that needs diagrams keeps them in a folder of the same name beside it, as `design/briefs/B07-riemann-solvers/`, made when the first diagram is needed. A diagram is saved as SVG, which is text, small and sharp at any size, and may be drawn by hand or by a short script that lies beside it. The folder is committed, as its diagrams belong to the record that a decided brief freezes. The experiments of a brief lie in a folder of the same name in `design/experiments/`, one subfolder to an experiment, as the template of the experiments sets out.

A sub-decision is identified by its brief, the letter D and a number, as B7D2. The number is given when the sub-decision is written and is never changed or reused. Within a sub-decision the options are lettered A, B and so on, and cited as option B of B7D2. Documents cite a sub-decision by a link whose text is its identifier, as [B7D2](../briefs/B07-riemann-solvers.md#b7d2-the-solver-for-hydrodynamics), and commit messages by the identifier alone.

## 2. The head of a brief

The title is the identifier with the subject, as B7 Riemann solvers. Three lines follow it. The status reads "Open." while sub-decisions remain to be written or decided, and "Decided on {date}." once the brief is closed, and gains a pointer when a later brief supersedes part of it (5). The topics name, with links, the topic summaries that the brief draws on. The line on supersession names the sub-decisions of earlier briefs that the brief replaces, or reads "None."

The scope says what the brief settles and what it leaves to other briefs. It names the decided sub-decisions of earlier briefs that the brief builds on, so that a conflict with them shows before it arises. A list follows with one line to each sub-decision, its link and its status: open, decided, revised or superseded. The sub-decisions still to be written are named after it, without identifiers. The list may change until the brief is decided, as the answer to one question can add or remove another.

## 3. The sub-decisions

A brief is worked through one sub-decision at a time: each is written, discussed with the author and decided before the next one is written (§2.4). Each is a section headed by its identifier and its question in a few words, and holds six parts under run-in labels, in a fixed order.

**Decision.** This part is consulted most, so it comes first, although it is written last. Until the author decides, it reads "Open.", which also shows at a glance what remains to be done. Once the author has decided, it holds one paragraph in the form of a Y-statement, split into two sentences to keep them short (§3.1): "In the context of {the situation}, facing {the concern}, {the option} is chosen over {the others}. This achieves {the priority served}, accepting {the price}." The date follows, with "as recommended" or, where the author departs from the recommendation, the reasons. The form keeps the answer to why a choice was made in one place, and its second sentence states where the decision falls in the ranking of §1.4.

**Question.** What must be decided, why it must be decided now and what depends on it. The part links the sections of the topics, and of the syntheses where needed, to read or reread first. It repeats from them only the points on which the decision turns.

**Options.** One paragraph to an option, labelled "Option A: {name}." and so on. Each says what the option is, which references use it and what they report, naming Athena++ where it makes this choice, as its solutions are trusted as robust and performant (§2.4). It then says what the option would mean for mhdpy: its consequences for correctness, performance, readability, extensibility and usability, and what it demands of the layers above. The consequences are the point of the part, since a method is chosen for what it does to mhdpy rather than for its merits in the abstract.

**Experiments.** Only where the references leave the question open (§2.4). For each experiment, the part gives the question that it answers, its result in a sentence or two, and a link to it. The experiment holds its method, its figures and the limits of its result, so that the brief stays short. An experiment that a sub-decision needs is run, and its result entered here, before the recommendation is written, so that the recommendation weighs what was measured and the measurement is not read in the light of a recommendation.

**Recommendation.** The option recommended and the reasons, with the priority of §1.4 that it serves and the one that it gives up, or that it gives up none. Only this part weighs the evidence, which the question, the options and the experiments state, so that the evidence can be judged apart from the conclusion drawn from it (§2.4).

**Set aside.** Written with the decision. Each option not chosen that is worth keeping gets a sentence or two on why it was not chosen and on what would bring it back, such as a later layer that needs it or a cost measured too high. A later brief can then test that condition instead of reopening the argument. Options not worth keeping are not listed.

A sub-decision runs to about 800 words at most, from its decision to its set-aside options and not counting links. One that needs more is split into two, as §2.2 asks of any step.

## 4. Writing

Briefs follow §3.1: a passive, scientific voice that names neither the author nor the assistant, short sentences, British spelling and inline LaTeX. A claim not taken from the reference material is marked **[GK]**, and a claim that a summary marks keeps its mark when a brief repeats it. Reasoning carries no mark of its own: the consequences drawn for mhdpy, the recommendation and the decision. Where it rests on a fact of hardware, libraries or numerics that the references do not give, the mark stands before that fact and covers the rest of the paragraph, as in the summaries. In an option, the mark then stands where the consequences begin. Topics are cited as in the summaries, as [topic 7, §2.4](../topics/07-riemann-solvers.md#24-hllc), and syntheses by their subsections. Dates take the form 2026-11-20. Sources cited directly, rather than through the topics and syntheses, are listed at the end in the format of the topic summaries, a part left out otherwise.

## 5. The life of a brief

A brief is open while sub-decisions remain to be written or decided. While it is open, a decided sub-decision may be revised, for instance when a later one shows it to be wrong. It is then changed in place, and a dated line in its decision says what changed and why. The brief is decided when the author declares it so, after its last sub-decision, and it is then frozen (§2.4).

A frozen brief changes only through a new brief that supersedes it, as a whole or in single sub-decisions. The new brief names them in its line on supersession, and the rest of the old brief stays in force. The old brief then receives its only edits: its status line, and the decision of each superseded sub-decision, gain a line that names the superseding brief and the date, as "Superseded by B12D1 on {date}." No one then follows a decision that is no longer in force. Work that conflicts with a decided brief stops and names the sub-decision concerned, as B7D2 (§2.4).

## 6. Sources

**[GK]** The template draws on established practice for records of decisions. From the architecture decision records of [Nygard](#nygard-2011) (2011) come the numbered record that is frozen once decided and superseded rather than edited, and the status that points to its successor. From MADR, the Markdown Architectural Decision Records of [Kopp, Armbruster and Zimmermann](#kopp-et-al-2018) (2018), come the options considered side by side. The decision paragraph follows the Y-statements of [Zdun et al.](#zdun-et-al-2013) (2013), and the options set aside follow the rejected ideas of the Python Enhancement Proposals ([PEP 12](#pep-12)).

- <a id="kopp-et-al-2018"></a>Kopp, O., Armbruster, A. and Zimmermann, O., Markdown architectural decision records: format and tool support, ZEUS 2018, Central European Workshop on Services and their Composition (2018), [adr.github.io/madr](https://adr.github.io/madr/).
- <a id="nygard-2011"></a>Nygard, M., Documenting architecture decisions, Cognitect blog, 15 November 2011, [cognitect.com/blog/2011/11/15/documenting-architecture-decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
- <a id="pep-12"></a>PEP 12, Sample reStructuredText PEP template, Python Enhancement Proposals, [peps.python.org/pep-0012](https://peps.python.org/pep-0012/).
- <a id="zdun-et-al-2013"></a>Zdun, U., Capilla, R., Tran, H. and Zimmermann, O., Sustainable architectural design decisions, IEEE Software 30(6), 46–53 (2013), [doi:10.1109/MS.2013.97](https://doi.org/10.1109/MS.2013.97).

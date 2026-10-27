# Plan of the reference syntheses

This file records how each synthesis of §4.1 of CLAUDE.md is split into steps, the decisions taken for it, and which of its steps are done. The steps of each synthesis are set when its work begins. Section signs refer to the reference, plain numbers to the sections of its synthesis.

## Zingale's text

The synthesis is kept in `computational-hydrodynamics-synthesis.md`. Its sources are `References/Computational Hydrodynamics Book/CompHydroTutorial.pdf` and, in the subfolder `drafts/` there, the draft chapters `gravity.tex` and `radiation.tex` of the same version.

The text is cited by title and date, as Zingale, *Introduction to Computational Astrophysical Hydrodynamics*, version of 26 January 2025, and its sections, equations, figures and tables by their numbers in that version. A **[GK]** mark covers the rest of its paragraph or list item. Where a web source disagrees with the text, the disagreement is reported for a decision, not settled in the synthesis. Slips that a derivation exposes are noted as **[GK]** without asking, and listed in the review of their step. Slips in wording without consequence are paraphrased correctly and listed in the review, but not noted. Gap fills likewise go in without asking, and are listed in the review. Exercises are not named, but a result of an exercise that the text relies on later is stated where it is used. Pointers to companion scripts are left out, and the overview names the three companion codes once. Test parameters that the text leaves out are not filled in from the companion codes. The tests that mhdpy reproduces come from the suites of the reference codes (§1.3 of CLAUDE.md), and pyro has a synthesis of its own.

The numerical methods are grouped into ten subjects, each fed by one or two consecutive chapters. The drafts join subject 2.6, marked as drafts. The software architecture draws on §3.4, §13.6, §13.7 and the appendices.

| Subsection | Subject | Chapters |
|---|---|---|
| 2.1 | Numerical foundations | 1, 2 |
| 2.2 | Finite-volume grids | 3 |
| 2.3 | Advection | 4, 5 |
| 2.4 | Burgers' equation | 6 |
| 2.5 | The Euler equations | 7, 8 |
| 2.6 | Elliptic equations and multigrid | 9, drafts |
| 2.7 | Diffusion | 10 |
| 2.8 | Multiphysics and reactive flow | 11, 12 |
| 2.9 | Planning a simulation | 13 |
| 2.10 | Low-speed flow | 14, 15 |

Each chapter is one step, and the two chapters longer than 25 pages are cut at section boundaries. The drafts follow in a step of their own at the end. The pages are those printed in the text; for the chapters, the page of the PDF is the printed page plus 22.

| Step | Part of the text | Pages | Feeds | Status |
|---:|---|---|---|---|
| 1 | Front matter: overview, scope, companion codes, notation | i–xxi | 1 | done |
| 2 | Ch. 1, Simulation Overview | 3–20 | 2.1 | done |
| 3 | Ch. 2, Classification of PDEs | 21–23 | 2.1 | done |
| 4 | Ch. 3, Finite-Volume Grids | 25–33 | 2.2, 3 | done |
| 5 | Ch. 4, Advection Basics | 37–47 | 2.3 | done |
| 6 | §5.1–5.3: finite-volume advection, limiting, method of lines | 49–62 | 2.3 | done |
| 7 | §5.4–5.7: multi-dimensional advection, high-order methods, WENO | 62–80 | 2.3 | done |
| 8 | Ch. 6, Burgers' Equation | 81–91 | 2.4 | done |
| 9 | Ch. 7, Euler Equations: Theory | 93–113 | 2.5 | |
| 10 | §8.1–8.5: reconstruction, Riemann solvers, conservative update, boundary conditions | 115–131 | 2.5 | |
| 11 | §8.6–8.9: multi-dimensional problems, source terms, geometries, test problems | 131–148 | 2.5 | |
| 12 | §8.10–8.12: method of lines, thermodynamics, WENO | 148–159 | 2.5 | |
| 13 | Ch. 9, Elliptic Equations and Multigrid | 163–184 | 2.6 | |
| 14 | Ch. 10, Diffusion | 185–199 | 2.7 | |
| 15 | Ch. 11, Model Multiphysics Problems | 203–208 | 2.8 | |
| 16 | Ch. 12, Reactive Flow | 209–216 | 2.8 | |
| 17 | Ch. 13, Planning a Simulation | 217–221 | 2.9, 3 | |
| 18 | Ch. 14, Incompressible Flow and Projection Methods | 225–241 | 2.10 | |
| 19 | Ch. 15, Low Mach Number Methods | 243–252 | 2.10 | |
| 20 | App. A–C: the companion codes | 255–266 | 3 | |
| 21 | Drafts: `gravity.tex` and `radiation.tex` | – | 2.6 | |

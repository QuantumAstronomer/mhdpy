# Decision briefs

Each architectural topic gets one decision brief, and briefs are written one at a time. Topics are worked through from the bottom layer of the architecture to the top, so each layer is designed with full knowledge of the layers beneath it. Every decision is made by the author; recommendations are advisory. The decision is recorded in the brief, and each brief gets one row in the table of [`../architecture.md`](../architecture.md) §2, with a short summary of what was decided.

## Layout

```
docs/
├── architecture.md                        purpose, priorities and a summary of all briefs
└── decisions/
    ├── README.md                          this file
    └── DNN-topic/                         one folder per brief, e.g. D02-verification/
        ├── DNN-topic-brief.md             the decision brief, e.g. D02-verification-brief.md
        └── experiments/
            ├── ENN.k-description.py       an experiment with a single script, e.g. E01.1-wheel-availability.py
            ├── ENN.kx-description.ext     each code file of an experiment with several, e.g. E02.1a-hydro1d.py,
            │                              E02.1b-convergence.py, E02.1c-figure.py
            ├── ENN.kx-description.py.lock the lockfile of a script (D01.6), with the script's ID
            └── results/
                └── ENN.kx-....            everything a script produces, with that script's ID
```

## Naming conventions

All names are lowercase, with words separated by hyphens; only the `D` and `E` prefixes are capitals.

| What | Pattern | Example |
|---|---|---|
| Brief folder | `DNN-<topic>` | `D01-tooling` |
| Brief file | `DNN-<topic>-brief.md` | `D01-tooling-brief.md` |
| Sub-decision ID | `DNN.k` | `D01.7`, the seventh sub-decision of brief D01 |
| Experiment ID | `ENN.k` | `E01.2`, the second experiment of brief D01 |
| Code file of a single-script experiment | `ENN.k-<description>.<ext>` | `E01.2-style-formatting.py` |
| Code file of a multi-script experiment | `ENN.kx-<description>.<ext>`, with x = a, b, c, … | `E02.1a-hydro1d.py`, `E02.1b-convergence.py`, `E02.1c-figure.py` |
| Lockfile | the script's name plus `.lock` | `E02.1b-convergence.py.lock` |
| Inputs and results | `ENN.k[x]-<description>.<ext>`, with the ID of the script that uses or produces them | `E01.2-style-sample.py`, `results/E02.1b-errors.json`, `results/E02.1c-convergence.png` |

- `NN` is the two-digit brief number; `k` counts sub-decisions or experiments within that brief, starting at 1.
- **One code file, one letter.** An experiment with a single script uses the plain experiment ID. As soon as an experiment has more than one code file (scripts, modules, kernels, Dockerfiles, shell scripts), every code file gets its own letter, starting at `a` and incrementing in the order the files are added. The letters show at a glance how many code files an experiment has and which files belong to which part. Should a single-script experiment later gain a second code file, its first file is renamed to letter `a`.
- **Every file belongs visibly to one script.** A lockfile carries its script's ID. An input file or a result carries the ID of the script that uses or produces it: in E02.1, the error data in `results/E02.1b-errors.json` comes from `E02.1b-convergence.py`, and the figure `results/E02.1c-convergence.png` from `E02.1c-figure.py`.
- Every file of an experiment starts with that experiment's ID, so the brief can refer to it unambiguously and its files sort together.
- IDs and letters are never reused, not even after a sub-decision is superseded or an experiment or script is dropped.

## Planned briefs

Ordered bottom-up. Brief D03 is a deliberate exception: the discretisation family sits high in the stack, but it determines what the lower layers must hold (for example face- and edge-centred variables for constrained transport) and which kernel is representative for the backend benchmarks.

| Brief | Topic | Scope |
|---|---|---|
| D01 | Tooling and project conventions | Python and uv setup, package layout, lint/type/test tools, experiment environment |
| D02 | Verification strategy | How correctness is demonstrated at every layer |
| D03 | Discretisation family | Finite-volume Godunov or finite differences; constrained transport or divergence cleaning for MHD |
| D04 | Compute backend and kernel model | How numerical kernels are written and run; precision; how compiled code is shipped |
| D05 | Parallelism model | Threads (including free-threaded Python), processes, MPI, the path to GPUs |
| D06 | Data model | Memory layout, index order, dimensionality, a variable registry with metadata |
| D07 | Mesh and geometry | Single grid or blocks, block tree, ghost zones, coordinates abstraction |
| D08 | Boundaries and inter-block communication | Ghost exchange, physical boundary conditions, flux correction, restriction and prolongation |
| D09 | Execution model | Fixed step function or task graph; scheduling over blocks |
| D10 | Numerical building blocks | Reconstruction, Riemann solvers, equation-of-state interface |
| D11 | Time integration and operator splitting | Method of lines with Runge–Kutta, VL2, super-time-stepping, source coupling, timestep control |
| D12 | Physics module interface | How hydro, scalars, cooling, conduction and gravity plug in |
| D13 | Driver and simulation lifecycle | Main loop, timestep, scheduling of outputs and restarts |
| D14 | I/O, restart and diagnostics | File formats, history output |
| D15 | Configuration and user interface | Python API, input files, problem setups and hooks, CLI |

## Brief template

```markdown
# DNN — <Topic>

| | |
|---|---|
| Status | Draft / Decided / Partly superseded / Superseded |
| Decided | <date all sub-decisions were made> |
| Supersedes | <IDs from earlier briefs, or "—"> |
| Superseded by | <per ID: "D03.2 → D07.1", or "—"> |

## 1. Introduction
What has to be decided and why it matters at this layer. Background from the
references (Athena/Athena++, Pyro, Ulula, ZEUS, CompHydro book), with pointers
to the syntheses in `References/`. Anything from outside those materials is
marked **[GK]** (general knowledge).

## 2. Evidence  (optional)
Supporting material from the references and from experiments: what was
measured, how, on which machine, with figures and tables. Every result is
reproducible from a script in `experiments/`.

## 3. Decisions

### DNN.1 — <sub-decision>
The question, in one or two sentences.

**Options**
- **A. <name>.** Description. Advantages. Drawbacks.
- **B. <name>.** ...

**Recommendation.** The option considered best, with a clear motivation for
why it is better than the alternatives for mhdpy's purpose, and where it lands
in the priority ranking of architecture.md §1.4.

**Decision.** *(by the author)* The chosen option, the date, and the
reasoning, including why if the recommendation was not followed.

### DNN.2 — ...

## 4. Consequences for higher layers
Written once all sub-decisions are made. What these decisions commit the
project to, and which later topics they constrain.
```

## Rules

- **Frozen once decided.** When all of a brief's sub-decisions have been made, the brief is frozen. After that, only the status table and supersession notes may change.
- **Changing a decision means writing a new brief.** The new sub-decision states `Supersedes DNN.k`. The old brief gets a line under that sub-decision's heading, `> Superseded by DMM.j (<date>)`, and its status table is updated. `architecture.md` is updated to the new decision.
- **Single sub-decisions can be superseded.** The rest of the old brief stays valid.

## Experiment conventions

- Each script that is run declares its dependencies inline (PEP 723) and has its own lockfile (`<script name>.lock`, created with `uv lock --script`). It is rerun with `uv run --locked --script <script name>` (D01.6). Modules and kernels that are only imported by a script need no lockfile of their own.
- Scripts record the machine, software versions and parameters alongside their results.
- Experiments test the decision at hand with the smallest code that can answer it. They are not early versions of mhdpy.

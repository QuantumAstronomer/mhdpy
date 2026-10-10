# Decision briefs

Each architectural topic gets one decision brief, and briefs are written one at a time. Topics are worked through from the bottom layer of the architecture to the top, so each layer is designed with full knowledge of the layers beneath it. Every decision is made by the author; recommendations are advisory. The decision is recorded in the brief, and each brief gets one row in the table of [`../architecture.md`](../architecture.md) §2, with a short summary of what was decided.

## Layout

```
docs/
├── architecture.md                       purpose, priorities and a summary of all briefs
└── decisions/
    ├── README.md                         this file
    └── DNN-topic/                        one folder per brief, e.g. D01-tooling/
        ├── DNN-topic-brief.md            the decision brief, e.g. D01-tooling-brief.md
        └── experiments/
            ├── ENN.k-description.py      experiment script, e.g. E01.1-wheel-availability.py
            ├── ENN.k-description.py.lock its lockfile (D01.6)
            ├── ENN.k-....                any input files of that experiment
            └── results/
                └── ENN.k-....            everything the experiment produces
```

## Naming conventions

All names are lowercase, with words separated by hyphens; only the `D` and `E` prefixes are capitals.

| What | Pattern | Example |
|---|---|---|
| Brief folder | `DNN-<topic>` | `D01-tooling` |
| Brief file | `DNN-<topic>-brief.md` | `D01-tooling-brief.md` |
| Sub-decision ID | `DNN.k` | `D01.7`, the seventh sub-decision of brief D01 |
| Experiment ID | `ENN.k` | `E01.2`, the second experiment of brief D01 |
| Experiment files | `ENN.k-<description>.<ext>` | `E01.2-style-formatting.py`, `E01.2-style-sample.py` |
| Experiment results | `results/ENN.k-<description>.<ext>` | `results/E01.2-format-120-double.diff` |

- `NN` is the two-digit brief number; `k` counts sub-decisions or experiments within that brief, starting at 1.
- Every file belonging to an experiment (script, lockfile, inputs and results) starts with that experiment's ID, so the brief can refer to it unambiguously and its files sort together.
- IDs are never reused, not even after a sub-decision is superseded or an experiment is dropped.

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

- Each experiment is a standalone script with inline dependency metadata (PEP 723) and its own lockfile (`ENN.k-description.py.lock`, created with `uv lock --script`). It is rerun with `uv run --locked --script ENN.k-description.py` (D01.6).
- Scripts record the machine, software versions and parameters alongside their results.
- Experiments test the decision at hand with the smallest code that can answer it. They are not early versions of mhdpy.

# D13 — Driver and simulation lifecycle

| | |
|---|---|
| Status | Decided (frozen) |
| Decided | 2026-10-12 |
| Supersedes | — |
| Superseded by | — |

## 1. Introduction

This brief decides how a simulation is set up, run and ended:

- the object that represents a simulation and the stages of its life;
- how the main loop is controlled, and where user work hooks in;
- how phases are synchronised during a step;
- how outputs and restarts are scheduled;
- what a restart must contain;
- how a run reacts to a wall-clock limit, an interruption or a failed step;
- what it reports while running.

File formats are D14's; how parameters and problems are supplied is D15's.

The earlier briefs fix most of what happens *inside* a step:

- **D09.** A step is a sequence of phases, registered as data with their reads and writes. The main thread runs them in order on a thread pool, workers claim chunks of blocks dynamically, and the driver owns the pool, the chunk size and the number of workers.
- **D11.** The order of a step is fixed:
  1. half a step of the stiff sources;
  2. half an RKL2 super step of diffusion;
  3. the integrator's stages;
  4. the other halves of the super step and the stiff sources;
  5. the new time step.

  The time step is bounded in its growth and shortened to hit output times exactly. The driver records which constraint limits it.
- **D12.** At set-up, the driver collects the modules' declarations, freezes the registry, assembles phases and per-block extension points, and reports the simulation's integration contract.
- **D02.3.** A restarted run must reproduce an uninterrupted one bit for bit within the same environment. That is one of the invariants tested.
- **D05.5 and D10.6.** The state does not depend on the number of workers or on the decomposition. Floors and first-order flux corrections are counted.

**What the references do** (syntheses in `References/`):

- **Athena++** runs one `main` program:
  - **Set-up:** initialise MPI and threads; parse the command line (input file, restart file, run directory, a dry run of the decomposition, a wall-time limit); build the mesh, from scratch or from a restart; build the task lists; initialise (problem generator, initial boundary exchange, primitives, first time step); write the initial outputs.
  - **Loop:** super-time-stepping; the stages; user work; time and cycle; load balancing and refinement; the new time step; outputs. It also checks for signals and the wall-time limit.
  - **End:** final outputs, user work after the loop, and a performance summary in zone-cycles per second.
  - **Outputs:** each output has its own cadence in time or in cycles.
  - **Restarts:** written with MPI-IO, and may resume on a different number of processes.
- **Pyro** offers a command-line script and a `Pyro` class side by side, the latter for notebooks and step-by-step use. Its synthesis lists that among the things worth borrowing.
- **Ulula** is driven by a `run` function with output and plot schedules. It writes outputs at exact times by advancing a *copy* of the simulation to the output time, without disturbing the main run's steps. Every snapshot is also a restart file, and a step can be undone and repeated when the CFL condition is violated during it.

## 2. Evidence

### E13.1 — The fixed cost of synchronised phases

**Method.** A step consists of many phases: exchanges, boundary conditions, conversions, fluxes with their attached passes, updates, sources, corrections and the time step. If the main thread runs every phase as tasks on the thread pool and waits for all of them, each phase costs a fixed amount of synchronisation, independent of the grid. [`experiments/E13.1-phase-overhead.py`](experiments/E13.1-phase-overhead.py) measures that cost with tasks that do nothing, for 1, 6 and 12 workers and both interpreters. It also times a realistic structure with the work removed: 24 phases per step (an SSP-RK2 step with stiff sources and diagnostics), of which 6 must be synchronised. Those are the ones that read neighbouring blocks after an exchange or reduce over all blocks. The structure is run two ways:

- with every phase synchronised;
- with consecutive block-local phases merged into one task per worker.

Full output: [`results/E13.1-phase-overhead.md`](experiments/results/E13.1-phase-overhead.md).

**Results.**

| Interpreter | Workers | One synchronised phase | Step, all 24 synchronised | Step, merged to 6 | Share of a 120 ms thesis step (all / merged) |
|---|---|---|---|---|---|
| Free-threaded | 1 | 26 µs | 0.59 ms | 0.14 ms | 0.5 % / 0.1 % |
| Free-threaded | 6 | 64 µs | 1.59 ms | 0.39 ms | 1.3 % / 0.3 % |
| Free-threaded | 12 | 131 µs | 3.31 ms | 0.81 ms | 2.8 % / 0.7 % |
| With GIL | 6 | 110 µs | 2.64 ms | 0.64 ms | 2.2 % / 0.5 % |
| With GIL | 12 | 192 µs | 4.61 ms | 1.12 ms | 3.8 % / 0.9 % |

- **A synchronised phase costs 25–190 µs,** growing with the number of workers.
- **On the thesis grid, synchronising every phase costs 1–4 % of a step; merging block-local phases cuts that by a factor of four.**
- **On small problems the fixed cost dominates.** A test problem of 128² cells takes a few milliseconds per step, about as long as the synchronisation of 24 phases. For the fast test tier (D02.5), which runs many small problems, merging decides whether parallel runs are faster than serial ones at all.

### E13.2 — What a restart must contain

**Method.** The time-step control of D11.5 makes the next step depend on the previous one: its growth is bounded, and steps are shortened to hit output times. [`experiments/E13.2b-restart.py`](experiments/E13.2b-restart.py) runs the Sod shock tube with the minimal solver of D02 ([`E13.2a-hydro1d.py`](experiments/E13.2a-hydro1d.py); SSP-RK2, CFL 0.4, step growth at most 1.1×, outputs every 0.025) to t = 0.2. It does so once without interruption, and once interrupted at t = 0.1 and continued *in a new process* from a restart file containing:

- the state, the time and the previous step, in binary;
- the state and time only, in binary;
- everything as text with 10 significant digits.

Full output: [`results/E13.2b-restart.md`](experiments/results/E13.2b-restart.md).

**Results.**

| Restart file | Equal to the uninterrupted run | Max. relative difference |
|---|---|---|
| State, time and previous step, binary | **bit for bit** | 0 |
| State and time only, binary | no | 3.8 × 10⁻⁴ |
| Everything as text, 10 significant digits | no | 1.0 × 10⁻⁹ |

- **A restart reproduces the uninterrupted run bit for bit, in a new process, if it contains everything the next step depends on, exactly.** Here that is the state, the time and the previous step.
- **Leaving out the step-control state changes the result by 4 × 10⁻⁴.** The restart then takes a different first step, and the run follows a different sequence of steps from there. The difference is of the order of the scheme's truncation error, invisible to a convergence test, but it breaks the bit-for-bit invariant.
- **Text loses the last bits** even at 10 significant digits. Restart files must be binary.

**What the two experiments mean together.**

- Synchronisation is cheap but not free. It should happen only where data dependencies require it, which the phases' declared reads and writes (D09.1) make it possible to work out automatically.
- A restart is a complete, exact snapshot of everything the continuation depends on, not just the physical state.

## 3. Decisions

### D13.1 — The simulation object and its life

How is a simulation represented, and what are the stages of its life?

**Options**

- **A. One `Simulation` object with explicit stages.**
  - **Set-up:** collect the modules' declarations, validate them, freeze the registry, build the mesh and allocate the state, apply the initial conditions, run the first exchange, compute the primitives and the first time step, and report the integration contract.
  - **Running:** the object can be advanced by `step()` or `run(until=…)`, from a script or interactively, as Pyro's class allows.
  - **Ending:** final outputs and a performance summary.
- **B. A main program only,** as Athena++: a command-line executable reads an input file and runs to the end. Simple for batch runs, but notebooks and tests cannot step through a simulation.
- **C. Separate functions** for set-up, stepping and output, with the state passed around. Flexible, but the invariants the object would guard (a frozen registry, a consistent time step) become the caller's responsibility.

**Recommendation.** A. One object with explicit stages guards the order of set-up that D06, D09 and D12 require. Exposing `step()` next to `run()` gives both of Pyro's interfaces: a command-line entry point (D15) can simply create the object and call `run()`. Tests use `step()` to check invariants after each step. This serves **correctness** and **ease of use**.

**Decision.** *(2026-10-12)* **A, one `Simulation` object with explicit stages**, following the recommendation.

### D13.2 — Controlling the loop and hooking in user work

How is the main loop controlled, and where does user work run?

**Options**

- **A. `run(until=…)` with defined hook points,** reached through the extension points of D12:
  - stopping conditions: a simulation time, a number of cycles, a wall-clock limit, or a condition;
  - user work after a step and before an output, as Athena++'s `UserWorkInLoop` and `UserWorkBeforeOutput`;
  - diagnostics at their cadence.

  Users who need full control call `step()` in a loop of their own.
- **B. A general event system** with callbacks on any event (every phase, every block). Maximally flexible, but callbacks inside a step would run Python per phase or per block, against D09.
- **C. No hooks:** users write the loop themselves around `step()`.

**Recommendation.** A. The hook points are the ones the reference codes found necessary. They sit between steps, where Python costs nothing measurable. `step()` remains available for anything else, which also covers C. This serves **ease of use** and **extensibility**.

**Decision.** *(2026-10-12)* **A, `run(until=…)` with defined hook points**, following the recommendation.

### D13.3 — Synchronising phases

When does the main thread wait for the workers?

**Options**

- **A. After every phase.** Simplest; 1–4 % of a thesis step, and dominant for small problems (E13.1).
- **B. Only where a dependency crosses blocks.** Consecutive phases that touch only their own blocks run back to back within one task per worker. The main thread waits only before a phase that reads neighbouring blocks (after an exchange), reduces over all blocks (the time step, diagnostics) or runs a global solver. The groups follow from the phases' declared reads and writes (D09.1) and are worked out once at set-up, not written by hand.

**Recommendation.** B. It cut the synchronisation by four in E13.1. It matters most for small problems, which the fast test tier runs by the hundred. Because the grouping follows from declarations, a module cannot get it wrong, and a test can check it: merged and unmerged execution must give bit-for-bit identical results. With dynamic assignment (D09.3), a merged group is claimed chunk by chunk like a single phase. This serves **performance**.

**Decision.** *(2026-10-12)* **B, synchronisation only where a dependency crosses blocks**, following the recommendation. Waiting after every phase would leave workers idle each time until the slowest of them has finished; merging block-local phases avoids that.

### D13.4 — Scheduling outputs and restarts

How are outputs and restart files scheduled?

**Options**

- **A. A schedule per output:** every output (and the restart file) has its own cadence, in simulation time, in cycles or in wall-clock time, as Athena++. Outputs in simulation time are hit exactly by shortening the step (D11.5). Restart files are also written at the end of the run and when it is interrupted (D13.6).
- **B. Exact output times by advancing a copy,** as Ulula: the main run is not disturbed, but each output costs a copy of the state and the work of the steps to reach it.
- **C. Outputs at the nearest step,** without hitting times exactly. Cheapest, but comparisons between runs and with analytic solutions at a given time then need interpolation.

**Recommendation.** A. Shortening the step is already decided (D11.5) and costs at most one short step per output. Independent schedules let history output run every few steps while snapshots and restart files run rarely, as production runs need. Wall-clock cadence for restart files bounds the work lost on a crash. This serves **correctness** (outputs at exact times) and **ease of use**.

**Decision.** *(2026-10-12)* **A, a schedule per output**, following the recommendation.

### D13.5 — What a restart contains

What must a restart file contain?

**Options**

- **A. Everything the continuation depends on, exactly:**
  - every registered array that is not derived (conserved variables, face-centred fields, registers that carry information between steps);
  - the time, the cycle and the step-control state (the previous step);
  - the mesh (root grid, logical locations) and the unit system;
  - every module's declarations, parameters and internal state, including the states of random-number generators (for example turbulence driving);
  - the output schedules;
  - all of it in binary.

  Primitive variables and ghost zones are derived again on restart. By D05.5 the continuation then equals the uninterrupted run bit for bit, even with a different number of workers or a different block size.
- **B. The physical state only:** the arrays and the time. Smaller and simpler, but a restarted run then drifts from the uninterrupted one by the order of the truncation error (E13.2), and the bit-for-bit invariant of D02.3 cannot be tested.

**Recommendation.** A. E13.2 shows that anything less, including text, breaks bit-for-bit continuation, and D02.3 makes that an invariant. Being able to resume with a different number of workers or block size is a direct benefit of D05.5, for example when a run moves from the laptop to the server. Athena++ allows the same for its number of processes. This serves **correctness**.

**Decision.** *(2026-10-12)* **A, everything the continuation depends on, exactly**, following the recommendation, as the only option consistent with the bit-for-bit invariant of D02.3.

### D13.6 — Wall-clock limits, interruptions and failed steps

How does a run end when it is not done?

**Options**

- **A. Ending cleanly in every case:**
  - **Wall-clock limit:** a run with a limit (for a batch system) stops in time to write a restart file, estimating the time per step.
  - **Interruption:** an interrupt or termination signal (SIGINT, SIGTERM) finishes the current step, writes a restart file and exits.
  - **Failed step:** a step that leaves invalid values despite floors and first-order flux correction (D10.6) stops the run. That means values that are not finite, detected by a cheap check folded into the time-step reduction. The run writes the failed state for inspection and reports where it failed (block, cell, variable) and the last time-step constraint.
- **B. Minimal handling:** a run ends when it ends; a crash loses the work since the last restart file.

**Recommendation.** A. Batch systems end jobs by time limit and signal, and production runs of hours (architecture.md §1.3) must survive both without losing work. A failed step should leave behind the evidence needed to understand it. The check costs nothing extra if it is part of the reduction the time step already makes (D11.5). This serves **correctness** and **ease of use**.

**Decision.** *(2026-10-12)* **A, ending cleanly in every case.** A run that leaves a restart file behind, whatever ended it, is the easiest to continue.

### D13.7 — Reporting while running

What does a run report?

**Options**

- **A. A log line at a chosen cadence**, as Athena++ reports zone-cycles per second, containing:
  - cycle, time and step;
  - the constraint that limited the step and where;
  - cell updates per second;
  - counts of floor activations and first-order flux corrections;
  - memory use.

  Each run ends with a summary of the total throughput and where the time went, per phase group.
- **B. Silent runs,** with information only in output files.

**Recommendation.** A. Cell updates per second is the quantity the success criterion of architecture.md §1.3 is measured in, so every run should report it. The limiting constraint and the counts of floors and corrections are the first things to look at when a run slows down or misbehaves. Timing per phase group costs nothing worth mentioning at the level of phases. This serves **performance** (it can only be improved where it is measured) and **ease of use**.

**Decision.** *(2026-10-12)* **A, a log line at a chosen cadence and a summary at the end.** Which information goes to the terminal and which to log files is still to be decided. That belongs to D15 (user interface), with the format of log files part of D14.

## 4. Consequences for higher layers

**For every layer**

- **The simulation object:** a `Simulation` with three stages (D13.1).
  - **Set-up**, in a fixed order: collect and validate the modules' declarations, freeze the registry, build the mesh and allocate the state, assemble the phases and per-block extension points, apply the initial conditions, run the first exchange, compute the primitives and the first time step, and report the integration contract (D12).
  - **Running:** `step()` advances one step; `run(until=…)` advances until a simulation time, a number of cycles, a wall-clock limit or a condition is reached.
  - **Ending:** final outputs, the restart file and the performance summary.

  The object guards the order: nothing can be registered once the registry is frozen, and nothing can be stepped before set-up is complete. The command-line entry point of D15 creates the object and calls `run()`.
- **Hook points** sit between steps: after a step, before an output, and after the run (D13.2). They are extension points in the sense of D12.3, so user work follows the same rules as module code: it receives ranges of blocks, never single blocks (D12.4). The loop also reserves the place where refinement and load balancing would go once AMR exists (D07.7): after the step, before the new time step, as in Athena++.
- **Phase groups:** at set-up, consecutive phases that touch only their own blocks are merged into groups, worked out from their declared reads and writes (D09.1). The main thread waits only between groups, before a phase that:
  - reads neighbouring blocks after an exchange;
  - reduces over all blocks (the time step, diagnostics);
  - runs a global solver.

  A group is claimed chunk by chunk like a single phase (D09.3). Every phase must therefore declare whether it reads neighbouring blocks or reduces; an undeclared dependency is an error in the module's contract (D13.3).
- **One reduction per step** for the time step (D11.5) also carries the check for non-finite values, the counts of floors and first-order flux corrections (D10.6) and the limiting constraint with its location. Checking a step and reporting on it then cost no extra pass over the state (D13.6, D13.7).
- **Schedules:** every output and the restart file have their own cadence, in simulation time, cycles or wall-clock time. Cadences in simulation time feed the shortening of the step (D11.5). Restart files are also written at the end of the run and when it is interrupted (D13.4).
- **Restart state:** a restart contains every registered array that is not derived, the time, the cycle and the step-control state, the mesh and the unit system, every module's parameters and internal state (including random-number generators), and the output schedules, all in binary (D13.5). Modules therefore declare any internal state that carries over between steps as part of their integration contract (D12.1). A restart may resume with a different number of workers or a different block size.
- **Ending a run that is not done** (D13.6):
  - **Signals:** the handler for SIGINT and SIGTERM only sets a flag. The loop checks it between steps, finishes the current step, writes a restart file and exits.
  - **Wall-clock limit:** the loop stops when the time left is less than the measured time of a step plus the time of writing a restart file.
  - **Failed step:** non-finite values found by the reduction stop the run. The failed state is written for inspection, with a report of the block, cell, variable and the last limiting constraint.
- **Reporting:** a log line at a chosen cadence (cycle, time, step, limiting constraint, cell updates per second, floor and correction counts, memory) and a summary at the end, with total throughput and the time per phase group, measured by the main thread at each synchronisation (D13.7).

**For the verification of D02**

- **Restarts:** a run interrupted halfway and continued in a new process equals the uninterrupted run bit for bit (D02.3), also with a different number of workers and a different block size.
- **Phase groups:** merged and unmerged execution give bit-for-bit identical results.
- **Ending cleanly:** a test simulation that receives SIGTERM leaves a restart file from which the continuation is bit-for-bit identical; a step with an injected non-finite value stops the run with the failed state written and the correct location reported.
- The cell updates per second reported by the driver are the quantity the performance criterion of architecture.md §1.3 is measured in, so benchmarks read them from the run rather than timing it separately.

**For brief D14 (I/O)**

- The restart format is binary and complete as listed above, and it stores blocks by logical location rather than by worker, so that it can be read with another decomposition.
- A restart file is written so that an interruption during writing never destroys the last good one, for example by writing to a temporary file and renaming it.
- The failed state of D13.6 is written in an output format that the usual analysis tools can read.
- Log files, if any, are an output whose format D14 decides.

**For brief D15 (configuration and user interface)**

- The command-line entry point creates the `Simulation` and calls `run()`. Its options include at least the parameter file, a restart file to resume from, the output directory, the number of workers and a wall-clock limit, as Athena++'s do.
- **Open question from D13.7:** which information goes to the terminal and which to log files, at which verbosity, and how this is set.
- Stopping conditions, output schedules and hook points are configurable in the same way as module parameters.

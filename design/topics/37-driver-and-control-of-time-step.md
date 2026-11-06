# The driver and the control of a time step

## 1. Overview

The driver turns a solver into a run: it reads the parameters, sets up the problem, takes steps until a criterion stops it, chooses each step, and writes outputs at their times. The references share this flowchart and differ in how general the driver is, how parameters reach it, how modules join the loop and how a step ends at a requested time. pyro has one driver for all its solvers, with parameters from files and the command line, Ulula a runtime function that runs a setup in two lines of Python, ZEUS-2D a main loop whose modules preprocessor macros include or remove, and Athena++ a main program whose loop runs the stages of its task lists with further solvers between them. The integrators and the limits of the step follow in [topic 8](08-time-integration.md), task lists in [topic 18, §2.4](18-operator-splitting-and-coupling-of-processes.md#24-task-lists), problems in [topic 38](38-problem-setups-and-user-functions.md) and outputs and restarts in [topic 39](39-output-restarts-and-analysis.md).

## 2. Designs

### 2.1 One driver for all solvers

The methods for different systems of equations are so alike, in their grids, boundaries and flowchart, that one driver serves all time-dependent solvers of pyro ([Zingale](#zingale-2014) 2014, §2). It runs from the command line with a solver, a problem, an inputs file and overrides, or from Python through a class that can also take single steps.

1. Read the defaults of pyro and of the solver, add the parameters of the problem, and let the inputs file change existing parameters, but not add new ones, and a dictionary override the rest; write the full set to a file.
2. Create the simulation of the solver with the problem and the parameters, and initialise it.
3. In each step, fill the ghost cells of all variables, compute the time step, evolve the state, and write and plot the outputs that are due.
4. Stop once the time reaches its limit or the number of steps its maximum, report unused parameters and timings when the output is verbose, and finalise.

A base class of every simulation holds the step number, the time, the current and previous steps, the parameters and the data. Its time step is fixed if a parameter sets one; otherwise the solver computes it, the first step is reduced by a factor, later ones may grow by at most a factor over the previous one, and the last is shortened to end at the final time.

Detail: [pyro 3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters).

### 2.2 A runtime function

Ulula's core is a simulation class, problem setups derived from one base class, a module of plotting and analysis, and the function `run`, so that two lines of Python run a simulation ([Diemer](#diemer-2025) 2025, §3.6). `run` takes the setup, the scheme, the number of cells along $x$, the final time and optionally a largest number of steps or a restart file, and controls printing, checks of conservation, files, plots and movies at intervals of steps or time. Each step follows from the Courant condition, and a step below $10^{-10}$ stops the run with an error that usually signals an unphysical state. The loop ends with the first step that reaches the final time, without shortening it, so that the run can pass the final time slightly. An output at a fixed time within the next step is meant to advance a copy of the simulation to that time and leave the run untouched.

Detail: [Ulula 3.3](../references/ulula-synthesis.md#33-the-runtime-function).

### 2.3 A main loop assembled by macros

Each cycle of ZEUS-2D solves the Poisson equation, performs the three substeps of the source step and the directionally split transport step, computes new velocities of a moving grid, and finds a new step from the Courant condition, until a criterion stops the loop ([Stone and Norman](#stone-norman-1992a) 1992a, §4.8). An interrupt checker accepts several dozen commands during a run, to dump data, set flags and variables, or halt, resume and restart. Preprocessor macros include or suppress the parts of the code that serve a physical process, a geometry or an output, so that an executable without MHD carries no arrays or routines for it. Most algorithms of MHD, and those of radiation, form self-contained modules that join the control sequence at fixed points: the first substep gains the gradients of the magnetic pressure, the method of characteristics follows it before the second, the moment solver takes the place of the third, and the field and the radiation are transported in the transport step ([Stone and Norman](#stone-norman-1992b) 1992b, §3.5; [Stone, Mihalas and Norman](#stone-et-al-1992a) 1992, §5).

Detail: [ZEUS 3.2](../references/zeus-synthesis.md#32-program-control).

### 2.4 A main program with task lists

The main program of Athena++ runs as follows.

1. Start MPI, checking the level of thread safety that OpenMP needs.
2. Read the command line: the input file, a restart file, the directory of the run, a limit of wall-clock time and overrides of parameters.
3. Read the parameters, build the mesh and the task lists, and set the initial conditions by the problem generator or from the restart file.
4. Change to the directory of the run and write the first outputs.
5. In each cycle, print diagnostics, take the part of super time-stepping that precedes the integration, drive turbulence, and solve the diffusion of cosmic rays and the radiation for chemistry.
6. Run the stages of the main task list, with self-gravity and implicit radiation between them.
7. Complete super time-stepping and call the work of the user.
8. Advance the time, refine and balance the load, compute the new step and write the outputs that are due.
9. End the loop at the final time, after a number of cycles, on a signal or at the limit of wall-clock time.
10. Write the final outputs and report the time, the cycles, the blocks created and destroyed, and the cell updates per second.

New modules join either the task lists or this loop ([topic 18, §2.4](18-operator-splitting-and-coupling-of-processes.md#24-task-lists)).

Detail: [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [Athena 3.5](../references/athena-synthesis.md#35-task-lists-and-parallelisation).

### 2.5 Runtime parameters and units

pyro reads files of sections with lines of key and value, whose keys become `section.option`; later definitions replace earlier ones, inputs files may change only existing keys, and the object records which parameters are read, so that unused ones can be reported, and writes all of them to the output. Athena++ reads blocks headed by a name with one parameter per line, after the model of Fortran's NAMELIST; the command line may change only existing parameters, and functions that add a default when a parameter is missing record every value in use in the head of restart files. Ulula works in code units, which the solver never uses and only plots convert, since the Euler equations are free of scales. Athena++ derives its code units from a choice of systems, one for the interstellar medium in units of $1.4\,m_\mathrm{H}\,\mathrm{cm^{-3}}$ for the density, with the mass $m_\mathrm{H}$ of a hydrogen atom, parsecs and km/s, one for galaxies in kiloparsecs and megayears, or custom units in cgs.

Detail: [pyro 3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters), [Ulula 3.5](../references/ulula-synthesis.md#35-units), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop).

### 2.6 Limits of the step from cooling and conduction

The simulations of [Armillotta, Fraternali and Marinacci](#armillotta-et-al-2016) (2016) limit the step of Athena to a tenth of the cooling time, and lift the limit of conduction by semi-implicit sweeps whose weight follows from the ratio of the hydrodynamic to the conductive step ([topic 17, §2.4](17-thermal-conduction.md#24-semi-implicit-integration) and [topic 20, §2.5](20-radiative-cooling.md#25-integration-over-a-step)). In AthenaPK conduction takes two super steps of RKL2 within each step of the MHD ([Brüggen, Scannapieco and Grete](#bruggen-et-al-2023) 2023; [topic 16, §2.5](16-diffusion.md#25-super-time-stepping)), and [Townsend](#townsend-2009) (2009) notes that a limit of the step to a fraction of the expected change of temperature helps accuracy at the price of more steps.

Detail: [Conduction and cooling 2.4.2](../references/conduction-and-cooling-synthesis.md#242-the-semi-implicit-scheme-of-the-simulations-of-2016), [Conduction and cooling 2.4.5](../references/conduction-and-cooling-synthesis.md#245-super-time-stepping-of-conduction), [Conduction and cooling 2.7.1](../references/conduction-and-cooling-synthesis.md#271-operator-splitting-and-the-limit-on-the-time-step), [Conduction and cooling 2.7.2](../references/conduction-and-cooling-synthesis.md#272-exact-integration-of-cooling), [Conduction and cooling 3.4](../references/conduction-and-cooling-synthesis.md#34-athenapk-in-the-simulations-of-brüggen-scannapieco-and-grete).

## 3. Tests

pyro's unit tests cover the stopping criteria, the control of the time step, the set-up of the grid, a short run through its class and the parsing of runtime parameters. No other reference aims a test at its driver, although the regression tests of Athena++ restart runs through its main program ([topic 39, §3](39-output-restarts-and-analysis.md#3-tests)). **[GK]** Runs of Ulula show that its outputs at fixed times disturb the run, and that a run without output and with a final time of 0.5 stops at 0.5023.

Detail: [pyro 3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters), [Ulula 3.3](../references/ulula-synthesis.md#33-the-runtime-function).

## 4. Assessment

pyro's single driver serves 17 solvers, Ulula runs any setup in two lines, and the macros of ZEUS-2D give optimised executables with and without MHD or radiation (Stone and Norman 1992a, 1992b; Stone, Mihalas and Norman 1992). Ulula's copy for outputs at fixed times is shallow and shares the arrays of the run, so that advancing it advances the arrays of the run but not its time, and a setup with an update function cannot be restarted through `run`. **[GK]** In runs the disturbance reaches a tenth of the amplitude of an advected wave. A step shortened to land on output and final times avoids both the copy and the overshoot; pyro shortens only the last step, to end at the final time. One driver with a fixed loop is the easiest to read and suffices while the modules are few; hooks at fixed points, as in ZEUS-2D, extend it with little cost, whereas task lists pay off once modules communicate or overlap ([topic 18, §2.4](18-operator-splitting-and-coupling-of-processes.md#24-task-lists)). Recording every parameter in use, as pyro and Athena++ do, lets a run be repeated with the same version of the code and, in Athena++, the same choices of configuration, and rejecting unknown parameters catches misspelt ones. The production runs need physical units, for the cooling function and the conduction, so that a system of code units with constants, such as that of Athena++ for the interstellar medium, belongs to the driver from the start, as does a limit of wall-clock time for long runs. Open are the structure of the loop, the format of the parameters, the system of units, and which limits of §2.6 join the Courant condition.

## 5. Sources

- <a id="armillotta-et-al-2016"></a>Armillotta, L., Fraternali, F. and Marinacci, F., Efficiency of gas cooling and accretion at the disc–corona interface, MNRAS 462, 4157–4170 (2016), [arXiv:1608.06290](https://arxiv.org/abs/1608.06290), [doi:10.1093/mnras/stw1930](https://doi.org/10.1093/mnras/stw1930).
- <a id="bruggen-et-al-2023"></a>Brüggen, M., Scannapieco, E. and Grete, P., The launching of cold clouds by galaxy outflows. V. The role of anisotropic thermal conduction, ApJ 951, 113 (2023), [arXiv:2304.09881](https://arxiv.org/abs/2304.09881), [doi:10.3847/1538-4357/acd63e](https://doi.org/10.3847/1538-4357/acd63e).
- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="stone-et-al-1992a"></a>Stone, J. M., Mihalas, D. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. III. The radiation hydrodynamic algorithms and tests, ApJS 80, 819–845 (1992), [doi:10.1086/191682](https://doi.org/10.1086/191682).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="townsend-2009"></a>Townsend, R. H. D., An exact integration scheme for radiative cooling in hydrodynamical simulations, ApJS 181, 391–397 (2009), [arXiv:0901.3146](https://arxiv.org/abs/0901.3146), [doi:10.1088/0067-0049/181/2/391](https://doi.org/10.1088/0067-0049/181/2/391).
- <a id="zingale-2014"></a>Zingale, M., pyro: a teaching code for computational astrophysical hydrodynamics, Astronomy and Computing 6, 52–62 (2014), [arXiv:1306.6883](https://arxiv.org/abs/1306.6883), [doi:10.1016/j.ascom.2014.07.003](https://doi.org/10.1016/j.ascom.2014.07.003).

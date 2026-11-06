# Problem setups and user functions

## 1. Overview

A problem setup supplies what the framework cannot know: the initial state, the domain and its boundaries, parameters of its own, and functions that act during a run, such as boundaries, sources or diagnostics. The references keep the code of a problem in one place and differ in its form and in how it reaches the framework. pyro makes each problem a module with a fixed interface that the driver finds by name, Ulula a class derived from an abstract base with optional methods, and Athena++ a file chosen at configuration that defines functions of the mesh and its blocks and enrols further functions at run time. The driver follows in [topic 37](37-driver-and-control-of-time-step.md), boundary conditions in [topic 4](04-boundary-conditions-and-ghost-cells.md) and source terms in [topic 13](13-source-terms.md).

## 2. Designs

### 2.1 Problems as modules

A problem of pyro is a module in the directory of problems of its solver, which the driver finds by its name, or a problem registered with the driver, such as one defined in a notebook. It provides a dictionary of the parameters it needs, named `problem.parameter` with their defaults, the inputs file read when none is given, a function that fills the data object from the parameters through the same interface for every solver, a function called at the end, mostly to print how the output can be analysed, and optionally source terms. Inputs files beside it set the domain, the boundaries and other parameters of a run. **[GK]** Problems that omit their dictionary of parameters stop at initialisation, since the driver reads it without a fallback.

Detail: [pyro 2.3.3](../references/pyro-synthesis.md#233-problems-and-tests), [pyro 3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters).

### 2.2 Problems as classes

A setup of Ulula is a class derived from an abstract base ([Diemer](#diemer-2025) 2025, §4.1), whose methods giving a short name and setting the initial conditions every setup must define. A wrapper of the base class initialises a simulation in steps.

1. Set the code units of the simulation.
2. Call the setup's method of initial conditions, which chooses the equation of state, gravity and domain and writes the primitive variables.
3. Stop if any physical cell has a density or pressure that is not positive.
4. Pass the update and boundary functions of the setup to the simulation where the setup overrides them, initialise gravity, convert to conserved variables and fill the boundaries.

Optional methods give a known solution for plots in one dimension, limits and colour maps of plots, and the update and boundary functions, whose defaults do nothing; the base class tells whether a setup overrides the last two by calling them without a simulation. The update function runs before the boundary conditions are filled, so that a setup can act on the simulation while the boundaries still follow automatically, and the boundary function runs after them, for boundaries of its own such as an inflow. The code does not check that these functions leave primitive and conserved variables consistent. Fifteen setups come prepared, each with an example in the code and an image of its result in the documentation.

Detail: [Ulula 2.2.3](../references/ulula-synthesis.md#223-updates-and-boundaries-of-the-user), [Ulula 2.8.1](../references/ulula-synthesis.md#281-the-setups), [Ulula 3.6](../references/ulula-synthesis.md#36-problem-setups).

### 2.3 Problem generators with enrolled functions

A problem generator of Athena++ is one file, chosen at configuration, that defines up to seven functions of the mesh and its blocks: the initial state of a block on a new run, the reading of parameters and enrolment of functions before any block exists, the allocation of data of each block, work after each cycle and in the last stage of each step, work before outputs, and work after the loop, for instance to compute errors. Empty defaults of all seven, declared weak, let the linker take those of the problem file where they exist. Within the function that reads the parameters, called before any block exists, the problem enrols further functions: boundary functions for faces flagged as user boundaries, conditions of refinement, generators of the mesh, explicit source terms, limits of the time step, a metric of general relativity, coefficients of diffusion and an orbital velocity. It may add outputs to the history with a reduction over the blocks, arrays of data for the mesh and for each block that restart files keep, output variables, and the cost of a block for balancing the load. A generator can also read the initial state from a file in HDF5.

Detail: [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [Athena 3.6](../references/athena-synthesis.md#36-problem-generators-and-user-functions).

## 3. Tests

Athena++ compiles every problem generator except the empty defaults and the reader of HDF5, in single and double precision, in groups with fitting options, and requires a state read from HDF5 to reproduce the input exactly, serially and on three processes. pyro's unit tests check the initial data of some problems, and its regression tests run problems against stored benchmarks ([topic 28, §2.5](28-verification-and-testing.md#25-regression-tests-and-reproducibility)). **[GK]** Apart from the problems whose initial data the unit tests check and the state read from HDF5, these tests show that problems compile or reproduce stored results, not that their initial states are those intended.

Detail: [Athena 3.6](../references/athena-synthesis.md#36-problem-generators-and-user-functions), [pyro 2.2.5](../references/pyro-synthesis.md#225-problems-and-tests), [pyro 2.4.12](../references/pyro-synthesis.md#2412-problems-and-tests), [pyro 2.7.2](../references/pyro-synthesis.md#272-problems-and-tests), [pyro 3.3](../references/pyro-synthesis.md#33-driver-simulations-and-runtime-parameters), [pyro 3.4](../references/pyro-synthesis.md#34-output-analysis-and-testing).

## 4. Assessment

Athena++ notes that its weak defaults rely on an extension of GNU, without which every problem file would have to define all seven functions. **[GK]** Modules with a fixed interface, as in pyro, are the simplest form in Python and keep the code of a problem in one file, beside its inputs files, but nothing forces a problem to define its parts, which the problems without parameters show. An abstract base class, as in Ulula, makes the required parts explicit and lets optional hooks default to nothing, which reads well and extends without changes to the framework. Enrolment of functions, as in Athena++, is the most general, letting a problem supply boundaries and conditions of refinement and add sources and diagnostics at defined points, and in Python it needs no linker tricks, as hooks are attributes that default to nothing. Declaring parameters with defaults and rejecting unknown ones catches misspellings, and checking positivity after the initial state, as Ulula does, catches broken setups early, while the consistency of variables after user functions is better enforced by the framework than left to the user. The production runs need a setup with a cloud that moves through a static corona, boundaries through which gas can leave on every side and diagnostics of mixing and cooling, which a class with hooks for boundaries, sources and history outputs covers; an inflow boundary enters only if the frame follows the cloud. Open are the form of a problem, the declaration of its parameters, and which hooks the framework offers.

## 5. Sources

- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).

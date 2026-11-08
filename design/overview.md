# Overview of mhdpy

*A paragraph on what mhdpy is, for a newcomer, and on what this overview holds and for whom: the goals, the context of a run, the layers and how a step runs through them, what the layers share, and the briefs that build them. About 80 words with the line below.*

**Where the work stands.** *The stratum in progress and its next brief, as part 6 lists them.*

## 1. Goals

*The goals, scope and success criteria of mhdpy, moved from §1.1 to §1.3 of CLAUDE.md in step 7 of `design/overview/plan.md`, with a pointer to the priorities, which stay in §1.4 of CLAUDE.md. About 500 words.*

### 1.1 Goals

### 1.2 Scope

### 1.3 Success criteria

## 2. Context of a run

*What a user brings to mhdpy, a problem setup with its parameters, what a run does with it, and what comes out for analysis, on the development machine and a small server. About 150 words.*

## 3. Layers

![The five strata of mhdpy, with the components of the first pass in red and the extensions in grey](overview/layers.svg)

mhdpy is cut into five strata by the kind of code that each holds, after the layers pattern of [Buschmann et al.](#buschmann-et-al-1996) (1996). Each stratum rests on those below it and is finished before the next is begun, with its briefs, then its requirements, then its code, as §2.3 of [CLAUDE.md](../CLAUDE.md) asks. A first pass builds the five strata for the production run of [§1.3](#13-success-criteria), hydrodynamics with radiative cooling, thermal conduction and a passive scalar, and provides for the rest of the scope where this costs little. Every other module of the scope of [§1.2](#12-scope) enters later, as an extension of the stratum of its kind of code, MHD first. No problem runs before the driver of stratum 5 exists, so that the lower strata are checked by tests of their own, the numerical core also by a small loop in its tests that steps problems with known solutions.

*Each subsection grows in step 6 of the plan into what its stratum holds, what it must provide to the strata above, and the tests that close it, in about 220 words.*

### 3.1 Infrastructure

The code that every stratum runs on and that knows nothing of grids or physics: the package and its installation ([topic 35](topics/35-packaging-configuration-and-build.md)), runtime parameters and units ([topic 37, §2.5](topics/37-driver-and-control-of-time-step.md#25-runtime-parameters-and-units)), the route of the kernels ([topic 41](topics/41-vectorised-and-compiled-kernels.md)), execution in parallel and the measure of cell updates ([topic 42](topics/42-parallelisation-and-performance.md)), and the tools of testing ([topic 28](topics/28-verification-and-testing.md)).

### 3.2 Mesh and data

The code that holds the state on the grid: coordinates with a geometry kept general ([topic 3](topics/03-grids-and-finite-volume-discretisation.md)), the arrays of the state with room for the face fields of MHD ([topic 36](topics/36-data-structures.md)), and ghost cells with the standard boundaries and their exchange between blocks ([topic 4](topics/04-boundary-conditions-and-ghost-cells.md)). Extensions: curvilinear coordinates ([topic 12](topics/12-curvilinear-coordinates.md)) and mesh refinement ([topic 40](topics/40-mesh-refinement.md)).

### 3.3 Numerical core

The code that advances the equations of the gas: its variables ([topic 1](topics/01-equations-and-their-variables.md)), equations of state ([topic 2](topics/02-equations-of-state.md)), reconstruction ([topic 6](topics/06-reconstruction-and-limiting.md)), Riemann solvers ([topic 7](topics/07-riemann-solvers.md)), the integrator ([topic 8](topics/08-time-integration.md)), source terms ([topic 13](topics/13-source-terms.md)), the coupling of processes within a step ([topic 18](topics/18-operator-splitting-and-coupling-of-processes.md)), the passive scalar, whose flux is the mass flux of the gas ([topic 21](topics/21-passive-scalars.md)), and open boundaries ([topic 5](topics/05-non-reflecting-boundaries.md)). Extensions: MHD with constrained transport ([topic 11](topics/11-constrained-transport.md)) first, then methods of higher order ([topic 9](topics/09-methods-of-higher-order.md)), artificial viscosity ([topic 10](topics/10-artificial-viscosity.md)) and relativistic MHD ([topic 25](topics/25-relativistic-mhd.md)).

### 3.4 Physics

The modules that add processes to the flow: diffusion ([topic 16](topics/16-diffusion.md)) and thermal conduction ([topic 17](topics/17-thermal-conduction.md)), and radiative cooling ([topic 20](topics/20-radiative-cooling.md)) with the integration of local, stiff sources ([topic 19](topics/19-reactions-chemistry-and-cooling.md)). Extensions: elliptic solvers and self-gravity ([topic 14](topics/14-elliptic-solvers.md), [topic 15](topics/15-self-gravity.md)), particles ([topic 22](topics/22-particles.md)), radiation ([topic 23](topics/23-radiation-transport.md)), the shearing box ([topic 24](topics/24-shearing-box-and-orbital-advection.md)), cosmic rays ([topic 26](topics/26-cosmic-rays.md)), driven turbulence ([topic 27](topics/27-driving-of-turbulence.md)) and chemical networks.

### 3.5 Driver and problems

The code that turns the solver into a run: the main loop and the control of its step ([topic 37](topics/37-driver-and-control-of-time-step.md)), problem setups and user functions ([topic 38](topics/38-problem-setups-and-user-functions.md)), outputs, restarts and analysis ([topic 39](topics/39-output-restarts-and-analysis.md)), and the problems that verify the whole scheme ([topic 29](topics/29-advection-and-linear-waves.md) to [topic 34](topics/34-cold-clouds-and-mixing-layers.md)).

## 4. One time step

*One step of the production run, with hydrodynamics, radiative cooling, thermal conduction and a passive scalar, traced down through the strata in numbered steps, each naming its stratum, with each choice of method left to its brief and linked to its topic. About 250 words.*

## 5. Crosscutting concepts

Some conventions bind every stratum, although no stratum holds them, and each is settled by the briefs of the stratum named: how kernels are written, vectorised or compiled ([topic 41](topics/41-vectorised-and-compiled-kernels.md)), execution in parallel and the measure of performance ([topic 42](topics/42-parallelisation-and-performance.md)), runtime parameters and units ([topic 37, §2.5](topics/37-driver-and-control-of-time-step.md#25-runtime-parameters-and-units)), and testing and verification ([topic 28](topics/28-verification-and-testing.md)), in stratum 1; the naming and indexing of variables ([topic 36](topics/36-data-structures.md)), in stratum 2; precision, floors and unphysical states ([topic 2](topics/02-equations-of-state.md)), in stratum 3; the way modules plug in, by boundaries, sources and the hooks of problems ([topic 13](topics/13-source-terms.md), [topic 38](topics/38-problem-setups-and-user-functions.md)), in strata 2, 3 and 5; and reproducibility, by recorded versions, seeds and exact restarts ([topic 39](topics/39-output-restarts-and-analysis.md)), in stratum 5.

*Each concept gains a sentence or two and the brief that settles it in step 6 of the plan, in about 300 words in all.*

## 6. Briefs

Briefs are opened stratum by stratum, from infrastructure upwards, those of the first pass before the extensions. A brief is opened in the lowest stratum whose code its decision shapes, even where most of its code lies higher: the coupling of processes within a step is decided with the integrator of stratum 3, although the driver of stratum 5 runs it.

*One subsection to a stratum, in the order of part 3, with a table of its briefs in the order in which they are opened, then a line on its requirements and code. A brief not yet opened is listed by its subject, since it receives its identifier only when it is opened. About 300 words.*

| Brief | Subject | Topics | Status | Changed in the overview |
|---|---|---|---|---|
| *Identifier, once opened* | *Subject* | *Topics, linked* | *Not begun, open, or decided on {date}* | *What the brief changed, with a link to the sub-decision* |

*Requirements: each document of the stratum, with its status, draft or agreed on {date}. Code: not begun, in progress or complete.*

## 7. Glossary

*The terms that a newcomer meets, in alphabetical order, each with an anchor, a sentence of explanation and its topic linked. The first use of a term in the text links to its entry. About 250 words.*

## Sources

*The established practice that the overview follows and the references that it cites directly, as anchored entries in the format of the topic summaries.*

- <a id="buschmann-et-al-1996"></a>Buschmann, F., Meunier, R., Rohnert, H., Sommerlad, P. and Stal, M., Pattern-oriented software architecture, volume 1: a system of patterns, Wiley (1996).

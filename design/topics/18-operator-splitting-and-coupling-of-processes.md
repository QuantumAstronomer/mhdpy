# Operator splitting and the coupling of processes

## 1. Overview

A flow with several processes, $\partial\mathbf{U}/\partial t = \mathcal{L}_\mathrm{A}(\mathbf{U}) + \mathcal{L}_\mathrm{D}(\mathbf{U}) + \mathcal{L}_\mathrm{R}(\mathbf{U})$ for advection, diffusion and reactions, can be advanced with one method and one time step for all, or split into parts that each take the method and step that suit them. Explicit advection allows a step proportional to $\Delta x$, explicit diffusion one proportional to $\Delta x^2$, and stiff reactions or cooling need far shorter steps or implicit integration, so that a common explicit step is needlessly expensive. Splitting pays for this freedom with a weaker coupling of the processes. Zingale's text sets out Strang splitting and a coupled split of advection and diffusion, ZEUS splits its source terms from the transport, Ulula splits its gravity by halves of a step, pyro integrates by spectral deferred corrections, and Athena++ couples most processes unsplit within the stages of its integrator, organised as task lists, and splits only super time-stepping off. The integrators follow in topic 8, diffusion in topics 16 and 17, reactions and cooling in topics 19 and 20, and the driver of a step in topic 37.

## 2. Methods

### 2.1 Strang splitting

Splitting solves for each operator in turn, with its own step and method, each acting as if the others were absent but starting from the state that they left ([Zingale's text](#zingale-2025), §11.1). With $\mathcal{S}^\mathrm{X}_{\Delta t}$ the solution operator of process X over a step, the symmetric form of [Strang](#strang-1968) (1968) is of second order (eq. 11.4):

$$\mathbf{U}^{n+1} = \mathcal{S}^\mathrm{R}_{\Delta t/2}\,\mathcal{S}^\mathrm{D}_{\Delta t}\,\mathcal{S}^\mathrm{R}_{\Delta t/2}\,\mathbf{U}^n.$$

For a flame, the reactions advance by half a step as ordinary differential equations in each cell, the diffusion by a full step with Crank–Nicolson from the result, and the reactions by another half step (eqs. 11.5 to 11.7). Reacting flow is split alike, with the hydrodynamics in place of the diffusion, advanced by its own method without seeing the reactions (eqs. 12.32 to 12.36). No source term of one process enters the update of another. ZEUS splits its operator into a source step, for the pressure gradient, gravity, the artificial viscosity and the compressional heating, and a transport step for the advection, each applied to the result of the one before ([Stone and Norman](#stone-norman-1992a) 1992a, §4). Ulula adds its gravity in Strang's form, by half a step before the sweeps and half a step after them, and Athena++ its super time-stepping of diffusion, RKL2 by half a step before and after the integrator (topic 16). pyro's reacting solver is laid out to burn and diffuse by half a step on either side of the hydrodynamics, but its functions for burning and diffusion hold only comments. Athena in the simulations of [Armillotta, Fraternali and Marinacci](#armillotta-et-al-2016) (2016) adds radiative cooling after the hydrodynamic step at first order and advances conduction by semi-implicit sweeps of the temperature, while AthenaPK splits conduction off the MHD with two super steps per update ([Brüggen, Scannapieco and Grete](#bruggen-et-al-2023) 2023; topics 17 and 20). **[GK]** The error of a split step lies in the commutator of the operators: the sequential form $\mathcal{S}^\mathrm{D}_{\Delta t}\mathcal{S}^\mathrm{R}_{\Delta t}$ is of first order in $\Delta t$, the symmetric form of second, and both are exact where the operators commute.

Detail: [Zingale 2.8.1](../references/computational-hydrodynamics-synthesis.md#281-operator-splitting), [Zingale 2.8.2](../references/computational-hydrodynamics-synthesis.md#282-diffusion-and-reactions), [Zingale 2.8.6](../references/computational-hydrodynamics-synthesis.md#286-operator-splitting-for-reacting-flow), [pyro 2.4.11](../references/pyro-synthesis.md#2411-reactions), [Ulula 2.3.4](../references/ulula-synthesis.md#234-source-terms), [ZEUS 2.1.2](../references/zeus-synthesis.md#212-operator-splitting), [Athena 2.11.2](../references/athena-synthesis.md#2112-super-time-stepping), [Conduction and cooling 2.4.5](../references/conduction-and-cooling-synthesis.md#245-super-time-stepping-of-conduction), [Conduction and cooling 2.7.1](../references/conduction-and-cooling-synthesis.md#271-operator-splitting-and-the-limit-on-the-time-step), [Conduction and cooling 3.1](../references/conduction-and-cooling-synthesis.md#31-athena-in-the-simulations-of-2016).

### 2.2 Coupled splitting

A split stays of second order without symmetric half steps if each part sees the other as a source (Zingale's text, eqs. 11.9 to 11.15). For viscous Burgers' equation, $u_t + [u^2/2]_x = \epsilon u_{xx}$, a step runs as follows.

1. Predict the face states as for advection (topic 8), with the diffusion at the old time as a source, $u^{n+1/2}_{i+1/2,\mathrm{L}} = u_i + \tfrac{1}{2}(1 - u_i\Delta t/\Delta x)\,\delta u_i + \tfrac{1}{2}\Delta t\,\epsilon\,(u_{xx})_i$.
2. Solve the Riemann problems and form the advective term $\mathcal{L}^{n+1/2}_{\mathrm{A},i}$ from the fluxes.
3. Diffuse by Crank–Nicolson with this term as a source, $(u^{n+1}_i - u^n_i)/\Delta t = \tfrac{1}{2}[\mathcal{L}_\mathrm{D}(u^n) + \mathcal{L}_\mathrm{D}(u^{n+1})]_i + \mathcal{L}^{n+1/2}_{\mathrm{A},i}$, by a tridiagonal solver or multigrid.

Only advection then limits the step. pyro's viscous Burgers solver follows this pattern in two dimensions, with multigrid for the implicit step (topic 14). The source terms of topic 13 enter the predicted states in the same way.

Detail: [Zingale 2.8.3](../references/computational-hydrodynamics-synthesis.md#283-advection-and-diffusion), [pyro 2.3.2](../references/pyro-synthesis.md#232-the-viscous-solver).

### 2.3 Unsplit coupling within stages

The method of lines adds every explicit process to the right-hand side of each stage, so that the integrator couples them at its own order and balances between terms, such as a source against a flux, hold within a stage (topic 8). Athena++ adds its diffusive fluxes before the update and its source terms after it, in every stage, which it calls the most accurate choice, and solves self-gravity between stages, so that each stage sees the potential of its own density (topics 13, 15 and 16). Spectral deferred corrections, as pyro implements them, iterate the update at three Gauss–Lobatto nodes, each iteration correcting the integral of the right-hand sides of the previous one, so that four iterations reach fourth order at nine evaluations per step (topic 8). The method served as the model for the schemes of higher order in Castro. **[GK]** There, [Zingale et al.](#zingale-et-al-2019) (2019) couple stiff nuclear reactions to the hydrodynamics by the same corrections, without splitting, each iteration raising the order by one up to that of the quadrature.

Detail: [pyro 2.4.10](../references/pyro-synthesis.md#2410-spectral-deferred-corrections), [Athena 2.11.1](../references/athena-synthesis.md#2111-viscosity-thermal-conduction-and-non-ideal-mhd).

### 2.4 Task lists

Athena++ executes the processes of a stage as a list of tasks, each with an identifier, the tasks it depends on and a function, with identifiers and dependencies stored as bit fields ([Stone et al.](#stone-et-al-2020) 2020, §2.5). A block runs the first task whose dependencies are done. A task that still waits for messages fails and is retried later, so that communication hides behind computation, and blocks may even follow lists of their own. The main list of a stage runs in this order.

1. Compute the diffusive and then the hyperbolic fluxes, with the electric fields in MHD, and correct them between levels of refinement.
2. Update the conserved variables and the field, and add the source terms.
3. Exchange and set the boundaries, and prolong between levels.
4. Convert to primitive variables, apply the physical boundaries and the work of the user, and in the last stage compute the next time step and flag blocks for refinement.

Passive scalars, chemistry, radiation, cosmic rays, the shearing box and orbital advection insert their tasks into this list, while super time-stepping, multigrid, implicit radiation and others run lists of their own. The combination of modules thus becomes flexible at run time, where Athena nested preprocessor flags in its main loop (topic 37).

Detail: [Athena 3.5](../references/athena-synthesis.md#35-task-lists-and-parallelisation).

## 3. Tests

A diffusion–reaction equation with the source $\psi(1 - \psi)/4\tau$ of the KPP type turns a smoothed top hat into a travelling flame front, shown for 256 cells with $\mathcal{D} = 0.1$ and $\tau = 1$ (Zingale's text, eq. 11.8). Its known speed $\sqrt{\mathcal{D}/\tau}$ and thickness $\sqrt{\mathcal{D}\tau}$ check Strang splitting. Viscous Burgers' equation tests the coupled split by its convergence against a benchmark on 4096 cells, averaged onto each coarser grid. Athena++ runs a linear wave of MHD serially and on several processes and threads, and requires the error on one process or thread to equal the serial one exactly and the others to differ from it by less than $5 \times 10^{-4}$, which checks that the task lists give the same answer however the work is distributed.

Detail: [Zingale 2.8.2](../references/computational-hydrodynamics-synthesis.md#282-diffusion-and-reactions), [Zingale 2.8.3](../references/computational-hydrodynamics-synthesis.md#283-advection-and-diffusion), [Athena 3.5](../references/athena-synthesis.md#35-task-lists-and-parallelisation).

## 4. Assessment

The coupled split of viscous Burgers' equation converges at second order for $\epsilon = 0.005$, with the shock in the same place for all viscosities, and Crank–Nicolson makes sharp initial data of the flame jagged, so that they must be smooth (Zingale's text). The numerical experiments that Stone and Norman (1992a) cite found a sequence of partial updates more accurate than a single update from the old state, and their order of little consequence. **[GK]** pyro's reacting solver does not run at version 4.5.1. Splitting lets each process take its own method and step, which stiff cooling and fast conduction require, but it loses balances that the processes strike together, such as a cooling layer in equilibrium with the flow through it, and the symmetric form is of second order only if every part is. Unsplit coupling in the stages keeps such balances and is the simplest to extend, at the price of one step for all processes, which suits explicit terms of comparable time scales. Spectral deferred corrections couple stiff terms at high order but multiply the work per step. Task lists make the order of operations explicit and modular, at some cost in readability compared with a fixed loop. Open are how the production runs combine explicit hydrodynamics, conduction faster than the flow, stiff radiative cooling and a passive scalar, whether they split these in sequence at first order, as the simulations of 2016 do, or symmetrically, and whether the balance of heating and cooling survives the split.

## 5. Sources

- <a id="armillotta-et-al-2016"></a>Armillotta, L., Fraternali, F. and Marinacci, F., Efficiency of gas cooling and accretion at the disc–corona interface, MNRAS 462, 4157–4170 (2016), [arXiv:1608.06290](https://arxiv.org/abs/1608.06290), [doi:10.1093/mnras/stw1930](https://doi.org/10.1093/mnras/stw1930).
- <a id="bruggen-et-al-2023"></a>Brüggen, M., Scannapieco, E. and Grete, P., The launching of cold clouds by galaxy outflows. V. The role of anisotropic thermal conduction, ApJ 951, 113 (2023), [arXiv:2304.09881](https://arxiv.org/abs/2304.09881), [doi:10.3847/1538-4357/acd63e](https://doi.org/10.3847/1538-4357/acd63e).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="strang-1968"></a>Strang, G., On the construction and comparison of difference schemes, SIAM Journal on Numerical Analysis 5, 506–517 (1968), [doi:10.1137/0705041](https://doi.org/10.1137/0705041).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).
- <a id="zingale-et-al-2019"></a>Zingale, M., Katz, M. P., Bell, J. B., Minion, M. L., Nonaka, A. J. and Zhang, W., Improved coupling of hydrodynamics and nuclear reactions via spectral deferred corrections, ApJ 886, 105 (2019), [arXiv:1908.03661](https://arxiv.org/abs/1908.03661).

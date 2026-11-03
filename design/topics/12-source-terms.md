# Source terms

## 1. Overview

Source terms add to the conservation laws a right-hand side, $\partial\mathbf{U}/\partial t + \nabla\cdot\mathbf{F} = \mathbf{S}$, that no flux carries: gravity, the forces of a rotating frame, heating and the damping of a sponge. A scheme of second order must centre them in time, both in the prediction of the face states and in the conservative update, and must keep the balances that they strike with the fluxes, such as hydrostatic equilibrium. Zingale's text sets out the centring, pyro adds gravity, heating and sponges by a predictor and corrector, Ulula adds gravity in two half steps around its sweeps, ZEUS applies its forces in a source step split from the transport, and Athena++ adds a list of explicit terms in each stage of its integrator. The geometric terms of curvilinear coordinates follow in topic 11, self-gravity in topic 14, cooling and reactions, whose stiffness calls for other methods, in topic 17, the shearing box in topic 21 and the splitting of processes in topic 16. Schemes that keep a general equilibrium exactly are not described.

## 2. Methods

### 2.1 Centring in time

A source enters the prediction of the face states through the time derivative of the Taylor expansion and adds $(\Delta t/2)\,\mathbf{S}_i$, from the cell-centred source, to both states of the cell, which is of second order ([Zingale's text](#zingale-2025), eqs. 8.79 to 8.82). PPM can instead carry it through the characteristic tracing, as gravity, which acts on the velocity alone, then adds to each wave the average of $g$ over its domain of dependence. The update needs the source centred in time, usually as

$$\mathbf{U}^{n+1}_i = \mathbf{U}^n_i - \frac{\Delta t}{\Delta x}\left(\mathbf{F}_{i+1/2} - \mathbf{F}_{i-1/2}\right) + \frac{\Delta t}{2}\left[\mathbf{S}(\mathbf{U}^n_i) + \mathbf{S}(\mathbf{U}^{n+1}_i)\right],$$

which looks implicit but can often be evaluated in sequence (eqs. 8.87 to 8.90). For a constant gravity, $\mathbf{S} = (0, \rho g, \rho v_x g)$, the update runs as follows.

1. Update the density with the fluxes alone.
2. Update the momentum with the fluxes and $\tfrac{1}{2}\Delta t\,(\rho^n + \rho^{n+1})\,g$.
3. Update the energy with the fluxes and $\tfrac{1}{2}\Delta t\,[(\rho v_x)^n + (\rho v_x)^{n+1}]\,g$.

A source such as the Coriolis force needs an implicit update, but one local to the cell, which can be solved analytically. The codes centre their sources in different ways. pyro corrects an update with the old source, $\mathbf{U}^\star = \mathbf{U}^n + \ldots + \Delta t\,\mathbf{S}(\mathbf{U}^n)$, by $\tfrac{1}{2}\Delta t\,[\mathbf{S}(\mathbf{U}^\star) - \mathbf{S}(\mathbf{U}^n)]$, with the corrected momentum in the source of the energy. Ulula adds half a step of the sources before its sweeps and half after them. ZEUS applies the pressure gradient, gravity and the inertial forces of its coordinates in the first substep of its source step, at the old time level (topic 16). Athena++ adds its sources in each stage of the integrator, with the weight of the stage and the primitive variables and fluxes of that stage, so that the Runge–Kutta method centres them.

Detail: [Zingale 2.5.17](../references/computational-hydrodynamics-synthesis.md#2517-source-terms), [pyro 2.4.3](../references/pyro-synthesis.md#243-sources-and-transverse-corrections), [pyro 2.4.5](../references/pyro-synthesis.md#245-source-terms), [Ulula 2.3.4](../references/ulula-synthesis.md#234-source-terms), [ZEUS 2.3.1](../references/zeus-synthesis.md#231-substeps-and-forces), [Athena 2.9.1](../references/athena-synthesis.md#291-physical-source-terms).

### 2.2 Gravity

A fixed acceleration $\mathbf{g}$ adds $\rho\mathbf{g}$ to the momentum and $\rho\mathbf{v}\cdot\mathbf{g}$ to the total energy, in pyro and Athena++ along a coordinate direction. Ulula counts the potential energy in its total energy, so that a fixed potential changes only the momentum, by $-\rho\,\nabla\Phi\,\Delta t$, while self-gravity adds $\rho$ times the change of the potential since its last solution to the energy ([Diemer](#diemer-2025) 2025). A fixed potential of Ulula has its gradient taken by central differences once, which needs the potential in the ghost cells too. The point mass of Athena++ subtracts $\Delta t\,\rho\,\langle 1/r\rangle\,GM/r_\mathrm{v}$ from the radial momentum, with the volume average $\langle 1/r\rangle$ and the radial volume centre $r_\mathrm{v}$ of topic 11, and takes the work of gravity from the radial mass fluxes $F_\rho$ through the two faces of the cell,

$$\Delta E = -\tfrac{1}{2}\,\Delta t\,GM\,\frac{F_{\rho,i-1/2} + F_{\rho,i+1/2}}{r_\mathrm{v}^2},$$

in spherical-polar coordinates. In cylindrical coordinates the point mass acts with the cylindrical radius alone. ZEUS differences the gradient of the potential on its staggered mesh, $-(\Phi_i - \Phi_{i-1})/\Delta x$ on the face of $v_x$, with the potential from the Poisson equation at the start of the step (topic 14).

Detail: [pyro 2.4.5](../references/pyro-synthesis.md#245-source-terms), [Ulula 2.7.1](../references/ulula-synthesis.md#271-the-modes-of-gravity), [Ulula 2.7.2](../references/ulula-synthesis.md#272-fixed-potentials), [Ulula 2.7.4](../references/ulula-synthesis.md#274-the-gravitational-sources), [ZEUS 2.3.1](../references/zeus-synthesis.md#231-substeps-and-forces), [Athena 2.9.1](../references/athena-synthesis.md#291-physical-source-terms).

### 2.3 Rotating frames

A frame rotating at $\boldsymbol{\Omega}_0$ adds the Coriolis force $-2\rho\,\boldsymbol{\Omega}_0\times\mathbf{v}$ and the centrifugal force $\rho\,\Omega_0^2\varpi$ along the cylindrical radius $\varpi$, with the work of the latter in the energy. Athena++ evaluates them with the speed of the frame $v_\mathrm{c} = \Omega_0R_\mathrm{v}$ at the volume centre: in cylindrical coordinates the radial momentum gains $\Delta t\,\langle 1/R\rangle\,(2v_\mathrm{c}\rho v_\phi + \rho v_\mathrm{c}^2)$, and the azimuthal momentum loses $\Delta t\,\langle 1/R\rangle\,v_\mathrm{c}(\rho v_R + \bar F_\rho)$, with half of the radial momentum from the cell and half from the mean radial mass flux of its faces, from which the work of the centrifugal force also comes. The shearing box and orbital advection add terms of their own (topic 21).

Detail: [Athena 2.9.1](../references/athena-synthesis.md#291-physical-source-terms).

### 2.4 Heating, sponges and problem sources

pyro lets a problem return a vector of sources, which its convective problems use for a heating $\rho\epsilon_\mathrm{h}\exp[-(y - y_\mathrm{h})^2/d^2]$ in a layer. A sponge damps the velocity where the density is low, as above an atmosphere, by $-(f/\tau_\mathrm{s})\rho\mathbf{v}$ in the momentum. The factor $f$ rises from 0 to 1 as a half cosine in the density between two thresholds, and $\tau_\mathrm{s}$ is best a few to ten time steps. pyro divides the momenta by $1 + \Delta t\,f/\tau_\mathrm{s}$, an implicit step, and changes the total energy by the change of the kinetic energy alone, so that the internal energy is unchanged. Athena++ lets a problem enrol a function of explicit sources, which it applies after its own terms and to the passive scalars as well. **[GK]** pyro's source of the polar momentum on its spherical grid, $-(\rho v_r)(\rho v_\theta)/\rho$, lacks the factor $1/r$ of $-\rho v_rv_\theta/r$, which holds only at $r = 1$.

Detail: [pyro 2.4.5](../references/pyro-synthesis.md#245-source-terms), [Athena 2.9.1](../references/athena-synthesis.md#291-physical-source-terms).

## 3. Tests

pyro holds an isothermal atmosphere, $\rho = e^{-y/H}$ with the pressure integrated by the trapezoidal rule of discrete hydrostatic balance, at rest for three units of time, which tests the gravitational source, and heats a uniform medium at its centre to test the sources of energy. Its convective problems heat a layer of an adiabatic atmosphere with a sponge above it. Ulula lets a Gaussian blob fall freely under $g = 1$ in a domain with outflow boundaries, so that the profile must move to $x = 0.8 - gt^2/2$ with the velocity $-gt$ and the pressure unchanged, and uses it for a test of convergence. Its tidal disruption sends a blob past a point mass of strong gradient, without a known solution.

Detail: [pyro 2.4.12](../references/pyro-synthesis.md#2412-problems-and-tests), [Ulula 2.8.5](../references/ulula-synthesis.md#285-free-fall), [Ulula 2.8.14](../references/ulula-synthesis.md#2814-tidal-disruption).

## 4. Assessment

In Ulula's free fall the blob follows the known solution, its peak of 1.1 sinking slightly by $t = 1$ (Diemer 2025). **[GK]** Gravity and the forces of a rotating frame are easy to centre in time to second order, by a sequential update, a predictor and corrector, or the stages of a Runge–Kutta method, which takes in sources without further work. Taking the work of gravity from the mass fluxes, as Athena++ does, keeps the energy consistent with the transport of mass, and counting the potential in the total energy, as Ulula does, conserves the sum exactly for a fixed potential. The harder problem is balance: a stratified atmosphere at rest is a cancellation between the pressure flux and the source, which the references keep only with special slopes and boundaries (topics 4 and 5), and errors there drive spurious flows. Stiff sources need implicit or subcycled updates (topic 17). Open are how sources are registered in the lower layers so that new physics adds terms without changes to the framework, whether the energy source of gravity is taken from the fluxes, and whether a well-balanced scheme is needed for stratified atmospheres.

## 5. Sources

- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

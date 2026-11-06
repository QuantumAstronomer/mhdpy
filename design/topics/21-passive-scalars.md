# Passive scalars

## 1. Overview

A passive scalar is a quantity per unit mass that the flow carries without being acted on by it, such as a dye that traces mixing, the metallicity of the gas, or the mass fractions of species between reactions. Its density obeys a continuity equation of its own, and its flux is the mass flux times the scalar on the upwind side of a face, so that it needs no Riemann solver of its own. Zingale's text derives this from the characteristic structure and sets out how mass fractions are kept summing to one, pyro carries scalars among its variables and upwinds them in its Riemann solvers, and Athena++ implements them as a module of their own, with floors, diffusion and the exchange between blocks. Ulula and ZEUS carry no scalars. Reactions that change the species follow in topic 19, the reconstruction that they share with the gas in topic 6 and their diffusion in topic 16.

## 2. Methods

### 2.1 Equations and variables

With $C$ a scalar per unit mass, a concentration, its conserved density $\rho C$ obeys a continuity equation ([Zingale's text](#zingale-2025), eqs. 12.2 to 12.5; [Stone et al.](#stone-et-al-2020) 2020, eq. 20):

$$\frac{\partial(\rho C)}{\partial t} + \nabla\cdot(\rho C\mathbf{v}) = 0.$$

With the continuity equation of the gas, this becomes $DC/Dt = 0$: the scalar of a fluid element does not change as it moves. The conserved variables hold $\rho C$ and the primitive ones $C$, in pyro as in Athena++. Athena++ sets the number of scalars at configuration, zero by default, and stores them in arrays and registers of their own, indexed like those of the gas. With chemistry, its first scalars hold the abundances of the network. For several species the partial densities sum to the density, so that evolving both over-specifies the system (topic 19).

Detail: [Zingale 2.8.4](../references/computational-hydrodynamics-synthesis.md#284-reactive-hydrodynamics), [pyro 2.4.1](../references/pyro-synthesis.md#241-variables-and-equation-of-state), [Athena 2.12.1](../references/athena-synthesis.md#2121-advection).

### 2.2 Upwinded fluxes

In the primitive variables, a scalar adds the eigenvalue $v_x$ with a right eigenvector that has only a scalar component, while the other eigenvectors have none, so that the scalar is advected with the flow and jumps only across the contact (Zingale's text, eqs. 12.41 and 12.42). It needs no star state. Its face states follow the reconstruction of topic 6 with this eigenvalue in the characteristic tracing, as in pyro, and the Riemann solver takes the scalar from the left or the right state by the sign of the speed of the contact. pyro's solvers take it, like the transverse velocity, from the upwind side. Athena++ reconstructs the concentrations by the method of the gas, by donor cell in the first stage of VL2 as the gas is, and multiplies the mass flux $F_\rho$ of the Riemann solver by the upwind state:

$$F_{C,i+1/2} = \begin{cases} F_{\rho,i+1/2}\,C_{\mathrm{L},i+1/2}, & F_{\rho,i+1/2} \ge 0, \\ F_{\rho,i+1/2}\,C_{\mathrm{R},i+1/2}, & F_{\rho,i+1/2} < 0. \end{cases}$$

The scalars are then updated with the same registers and flux divergence as the gas in every stage. At fourth order, Athena++ converts the face averages to point values, multiplies them by the pointwise mass fluxes, and corrects the products back to face averages by the transverse Laplacian, as for the gas (topic 9). pyro's solver of fourth order, by contrast, leaves its scalars out of the conversion to point values, so that they enter its reconstruction as zero and the last of them gets no flux, while no problem of its unsplit compressible solver carries a scalar. **[GK]** With equal states on both sides of every face, the scalar fluxes are $C$ times the mass fluxes, so that a uniform scalar stays uniform, because its fluxes are built from those of the gas.

Detail: [Zingale 2.8.6](../references/computational-hydrodynamics-synthesis.md#286-operator-splitting-for-reacting-flow), [pyro 2.4.2](../references/pyro-synthesis.md#242-interface-states), [pyro 2.4.7](../references/pyro-synthesis.md#247-riemann-solvers), [pyro 2.4.9](../references/pyro-synthesis.md#249-the-fourth-order-solver), [Athena 2.12.1](../references/athena-synthesis.md#2121-advection).

### 2.3 Floors and the sum of mass fractions

After an update the mass fractions $X_k$ of several species may no longer sum to one, and Zingale's text names three remedies (§12.2.1). The density can be defined as $\sum_k\rho X_k$ rather than taken from the continuity equation. The face states of $X_k$ can be renormalised to sum to one, which then holds for the updated averages too, as in [Plewa and Müller](#plewa-muller-1999) (1999). Or the limiting can preserve the sum, for piecewise linear reconstruction by applying the most restrictive limited slope to all species.

Athena++ keeps its scalars non-negative by floors. After PPM or WENO, though not after donor cell or PLM, the face states are raised to a floor common to all scalars, and the conversion to primitive variables raises each $\rho C$ to at least the floor times the density, since fluxes in several dimensions can drive it lower. A note in the code warns that this floor adds scalar mass and can violate global conservation strongly, for instance in the first cycles of the slotted cylinder. A further floor, and that of the fourth order, raise only the primitive values and leave the conserved scalars unchanged.

Detail: [Zingale 2.8.6](../references/computational-hydrodynamics-synthesis.md#286-operator-splitting-for-reacting-flow), [Athena 2.12.1](../references/athena-synthesis.md#2121-advection).

### 2.4 Scalars in the framework

In Athena++ the scalar fluxes follow those of the gas, whose mass fluxes they need, and the sources of a stage follow the updates of gas and scalars. The conserved scalars are exchanged between blocks, across levels of refinement with the corrections of their fluxes, and across shearing-periodic boundaries, while the physical boundaries act on the concentrations, as those of the gas act on its primitive variables. Orbital advection remaps the scalars like the conserved variables of the gas, restart files and refinement register them, and the history adds the integral of each over the volume. The source function of a problem may add the rates of reactions, and the chemistry integrates its network over the whole step in the last stage (topic 19). With the gas held fixed, its mass fluxes still carry the scalars and the step follows from the widths of the cells and the velocity alone, which isolates the advection, as in the tests of [Mignone](#mignone-2014) (2014).

Athena++ lets all scalars diffuse with one constant coefficient $\nu_\mathrm{s}$, through the flux $-\nu_\mathrm{s}\bar{\rho}\nabla C$, with $\bar{\rho}$ the mean density of the two cells of a face. The coefficient cannot depend on position or on the variables. The diffusive fluxes join the advective ones in each stage, or enter only the stages of super time-stepping, and the explicit limit $\Delta x^2/\nu_\mathrm{s}$, times a factor from 1/2 in one dimension to 1/6 in three, joins the limits of the step (topic 16).

Detail: [Athena 2.12.1](../references/athena-synthesis.md#2121-advection), [Athena 2.12.2](../references/athena-synthesis.md#2122-diffusion-and-tests).

## 3. Tests

A Gaussian profile of concentration in a gas at rest diffuses as the analytic Gaussian, in one, two or three dimensions and with cylindrical or spherical-polar coordinates as well. Athena++'s regression runs it in one dimension on 256 and 512 cells and requires the $L_1$ error to fall faster than the resolution to the power $-1.99$, explicitly and with super time-stepping. The Gaussian starts at a time $t_0$ of its analytic evolution, so that the error is measured against the Gaussian of time $t_0 + t$.

A slotted cylinder of scalar after [Zalesak](#zalesak-1979) (1979) rotates rigidly once about the centre of a periodic square of $100 \times 100$ cells, its sharp edges and narrow slot testing the limiter. The problem of Athena++ takes the cell averages and the errors by Gauss–Legendre quadrature and can refine on the gradient of the scalar. [Felker and Stone](#felker-stone-2018) (2018) advect the same shape as the velocity normal to the plane, a passive quantity of the flow, to compare reconstructions of second and fourth order.

The four relativistic shock tubes of Athena++ each carry a scalar of 0 to the left of the interface and 1 to its right. At the end, the scalar must keep these values outside a band of width 0.1 set for each problem, so that it follows the contact. A run of Sod's shock tube with two scalars is restarted from its initial state and passes if both runs complete.

Detail: [Athena 2.7.2](../references/athena-synthesis.md#272-tests-of-the-hydrodynamic-subsystem), [Athena 2.8.7](../references/athena-synthesis.md#287-tests-in-curvilinear-coordinates), [Athena 2.12.2](../references/athena-synthesis.md#2122-diffusion-and-tests).

## 4. Assessment

In the slotted cylinder, limited reconstructions keep the advected quantity monotone, while unlimited ones oscillate as strongly as the cylinder is high, and the limited fourth order keeps the discontinuous slot, which the second order loses, with a much narrower edge and much slower dissipation (Felker and Stone 2018). The tests of Athena++ report thresholds rather than errors, and its code warns that fluxes in several dimensions drive scalars below zero and that its floor then violates their conservation strongly. **[GK]** Upwinding with the mass flux makes scalars cheap, any number of them at the cost of a reconstruction and a product per face, and consistent with the gas, so that a uniform scalar stays uniform. A scalar measures mixing only down to the numerical diffusion of the scheme, so that the mixing of cloud and corona that it traces depends on the resolution and on the limiter. Floors buy positivity at the price of conservation, which a limiting of the fluxes that keeps the bounds would avoid. In the production runs, the metallicity is such a scalar, passive in its transport but active through the cooling function, which depends on it (topic 19). Open are whether the scalars share the reconstruction of the gas, whether a floor is needed, and how the metallicity of a mixed cell enters the cooling.

## 5. Sources

- <a id="felker-stone-2018"></a>Felker, K. G. and Stone, J. M., A fourth-order accurate finite volume method for ideal MHD via upwind constrained transport, Journal of Computational Physics 375, 1365–1400 (2018), [arXiv:1711.07439](https://arxiv.org/abs/1711.07439), [doi:10.1016/j.jcp.2018.08.025](https://doi.org/10.1016/j.jcp.2018.08.025).
- <a id="mignone-2014"></a>Mignone, A., High-order conservative reconstruction schemes for finite volume methods in cylindrical and spherical coordinates, Journal of Computational Physics 270, 784–814 (2014), [doi:10.1016/j.jcp.2014.04.001](https://doi.org/10.1016/j.jcp.2014.04.001).
- <a id="plewa-muller-1999"></a>Plewa, T. and Müller, E., The consistent multi-fluid advection method, A&A 342, 179–191 (1999), [arXiv:astro-ph/9807241](https://arxiv.org/abs/astro-ph/9807241).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="zalesak-1979"></a>Zalesak, S. T., Fully multidimensional flux-corrected transport algorithms for fluids, Journal of Computational Physics 31, 335–362 (1979), [doi:10.1016/0021-9991(79)90051-2](https://doi.org/10.1016/0021-9991%2879%2990051-2).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

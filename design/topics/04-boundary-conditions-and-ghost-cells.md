# Boundary conditions and ghost cells

## 1. Overview

A scheme updates every zone with the same stencil, which near the edge of the domain reaches beyond it. All five references therefore extend the grid by ghost cells, which exist only to carry the boundary conditions, so that one update serves every zone. At a physical boundary, the condition that fills them stands in for the world outside the domain, as a periodic, outflow, reflecting, inflow or hydrostatic boundary or one that the problem defines. At a boundary between blocks of a decomposed domain, the ghost cells take their values from the neighbour. Every reference provides periodic, outflow and reflecting boundaries; pyro adds hydrostatic ones, ZEUS conditions on the electromotive force, and Athena++ poles and the exchange between blocks. Boundaries that let every wave leave without reflection are only named, by ZEUS after [Thompson](#thompson-1987) (1987), and applied there to the toroidal components alone; the non-reflecting conditions of other codes follow in topic 5.

## 2. Methods

### 2.1 Ghost cells

The first and last zones of the domain along a direction are $\mathrm{lo}$ and $\mathrm{hi}$, and the $n_\mathrm{g}$ ghost cells beyond them are $\mathrm{lo}-1-k$ and $\mathrm{hi}+1+k$, with $k = 0, \ldots, n_\mathrm{g}-1$ ([Zingale's text](#zingale-2025), fig. 3.2). Their number is the reach of the stencil beyond the domain. A method of first order needs one, piecewise linear reconstruction two, as the state on the boundary face needs the slope in the first ghost cell and that slope the second, and the PPM of Athena++ three (topic 6). The ghost cells are filled anew by explicit formulae before every update that reads them: in every stage of the integrator in pyro and Athena++, after each sweep in Ulula and after each substep in ZEUS ([Stone and Norman](#stone-norman-1992a) 1992a, §4.5). Ulula fills the ghost cells at the corners of the domain explicitly, and Athena++ by applying its conditions direction by direction, each covering the ghost cells of those before. **[GK]** Corners matter to stencils that reach diagonally, such as the transverse corrections of unsplit schemes (topic 8).

Detail: [Zingale 2.2.5](../references/computational-hydrodynamics-synthesis.md#225-boundary-conditions-and-ghost-cells), [Zingale 2.3.8](../references/computational-hydrodynamics-synthesis.md#238-the-predictor-corrector-scheme), [pyro 2.4.8](../references/pyro-synthesis.md#248-the-method-of-lines-solver), [Ulula 2.2.2](../references/ulula-synthesis.md#222-boundary-conditions), [Ulula 2.3.2](../references/ulula-synthesis.md#232-dimensional-splitting), [ZEUS 2.5.1](../references/zeus-synthesis.md#251-boundary-conditions), [Athena 3.2](../references/athena-synthesis.md#32-arrays-the-mesh-and-its-blocks), [Athena 3.3](../references/athena-synthesis.md#33-boundaries-and-their-communication).

### 2.2 Periodic, outflow and reflecting boundaries

Three conditions are common to all references (Zingale's text, eqs. 3.16 to 3.19, 8.58 to 8.60). For any variable $f$ at the lower boundary, and alike at the upper one,

$$\text{periodic: } f_{\mathrm{lo}-1-k} = f_{\mathrm{hi}-k}, \qquad \text{outflow: } f_{\mathrm{lo}-1-k} = f_\mathrm{lo}, \qquad \text{reflecting: } f_{\mathrm{lo}-1-k} = \pm f_{\mathrm{lo}+k},$$

with the minus sign for the normal velocity $v_\mathrm{n}$ and the plus sign for the other hydrodynamic variables. A periodic boundary wraps the domain around, outflow continues the flow with zero gradient, and reflection mirrors the domain, as a wall or a plane of symmetry does, so that an odd variable vanishes on the boundary. ZEUS adds an axis of symmetry, at which the third, azimuthal component of the velocity is odd as well.

Ulula's documentation states what each kind conserves: periodic boundaries mass, momentum and energy, walls mass and energy, and outflow boundaries nothing. These can even draw gas in where the flow at the edge points into the domain.

**[GK]** A wall pairs each state with its mirror image, so that the Riemann problem on the wall is symmetric and its contact rests there. No mass, tangential momentum or energy crosses the wall, and only the pressure acts on it. Ulula's HLL and HLLC fluxes reproduce this only while the flow meets the wall subsonically, with the flux $p + \rho v_\mathrm{n} c_\mathrm{s}$ of normal momentum, an acoustic estimate of the pressure for $v_\mathrm{n}$ towards the wall. In faster flow mass and energy enter the domain.

Detail: [Zingale 2.2.5](../references/computational-hydrodynamics-synthesis.md#225-boundary-conditions-and-ghost-cells), [Zingale 2.5.15](../references/computational-hydrodynamics-synthesis.md#2515-boundary-conditions), [pyro 2.1.3](../references/pyro-synthesis.md#213-boundary-conditions), [Ulula 2.2.2](../references/ulula-synthesis.md#222-boundary-conditions), [ZEUS 2.5.1](../references/zeus-synthesis.md#251-boundary-conditions), [Athena 3.3](../references/athena-synthesis.md#33-boundaries-and-their-communication).

### 2.3 Prescribed values, inflow and hydrostatic boundaries

pyro's Dirichlet and Neumann conditions prescribe a value $f_\mathrm{b}$ or a gradient $f'_\mathrm{b}$ on the boundary face through the first ghost cell, as the mean or the centred difference of the two cells beside it:

$$f_{\mathrm{lo}-1} = 2f_\mathrm{b} - f_\mathrm{lo}, \qquad f_{\mathrm{lo}-1} = f_\mathrm{lo} - \Delta x\,f'_\mathrm{b}.$$

An inflow boundary holds prescribed values of all variables in the ghost cells (Stone and Norman 1992a, §4.5), although the inflow state belongs on the face itself, as Zingale's text notes.

A stratified atmosphere needs a boundary that supplies the pressure holding it against gravity, while letting acoustic waves pass (Zingale's text; [Zingale et al.](#zingale-et-al-2002) 2002). pyro's hydrostatic boundary at the lower or upper edge in $y$, with the gravitational acceleration $g$ along $y$, runs as follows.

1. Copy the density, the momenta and the other variables of the edge zone into the ghost cells.
2. Integrate the pressure outwards with the density of the edge zone, so that it changes by $\rho\,g\,\Delta y$ from one ghost cell to the next.
3. Set the total energy of each ghost cell from its pressure and the kinetic energy of the edge zone.

Athena++ leaves such boundaries to problems such as its Rayleigh–Taylor instability, which extrapolates the pressure hydrostatically, and Ulula holds its atmospheres between walls. **[GK]** Step 2 differences hydrostatic balance, $\partial p/\partial y = \rho g$, as $p_{\mathrm{lo}-1-k} = p_{\mathrm{lo}-k} - \rho_\mathrm{lo}\,g\,\Delta y$ below the domain. Outflow would copy the pressure instead, and a wall mirror it, which leaves the edge zone without the full gradient that carries its weight.

Detail: [Zingale 2.5.15](../references/computational-hydrodynamics-synthesis.md#2515-boundary-conditions), [pyro 2.1.3](../references/pyro-synthesis.md#213-boundary-conditions), [pyro 2.4.6](../references/pyro-synthesis.md#246-boundary-conditions-and-time-step), [pyro 2.6.2](../references/pyro-synthesis.md#262-boundary-conditions), [Ulula 2.8.6](../references/ulula-synthesis.md#286-the-atmosphere), [ZEUS 2.5.1](../references/zeus-synthesis.md#251-boundary-conditions), [Athena 2.16.5](../references/athena-synthesis.md#2165-hydrodynamics-in-two-and-three-dimensions).

### 2.4 Open boundaries and characteristics

An open boundary should let waves leave without reflection. Zero-gradient outflow is exact for supersonic outflow, where every wave leaves the domain, but in subsonic outflow some waves still enter, and the boundary reflects spuriously (Zingale's text; Stone and Norman 1992a). Prescribed inflow is likewise exact only when supersonic. ZEUS calls for a larger domain where the reflections matter, or for extrapolation along the characteristics (Thompson 1987). It gives its angular velocity and toroidal field zero gradient along the incoming characteristic at outflow boundaries, so that outgoing torsional Alfvén waves leave freely ([Stone and Norman](#stone-norman-1992b) 1992b, §3.4; [Vanajakshi, Thompson and Black](#vanajakshi-et-al-1989) 1989).

A boundary takes one condition for every characteristic that enters the domain through it, none at a supersonic outflow and one at a subsonic outflow of the Euler equations, so that copying or prescribing the whole state fits only supersonic flow ([Poinsot and Lele](#poinsot-lele-1992) 1992, Table I). Characteristic conditions, which prescribe the incoming waves and take the outgoing ones from the interior, absorbing layers and characteristic conditions set through ghost cells follow in topic 5.

Detail: [Zingale 2.5.15](../references/computational-hydrodynamics-synthesis.md#2515-boundary-conditions), [ZEUS 2.5.1](../references/zeus-synthesis.md#251-boundary-conditions), [ZEUS 2.8.8](../references/zeus-synthesis.md#288-boundary-conditions-and-the-time-step), [Non-reflecting boundaries 2.1.4](../references/non-reflecting-boundaries-synthesis.md#214-physical-and-soft-conditions).

### 2.5 The magnetic field at boundaries

Constrained transport keeps the field free of divergence if the initial field is, and if the boundaries introduce no monopoles (Stone and Norman 1992b, §3.4; topic 11). As conditions on the field that keep it so are hard to construct, ZEUS sets the electromotive force $\mathbf{v}\times\mathbf{B}$ in the ghost zones instead, and evolves their field with the difference equations of the active zones. Its component $v_xB_y - v_yB_x$, which evolves the field in the plane of the grid, follows from the conditions on velocity and field, so that reflection reverses it and outflow copies it. The toroidal components take the hydrodynamic conditions, except at outflow (2.4). A plane of symmetry, such as an equator, reflects the velocity and the tangential field, continues the normal field and reverses the toroidal field. **[GK]** The electromotive force then keeps its sign.

Athena++ sets the field on the faces of the ghost cells directly: outflow copies the normal component on the boundary face and the tangential components of the last active cell, and reflection mirrors the normal component about the boundary face with a change of sign. Faces shared by two blocks of one level stay with each, and the blocks average the electromotive forces on shared edges.

**[GK]** The divergence of the active cells keeps its initial value whatever the ghost cells hold, as long as every face of these cells is updated by constrained transport from single-valued electromotive forces. ZEUS ensures this by evolving the ghost field as well, Athena++ by counting the boundary faces among the active ones and averaging the shared edges.

Detail: [ZEUS 2.8.4](../references/zeus-synthesis.md#284-constrained-transport), [ZEUS 2.8.8](../references/zeus-synthesis.md#288-boundary-conditions-and-the-time-step), [Athena 3.3](../references/athena-synthesis.md#33-boundaries-and-their-communication).

### 2.6 Boundaries between blocks and across poles

A domain decomposed into blocks gives every block a border of ghost cells, which the neighbouring blocks fill wherever no physical condition applies (Zingale's text, fig. 3.3). In Athena++ the ghost cells beside each face, edge and corner of a block come from the neighbour there, up to 26 in three dimensions ([Stone et al.](#stone-et-al-2020) 2020), and 56 with refinement. Periodic and polar boundaries are exchanges as well. A stage runs as follows.

1. Load for each neighbour the cells that its ghost cells overlap, restricted for a coarser neighbour and with the cells that prolongation needs for a finer one (topic 40).
2. Copy the buffer to a neighbour on the same process or send it to another, and receive those of the neighbours while other tasks run (topic 42).
3. Unpack the conserved variables into the ghost cells, prolong where a neighbour is coarser, and convert to primitive variables.
4. Apply the physical conditions to the primitive variables and the field, face by face in the order $x$, $y$, $z$.
5. Recompute the conserved variables, and the field at the centres, in the ghost cells that the conditions set.

Across a pole of spherical-polar coordinates, the ghost cells take the cells beyond the pole at the azimuth $\phi + \pi$, in reversed order along the polar angle $\theta$, with $v_\theta$, $v_\phi$, $B_\theta$ and $B_\phi$ reversed, which requires a periodic azimuth with an even number of cells. **[GK]** The point at the polar angle $-\theta$ and the azimuth $\phi$ is the point at $\theta$ and $\phi + \pi$, where the unit vectors $\hat{\boldsymbol{\theta}}$ and $\hat{\boldsymbol{\phi}}$ point the other way.

Detail: [Zingale 2.2.6](../references/computational-hydrodynamics-synthesis.md#226-beyond-the-uniform-grid), [Athena 2.8.1](../references/athena-synthesis.md#281-grids-and-geometry), [Athena 3.2](../references/athena-synthesis.md#32-arrays-the-mesh-and-its-blocks), [Athena 3.3](../references/athena-synthesis.md#33-boundaries-and-their-communication), [Athena 3.5](../references/athena-synthesis.md#35-task-lists-and-parallelisation).

## 3. Tests

pyro's unit tests fill two ghost cells by the outflow, periodic and reflecting conditions and compare them with the values expected, which checks the indexing of the conditions apart from any solver.

A field loop carried across the pole tests the coordinate singularity and the polar boundary of Athena++ (Stone et al. 2020, §3.5.2). A uniform flow, perpendicular to the polar axis of a spherical-polar mesh, carries a weak loop of field through the pole, where the ghost cells take their data from the opposite azimuth and the cells become highly anisotropic.

Detail: [pyro 2.1.3](../references/pyro-synthesis.md#213-boundary-conditions), [Athena 2.8.7](../references/athena-synthesis.md#287-tests-in-curvilinear-coordinates).

## 4. Assessment

Stone et al. (2020) find that the loop diffuses, most at its centre, but keeps its structure through the pole. Stone and Norman (1992b) find the largest errors of a steady magnetised wind next to the boundaries, and ascribe them to ghost zones held at the analytic values while the active zones relax to a solution of the difference equations. [Diemer](#diemer-2025) (2025) ascribes the slow settling of an atmosphere in Ulula partly to its walls. **[GK]** The standard conditions are exact only where they match the physics: periodic boundaries for periodic problems, reflection at walls and planes of symmetry, and copying or prescribing the state where the flow crosses the boundary supersonically. Subsonic open boundaries are the weak point of all five references. A ghost value must be one that the discrete solution can hold, and in a gravitational field one that balances the discrete gravity, or the boundary launches waves of its own. Ghost cells cost memory and communication in proportion to the surface of a block: with $n_\mathrm{g} = 2$, a block of $16^3$ cells has nearly as many ghost cells as active ones. Open is how a hydrostatic boundary is differenced to stay in balance with the source terms of topic 13, while the reflection of zero-gradient outflow in the production runs and characteristic conditions in MHD pass to topic 5.

## 5. Sources

- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="poinsot-lele-1992"></a>Poinsot, T. J. and Lele, S. K., Boundary conditions for direct simulations of compressible viscous flows, Journal of Computational Physics 101, 104–129 (1992), [doi:10.1016/0021-9991(92)90046-2](https://doi.org/10.1016/0021-9991%2892%2990046-2).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="thompson-1987"></a>Thompson, K. W., Time dependent boundary conditions for hyperbolic systems, Journal of Computational Physics 68, 1–24 (1987), [doi:10.1016/0021-9991(87)90041-6](https://doi.org/10.1016/0021-9991%2887%2990041-6).
- <a id="vanajakshi-et-al-1989"></a>Vanajakshi, T. C., Thompson, K. W. and Black, D. C., Boundary value problems in magnetohydrodynamics (and fluid dynamics). I. Radiation boundary condition, Journal of Computational Physics 84, 343–359 (1989), [doi:10.1016/0021-9991(89)90237-4](https://doi.org/10.1016/0021-9991%2889%2990237-4).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).
- <a id="zingale-et-al-2002"></a>Zingale, M., Dursi, L. J., ZuHone, J., Calder, A. C., Fryxell, B., Plewa, T., Truran, J. W., Caceres, A., Olson, K., Ricker, P. M., Riley, K., Rosner, R., Siegel, A., Timmes, F. X. and Vladimirova, N., Mapping initial hydrostatic models in Godunov codes, ApJS 143, 539–565 (2002), [doi:10.1086/342754](https://doi.org/10.1086/342754).

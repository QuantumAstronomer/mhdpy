# Relativistic MHD

## 1. Overview

Flows near black holes, in gamma-ray bursts and in the jets of blazars move close to the speed of light or in strong gravity, and need the equations of special or general relativity. Their Godunov schemes keep the structure of the Newtonian ones, with conservative updates, Riemann solvers and CT, but the conserved variables no longer give the primitive ones in closed form, and errors can produce states without a physical counterpart. Athena couples an unsplit integrator, CT and relativistic HLL solvers with a hierarchy of corrections for such states ([Beckwith and Stone](#beckwith-stone-2011) 2011). Athena++ extends this to any stationary spacetime and brings the solvers of special relativity into general relativity by local transformations of frame ([White, Stone and Gammie](#white-et-al-2016) 2016; [Stone et al.](#stone-et-al-2020) 2020, §4). No other reference treats relativity. The Newtonian Riemann solvers follow in topic 7, CT in topic 11 and curvilinear coordinates in topic 12.

## 2. Methods

### 2.1 The equations

With $c = 1$, fields in Lorentz–Heaviside form, the comoving density $\rho$, the four-velocity $u^\mu$ and the stress-energy tensor $T^{\mu\nu}$, the equations conserve particle number, $\nabla_\mu(\rho u^\mu) = 0$, energy and momentum, $\nabla_\mu T^{\mu\nu} = 0$, and the dual of the electromagnetic tensor, which in ideal MHD reduces to the induction equation and $\nabla\cdot\mathbf{B} = 0$. With the magnetic four-vector $b^\mu$, the enthalpy $h = 1 + [\gamma/(\gamma - 1)]p/\rho$ of an ideal gas and the Lorentz factor $\Gamma$, the stress-energy tensor is $T^{\mu\nu} = (\rho h + b_\lambda b^\lambda)u^\mu u^\nu + (p + \tfrac{1}{2}b_\lambda b^\lambda)g^{\mu\nu} - b^\mu b^\nu$. In special relativity the equations read (Stone et al. 2020, eqs. 31 to 33)

$$\partial_tD + \nabla\cdot(D\mathbf{v}) = 0, \qquad \partial_t\mathbf{m} + \nabla\cdot\mathsf{M} = 0, \qquad \partial_tE + \nabla\cdot\mathbf{m} = 0, \qquad \partial_t\mathbf{B} - \nabla\times(\mathbf{v}\times\mathbf{B}) = 0,$$

with the density $D = \Gamma\rho$, the momentum $\mathbf{m}$, the total energy $E$ and the momentum flux $\mathsf{M}$ of the lab frame. In general relativity they take the flux-conservative form $\partial_t(\sqrt{-g}\,T^0{}_\mu) + \partial_j(\sqrt{-g}\,T^j{}_\mu) = \tfrac{1}{2}\sqrt{-g}\,(\partial_\mu g_{\alpha\beta})\,T^{\alpha\beta}$, and alike for particle number and field without source terms, where $g$ is the determinant of the metric (eqs. 40 to 42). With the lower index, the source vanishes for every coordinate on which the metric does not depend, so that a stationary metric never gives a source of energy. Athena++ precomputes the metric and the geometric factors, which include $\sqrt{-g}$, for Minkowski, Schwarzschild, Kerr–Schild or a metric of the user. The step lets light cross a fraction of a cell.

Detail: [Athena 2.14.1](../references/athena-synthesis.md#2141-the-equations-of-relativistic-mhd), [Athena 2.14.5](../references/athena-synthesis.md#2145-general-relativity).

### 2.2 Primitive variables

No algebraic expression gives the primitive variables, so that every cell solves for them iteratively in every stage (Beckwith and Stone 2011, §3.1). Athena finds by Newton–Raphson the root in $Q = \rho h\Gamma^2$ of the definition of the energy, the method 1DW of [Noble et al.](#noble-et-al-2006) (2006). Athena++ adopted the root-find in one dimension of [Newman and Hamlin](#newman-hamlin-2014) (2014), which finds a solution whenever one exists and proved more robust.

1. Raise $D$ and $E$ to their floors and limit $|\mathbf{m}|^2$ to $(1 - 10^{-12})E^2$.
2. From the pressure of the previous iterate, find the velocity, in MHD from a root of a cubic, then the enthalpy, $\rho = D/\Gamma$ and a new pressure, extrapolating by Aitken's method every third iterate.
3. Stop at a change below $10^{-12}$, or fail after 15 iterates.
4. Where density or pressure fall below their floors, raised in MHD by ceilings on the magnetisation and on the inverse plasma beta, add the deficit to $D$ and $E$ and repeat; limit the Lorentz factor, and give a cell that fails the floors at rest.

Athena++ takes as primitive velocity the spatial part of the four-velocity, in the normal frame in general relativity, since any finite real values then give a unique subluminal state, which the three-velocity would not. It reconstructs primitive variables only, which avoids the cost of a characteristic decomposition and its risk of failed inversions. Athena limits PLM in the primitive variables with the four-velocity as well and falls back to first order where a face state would still move faster than light.

Detail: [Athena 2.14.2](../references/athena-synthesis.md#2142-primitive-variables-reconstruction-and-corrections), [Athena 2.14.3](../references/athena-synthesis.md#2143-the-relativistic-equations-of-state-in-the-code).

### 2.3 The hierarchy of corrections

A conserved state without a physical primitive one arises from non-real fluxes of the Riemann solver, an inversion that does not converge, a negative density or pressure, or a superluminal velocity (Beckwith and Stone 2011, §3.4). Athena corrects these in turn.

1. Replace non-real fluxes of HLLC or HLLD by those of HLLE, which are real for any physical states.
2. Update a failed cell, and its neighbours on the shared faces and edges, with the first-order fluxes and electric fields of the predictor, which keeps conservation and the divergence constraint.
3. Where the inversion still fails, evolve the entropy in place of the energy, which keeps the pressure positive at the expense of conservation of energy.
4. Where even that fails, set density and pressure to floors and the velocity just below that of light.

In the most demanding run, a jet at high resolution with HLLD, the three corrections after the first were needed about once in $10^9$, $10^{10}$ and $10^{11}$ updates, and no test needed one. Athena++ relies on its floors and ceilings and was exploring the first-order correction.

Detail: [Athena 2.14.2](../references/athena-synthesis.md#2142-primitive-variables-reconstruction-and-corrections).

### 2.4 Riemann solvers and frames

The HLL solvers need the outermost speeds of the Riemann fan, the fast speeds, which Athena takes from the roots of a quartic, found numerically, as the extremes over both states; these make the code much more robust than quadratic approximations (Beckwith and Stone 2011, §3.3). HLLE diffuses contact and rotational discontinuities even at rest. The HLLC of [Mignone and Bodo](#mignone-bodo-2006) (2006) restores the contact, but treats vanishing and non-vanishing normal fields apart and is singular as the normal field vanishes in truly three-dimensional flows. The HLLD of [Mignone, Ugliano and Bodo](#mignone-et-al-2009) (2009) restores the rotational discontinuities as well, where relativistic aberration allows the normal velocity to jump across the intermediate states, at the price of a root-find by the secant method for the total pressure at the contact. Athena++ offers LLF and HLLE for hydrodynamics and MHD, HLLC for hydrodynamics and HLLD for MHD.

In general relativity, Athena++ solves the Riemann problem in a locally Minkowski frame rather than in the coordinates (White, Stone and Gammie 2016, §3.3).

1. Build at the face an orthonormal basis whose time vector is the unit normal to the surfaces of constant time and whose two transverse vectors lie within the face, so that the solver need return no transverse fluxes.
2. Transform the vectors of both states to this basis, leaving density and pressure as they are.
3. Solve the Riemann problem of special relativity with the face moving at the velocity that the shift gives it.
4. Transform the fluxes back to the coordinates.

As the normal observer exists everywhere, this works inside the ergosphere and, in coordinates that penetrate the horizon, inside the horizon, but it may fail where the coordinates are singular, so that faces on a polar axis fall back to HLLE in the coordinates. CT, extended to arbitrary stationary coordinates after Gardiner and Stone (topic 11), keeps the field free of divergence.

Detail: [Athena 2.14.4](../references/athena-synthesis.md#2144-relativistic-riemann-solvers), [Athena 2.14.5](../references/athena-synthesis.md#2145-general-relativity).

## 3. Tests

Beckwith and Stone (2011) test special relativity in several dimensions with HLLD. A circularly polarised Alfvén wave, an exact solution whose speed relativity changes, travels obliquely to the grid. A field loop advected across the grid tests both CT and the inversion, whose tolerance can drive the out-of-plane field through errors of the velocity. Current sheets that reconnect at the grid scale, in strongly magnetised gas, and the vortex of Orszag and Tang test robustness, and shock tubes rotated obliquely to a three-dimensional grid test the divergence.

The cylindrical blast wave of [Komissarov](#komissarov-1999) (1999), in the milder version that later studies use, runs without artificial viscosity or resistivity. The relativistic Kelvin–Helmholtz instability, with a Lorentz factor of 2.29 between two shear flows, compares the solvers on three grids and, in three dimensions, the amplification of the field by turbulence. A jet with a Lorentz factor of 7 into a magnetised medium compares HLLC and HLLD in the field of its cocoon.

White, Stone and Gammie (2016) test general relativity. Linear waves of hydrodynamics and MHD, also in coordinates tilted against those of Minkowski, so that the interfaces move, measure convergence and the gain of the better solvers. The seven shock tubes of Komissarov run on 220 cells, a blast wave runs in coordinates curved like a snake, and Bondi accretion onto a black hole of Schwarzschild and the plunging region of a thin disc around a spinning black hole test curved spacetimes. Tori around spinning black holes, seeded with weak fields, demonstrate the magnetorotational instability.

Stone et al. (2020) run a strong shock tube, a magnetised Kelvin–Helmholtz problem and a strongly magnetised blast with adaptive refinement. The regression tests of Athena++ require linear waves of special relativity to converge at an order of 1.8 or better, and run the shock tubes in general relativity with Minkowski coordinates against the reference data of special relativity.

Detail: [Athena 2.14.6](../references/athena-synthesis.md#2146-tests-of-special-relativistic-mhd), [Athena 2.14.7](../references/athena-synthesis.md#2147-tests-of-general-relativistic-mhd), [Athena 2.14.8](../references/athena-synthesis.md#2148-applications-of-relativistic-mhd).

## 4. Assessment

The current sheets run robustly to a plasma beta of about $10^{-3}$ with HLLE, $10^{-2}$ with HLLC and $10^{-1}$ with HLLD, while a stronger shear flow breaks every solver below a beta of one, and the oblique shock tubes show no spurious normal fields (Beckwith and Stone 2011). HLLE converges to a wrong linear phase of the Kelvin–Helmholtz instability at resolutions where HLLC and HLLD converge, and in the jet HLLD yields fields in the cocoon about ten times stronger and three to four times the effective resolution of the field, gains that far outweigh its cost. In general relativity the linear waves and the plunging region converge at second order, in tilted coordinates HLLC and HLLD beat HLLE by factors of up to 4.8 in the error of the entropy wave, and the shock tubes agree with reference solutions on ten times as many cells, with some artefacts that Komissarov saw as well (White, Stone and Gammie 2016). Adaptive refinement reproduces the uniform blast to 1 per cent over most of the volume at a quarter of the cost (Stone et al. 2020). **[GK]** The inversion dominates both the cost and the fragility of relativistic schemes: it iterates in every cell and stage, vectorises poorly in NumPy where cells converge after different numbers of iterates, and fails where truncation errors leave no physical state, so that floors and ceilings decide the results in magnetised, low-density regions. The local frames reuse the solvers of special relativity at little cost in code, which suits the extensibility of mhdpy. Relativity lies far from the production runs but within the eventual scope. Open are whether the layers of the framework keep the conversion between conserved and primitive variables general enough for an iterative inversion, and whether the velocity variable and the floors become part of the equation of state.

## 5. Sources

- <a id="beckwith-stone-2011"></a>Beckwith, K. and Stone, J. M., A second-order Godunov method for multi-dimensional relativistic magnetohydrodynamics, ApJS 193, 6 (2011), [arXiv:1101.3573](https://arxiv.org/abs/1101.3573), [doi:10.1088/0067-0049/193/1/6](https://doi.org/10.1088/0067-0049/193/1/6).
- <a id="komissarov-1999"></a>Komissarov, S. S., A Godunov-type scheme for relativistic magnetohydrodynamics, MNRAS 303, 343–366 (1999), [doi:10.1046/j.1365-8711.1999.02244.x](https://doi.org/10.1046/j.1365-8711.1999.02244.x).
- <a id="mignone-bodo-2006"></a>Mignone, A. and Bodo, G., An HLLC Riemann solver for relativistic flows – II. Magnetohydrodynamics, MNRAS 368, 1040–1054 (2006), [doi:10.1111/j.1365-2966.2006.10162.x](https://doi.org/10.1111/j.1365-2966.2006.10162.x).
- <a id="mignone-et-al-2009"></a>Mignone, A., Ugliano, M. and Bodo, G., A five-wave Harten–Lax–van Leer Riemann solver for relativistic magnetohydrodynamics, MNRAS 393, 1141–1156 (2009), [doi:10.1111/j.1365-2966.2008.14221.x](https://doi.org/10.1111/j.1365-2966.2008.14221.x).
- <a id="newman-hamlin-2014"></a>Newman, W. I. and Hamlin, N. D., Primitive variable determination in conservative relativistic magnetohydrodynamic simulations, SIAM Journal on Scientific Computing 36, B661–B683 (2014), [doi:10.1137/140956749](https://doi.org/10.1137/140956749).
- <a id="noble-et-al-2006"></a>Noble, S. C., Gammie, C. F., McKinney, J. C. and Del Zanna, L., Primitive variable solvers for conservative general relativistic magnetohydrodynamics, ApJ 641, 626–637 (2006), [doi:10.1086/500349](https://doi.org/10.1086/500349).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="white-et-al-2016"></a>White, C. J., Stone, J. M. and Gammie, C. F., An extension of the Athena++ code framework for GRMHD based on advanced Riemann solvers and staggered-mesh constrained transport, ApJS 225, 22 (2016), [arXiv:1511.00943](https://arxiv.org/abs/1511.00943), [doi:10.3847/0067-0049/225/2/22](https://doi.org/10.3847/0067-0049/225/2/22).

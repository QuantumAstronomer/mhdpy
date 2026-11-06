# Constrained transport

## 1. Overview

The magnetic field must stay free of divergence. Where $\nabla\cdot\mathbf{B} \ne 0$, the Lorentz force gains a component along the field ([Brackbill and Barnes](#brackbill-barnes-1980) 1980) and, as [Tóth](#toth-2000) (2000) showed, MHD shocks acquire wrong jump conditions, and errors in the evolved components violate the constraint unless the scheme builds it in. Three approaches are in use: cleaning the field by a projection after each step, adding an equation for the divergence that keeps its errors from accumulating in one place, as the eight-wave and GLM schemes do, and constrained transport (CT), which evolves the magnetic flux through the faces of the cells conservatively and so keeps the discrete divergence at round-off ([Evans and Hawley](#evans-hawley-1988) 1988). ZEUS and Athena use CT, ZEUS with electromotive forces from the method of characteristics and Athena with electric fields from the Godunov fluxes, upwinded at the cell corners after [Gardiner and Stone](#gardiner-stone-2005) (2005), which Athena++ keeps. Projection and divergence cleaning are only named. The boundaries of the field follow in topic 4, the Riemann solvers of MHD in topic 7, the integrators in topic 8 and CT of fourth order in topic 9.

## 2. Methods

### 2.1 The staggered field

Before CT, codes evolved the vector potential, $\mathbf{B} = \nabla\times\mathbf{A}$, for which a consistent discrete curl and divergence keep $\nabla\cdot\mathbf{B} = 0$ exactly. The Lorentz force then needs second derivatives of $\mathbf{A}$, and even with schemes of higher order the current reverses anomalously near shocks and sharp features of the field, which heats and accelerates the flow spuriously ([Stone and Norman](#stone-norman-1992b) 1992b, §3). CT evolves the field itself on a staggered mesh, so that no second derivatives arise and the current comes out smooth. Each component sits on the faces normal to it, as an average over the face, $B_{x,i-1/2,j,k}$, $B_{y,i,j-1/2,k}$ and $B_{z,i,j,k-1/2}$, and the electric field

$$\boldsymbol{\mathcal{E}} = -\mathbf{v}\times\mathbf{B}, \qquad \frac{\partial\mathbf{B}}{\partial t} + \nabla\times\boldsymbol{\mathcal{E}} = 0,$$

sits on the edges, each component averaged along its edge and over the step. ZEUS writes the electromotive force $\mathbf{v}\times\mathbf{B} = -\boldsymbol{\mathcal{E}}$. The momentum and energy need the field at the cell centres, which Athena takes as the mean of the two face values along each direction and Athena++ as their linear interpolation to the volume centre on nonuniform grids. The staggering reflects that MHD conserves the magnetic flux, an average over areas ([Gardiner and Stone](#gardiner-stone-2005) 2005).

Detail: [ZEUS 2.8.2](../references/zeus-synthesis.md#282-the-divergence-constraint-and-the-wave-families), [ZEUS 2.8.3](../references/zeus-synthesis.md#283-the-centring-of-the-field), [Athena 2.3.1](../references/athena-synthesis.md#231-keeping-the-field-free-of-divergence), [Athena 2.3.4](../references/athena-synthesis.md#234-the-field-in-the-code).

### 2.2 The update by the theorem of Stokes

Integrating the induction equation over a face and applying the theorem of Stokes changes the magnetic flux through the face by the circulation of $\boldsymbol{\mathcal{E}}$ around its edges ([Stone et al.](#stone-et-al-2008) 2008, eqs. 16 to 18):

$$B^{n+1}_{x,i-1/2,j,k} = B^n_{x,i-1/2,j,k} - \frac{\Delta t}{\Delta y}\left(\mathcal{E}_{z,i-1/2,j+1/2,k} - \mathcal{E}_{z,i-1/2,j-1/2,k}\right) + \frac{\Delta t}{\Delta z}\left(\mathcal{E}_{y,i-1/2,j,k+1/2} - \mathcal{E}_{y,i-1/2,j,k-1/2}\right),$$

and alike for $B_y$ and $B_z$ by cyclic permutation. Like the finite-volume update, it is exact, and a method lies in how it approximates $\boldsymbol{\mathcal{E}}$. Each edge enters the two faces it bounds once each with opposite signs, so that the change of the total flux through the surface of a cell vanishes: a cell without magnetic charge at $t^n$ has none at $t^{n+1}$, and the total flux through the domain is conserved to round-off. CT preserves the constraint but cannot create it, so that the initial field is best set from a vector potential, and the boundaries must introduce no monopoles (topic 4). On curvilinear grids the update uses the areas of the faces and the lengths of the edges, which ZEUS takes from its scale factors and Athena++ from its coordinates. One step runs as follows.

1. Take the electric fields on the faces from the fluxes of the Riemann solver: on a face normal to $x$, $\mathcal{E}_z$ is minus the flux of $B_y$ and $\mathcal{E}_y$ the flux of $B_z$.
2. Integrate them to the edges (2.4).
3. Update the face fields by the circulation above.
4. Compute the field at the cell centres from the new face fields.

Detail: [ZEUS 2.8.4](../references/zeus-synthesis.md#284-constrained-transport), [Athena 2.3.2](../references/athena-synthesis.md#232-finite-areas-and-the-update-of-the-field), [Athena 2.3.4](../references/athena-synthesis.md#234-the-field-in-the-code).

### 2.3 Consistency with the finite volumes

The finite-volume update also evolves the transverse components of the field at the cell centres, through the Godunov fluxes. Gardiner and Stone (2005, §2.3) require the cell-centred field to remain the mean of the face fields after the step, which fixes those fluxes in terms of the corner fields:

$$\mathbf{F}_y(B_x)_{i,j+1/2} = \tfrac{1}{2}\left(\mathcal{E}_{z,i-1/2,j+1/2} + \mathcal{E}_{z,i+1/2,j+1/2}\right), \qquad \mathbf{F}_x(B_y)_{i+1/2,j} = -\tfrac{1}{2}\left(\mathcal{E}_{z,i+1/2,j-1/2} + \mathcal{E}_{z,i+1/2,j+1/2}\right).$$

In effect the fluxes of the field from the Riemann solver serve only as predictors, which the corner fields correct. The algorithm for the corner fields thus decides the accuracy and the stability of the whole scheme. Splitting by direction cannot keep the constraint between its sweeps, as an update along $x$ keeps $B_x$ fixed, so that CT needs an unsplit integrator, CTU or VL2 (topic 8).

Detail: [Athena 2.3.3](../references/athena-synthesis.md#233-consistency-of-finite-volumes-and-ct), [Athena 2.6.3](../references/athena-synthesis.md#263-ctu-in-two-dimensions).

### 2.4 The electric fields at the corners

An algorithm for the corner fields should reduce to the one-dimensional integrator for plane-parallel flows aligned with the grid, where symmetry makes the corner value the mean of the two face values beside it, and it should use only the electric field that a Riemann flux contains, so that any solver serves (Gardiner and Stone 2005, §3.2). The plain average of the four face values fails this test: it halves the numerical viscosity of the solver, as it has no directional bias. Integrating instead from each face to the corner with a gradient, and averaging the four results, gives (their eq. 42)

$$\mathcal{E}_{z,i+1/2,j+1/2} = \bar{\mathcal{E}}_z + \frac{\Delta y}{8}\left[\left(\frac{\partial\mathcal{E}_z}{\partial y}\right)_{i+1/2,j+1/4} - \left(\frac{\partial\mathcal{E}_z}{\partial y}\right)_{i+1/2,j+3/4}\right] + \frac{\Delta x}{8}\left[\left(\frac{\partial\mathcal{E}_z}{\partial x}\right)_{i+1/4,j+1/2} - \left(\frac{\partial\mathcal{E}_z}{\partial x}\right)_{i+3/4,j+1/2}\right],$$

with $\bar{\mathcal{E}}_z$ the mean of the four face values. The gradients come from a face value and a reference value at the cell centre, $\mathcal{E}^\mathrm{r}_z = -(\mathbf{v}\times\mathbf{B})_z$ from the cell state, as $(\partial\mathcal{E}_z/\partial y)_{i,j+1/4} = 2(\mathcal{E}_{z,i,j+1/2} - \mathcal{E}^\mathrm{r}_{z,i,j})/\Delta y$. The algorithm $\mathcal{E}^\mathrm{c}$ upwinds each gradient on a face by the direction of the mass flux through it: the gradient of cell $i$ where $v_{x,i+1/2,j} > 0$, that of cell $i + 1$ where it is negative, and their mean where it vanishes. Upwinding with a Lax–Friedrichs flux instead, $\mathcal{E}^\alpha$, diffuses a field at rest, and the centred limit $\mathcal{E}^\circ$ oscillates under advection. Athena and Athena++ use $\mathcal{E}^\mathrm{c}$, the latter with a ramp, $w = \tfrac{1}{2} + \max\{-\tfrac{1}{2}, \min[\tfrac{1}{2},\ 1024\,\Delta t\,F_\rho/(\Delta x\,(\rho_\mathrm{L} + \rho_\mathrm{R}))]\}$ for the weight of the upwind side, from the mass flux $F_\rho$, which differs from the switch only where the flow crosses less than $1/1024$ of a cell in a step. The reference field is taken at $t^n$ for the first fluxes of a step and at the half step for the second. **[GK]** Stone et al. (2008, eq. 70) print both brackets with the wrong sign, which would double the error of the plain average; the code follows eq. 42.

Detail: [Athena 2.3.5](../references/athena-synthesis.md#235-the-electric-fields-at-the-corners).

### 2.5 Multidimensional terms in the interface states

In primitive variables the induction equation contains terms in $\partial B_x/\partial x$ and $\partial B_y/\partial y$ that a one-dimensional system lacks, and these can dominate, as for a weak field loop advected across the grid, where $v_x\,\partial B_y/\partial y$ alone evolves $B_x$ (Gardiner and Stone 2005, eqs. 25 to 33). Characteristic tracing along $x$ (topic 8) therefore carries the source $v_y\,\partial B_x/\partial x$ in the equation for $B_y$, evaluated from the face fields, while $B_x$ is taken from the faces without reconstruction, which keeps it continuous and free of limiting. The transverse updates of CTU add $\mathbf{B}\,\partial B_x/\partial x$ to the momentum and $B_zv_z\,\partial B_x/\partial x$ to the energy, and the term $v_z\,\partial B_x/\partial x$ for $B_z$ enters there rather than in the interface states, which keeps $B_z$ of a loop advected with $v_z \ne 0$ at round-off. In three dimensions two transverse terms compete, and [Gardiner and Stone](#gardiner-stone-2008) (2008, eqs. 21 to 26) limit them so that their balance holds, as $v_z\,\mathrm{minmod}(\partial B_x/\partial x, -\partial B_z/\partial z)$ in the equation for $B_z$ of a sweep along $x$, with the minmod of topic 6. **[GK]** The VL2 integrator of Athena++ needs no such terms, as its predictor is a full conservative update of first order without characteristic tracing.

Detail: [Athena 2.6.2](../references/athena-synthesis.md#262-a-first-order-unsplit-scheme-with-ct), [Athena 2.6.3](../references/athena-synthesis.md#263-ctu-in-two-dimensions), [Athena 2.6.4](../references/athena-synthesis.md#264-ctu-in-three-dimensions).

### 2.6 The method of characteristics in ZEUS

Hydrodynamic upwind schemes applied to the field give Alfvén waves a large dispersion error, with stable oscillations of short wavelength, and only schemes upwinded along the characteristics of these waves removed it (Stone and Norman 1992b, §3). ZEUS therefore forms its electromotive force at the zone corners, $\epsilon_z = v^{n+1/2}_xB^{n+1/2}_y - v^{n+1/2}_yB^{n+1/2}_x$, from values advanced by the method of characteristics for Alfvén waves alone, as the hydrodynamics carries the compressive waves. Along the characteristics $C^\pm$ of slope $v_\parallel \pm c_\mathrm{A}$, with $c_\mathrm{A} = |B_\parallel|/\sqrt{\rho}$ and $v_\parallel$, $B_\parallel$ the components along the direction of propagation, the transverse velocity $v$ and field $B$ obey (eqs. 16 to 19)

$$\left(v^{n+1/2} - v^+\right) - \frac{B^{n+1/2} - B^+}{\sqrt{\rho^+}} = 0, \qquad \left(v^{n+1/2} - v^-\right) + \frac{B^{n+1/2} - B^-}{\sqrt{\rho^-}} = 0,$$

where $v^\pm$ and $B^\pm$ are upwind averages over the domains of dependence of the two footpoints. The method runs in two sweeps.

1. Solve the pair for waves along $y$, with footpoints upwinded by $v_y \pm B_y/\sqrt{\rho}$, for $v_x$ and $B_x$ at every corner.
2. Solve the pair for waves along $x$ for $v_y$ and $B_y$.
3. Form $\epsilon_z$ and update the field by CT.

The Lorentz force is split: the gradients of the magnetic pressure act in the first substep of the source step, and the Alfvén terms with field values from a second solution of the pair in the frame of the fluid. The toroidal component needs no CT in two dimensions and follows a similar method for the angular velocity and the magnetic flux $h_3B_3$, with $h_3$ the scale factor of the third coordinate, and with consistent transport of $B_3/\rho$. **[GK]** The pair gives $B^{n+1/2} = [v^- - v^+ + B^+/\sqrt{\rho^+} + B^-/\sqrt{\rho^-}]/[(\rho^+)^{-1/2} + (\rho^-)^{-1/2}]$.

Detail: [ZEUS 2.8.5](../references/zeus-synthesis.md#285-the-electromotive-force-by-the-method-of-characteristics), [ZEUS 2.8.6](../references/zeus-synthesis.md#286-the-lorentz-force), [ZEUS 2.8.7](../references/zeus-synthesis.md#287-the-toroidal-field).

## 3. Tests

A weak loop of field, set from the vector potential $A_z = A_0(R - r)$ with $A_0 = 10^{-3}$ and $R = 0.3$, is advected diagonally across a periodic grid of $128 \times 64$ cells, at a plasma beta of $2 \times 10^6$, so that it should move unchanged (Gardiner and Stone 2005, §3.3.1). At rest it measures the diffusion of the corner fields, under advection their oscillations, and in three dimensions, as a cylinder advected with $v_z \ne 0$ or inclined to the grid, the balance of the terms of 2.5, which must keep the axial field at zero. Athena and Athena++ run it in two and three dimensions.

ZEUS advects a square pulse of transverse field, a double current sheet 50 zones wide, over five times its width, after Evans and Hawley (1988), with the van Leer method, PPA and PPA with steepening (Stone and Norman 1992b, §4.1). The pulse checks the advection by CT and the current at its edges, analytically a pair of delta functions.

Detail: [ZEUS 2.9.1](../references/zeus-synthesis.md#291-approach-and-advection-tests), [Athena 2.16.3](../references/athena-synthesis.md#2163-advection-of-a-field-loop).

## 4. Assessment

For the loop at rest, $\mathcal{E}^\alpha$ opens a hole at the centre while $\mathcal{E}^\circ$ and $\mathcal{E}^\mathrm{c}$ barely diffuse; under advection $\mathcal{E}^\circ$ develops oscillations that dominate by $t = 2$, and without the source terms of the interface states the loop breaks up within a fraction of an orbit (Gardiner and Stone 2005). With CTU the magnetic energy decays as $1 - (t/\tau)^\alpha$ with $\alpha \approx 0.3$. Athena keeps $B_z$ of the cylinder at round-off and that of the inclined loop at the truncation error, and Stone et al. (2008) find that $\mathcal{E}^\mathrm{c}$ balances accuracy and simplicity best. In ZEUS the pulse spreads over about 14 zones with the van Leer method and over 2 with steepened PPA, and its currents show no anomalous reversals. **[GK]** CT keeps the divergence at round-off at little cost per step and conserves the magnetic flux as finite volumes conserve mass, but it imposes a second, staggered representation of the field, which complicates the data structures, mesh refinement and the coupling to the cell-centred update. Its quality rests on the corner fields: $\mathcal{E}^\mathrm{c}$ is simple, robust and works with any Riemann solver, at second order. The method of characteristics of ZEUS predates this construction and is bound to its operator splitting. Open are how the face fields are laid out beside the cell data, whether VL2 with $\mathcal{E}^\mathrm{c}$ suffices for production runs or CTU repays its source terms, and whether divergence cleaning is worth offering for problems where staggering is impractical.

## 5. Sources

- <a id="brackbill-barnes-1980"></a>Brackbill, J. U. and Barnes, D. C., The effect of nonzero $\nabla \cdot \mathbf{B}$ on the numerical solution of the magnetohydrodynamic equations, Journal of Computational Physics 35, 426–430 (1980), [doi:10.1016/0021-9991(80)90079-0](https://doi.org/10.1016/0021-9991%2880%2990079-0).
- <a id="evans-hawley-1988"></a>Evans, C. R. and Hawley, J. F., Simulation of magnetohydrodynamic flows: a constrained transport method, ApJ 332, 659–677 (1988), [doi:10.1086/166684](https://doi.org/10.1086/166684).
- <a id="gardiner-stone-2005"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport, Journal of Computational Physics 205, 509–539 (2005), [arXiv:astro-ph/0501557](https://arxiv.org/abs/astro-ph/0501557), [doi:10.1016/j.jcp.2004.11.016](https://doi.org/10.1016/j.jcp.2004.11.016).
- <a id="gardiner-stone-2008"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport in three dimensions, Journal of Computational Physics 227, 4123–4141 (2008), [arXiv:0712.2634](https://arxiv.org/abs/0712.2634), [doi:10.1016/j.jcp.2007.12.017](https://doi.org/10.1016/j.jcp.2007.12.017).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="toth-2000"></a>Tóth, G., The $\nabla \cdot \mathbf{B} = 0$ constraint in shock-capturing magnetohydrodynamics codes, Journal of Computational Physics 161, 605–652 (2000), [doi:10.1006/jcph.2000.6519](https://doi.org/10.1006/jcph.2000.6519).

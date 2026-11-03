# Methods of higher order

## 1. Overview

Methods of second order, the subject of topics 5 to 7, treat a cell average as the value at the centre and a face average as the value at the middle of the face. Beyond second order this midpoint approximation fails, so that averages and point values must be told apart, fluxes integrated over faces by quadrature, and the integrator in time raised to the order in space. The references follow two routes. Finite volumes of fourth order, after [McCorquodale and Colella](#mccorquodale-colella-2011) (2011), keep cell averages and correct the fluxes with Laplacians, in pyro for advection and hydrodynamics and in Athena++ for hydrodynamics on uniform Cartesian meshes. Conservative finite differences with WENO and flux splitting reconstruct the fluxes from point values, in Zingale's text and pyro. [Felker and Stone](#felker-stone-2018) (2018) extend the fourth order to MHD with an upwind constrained transport, which the copy of Athena++ does not yet contain. The integrators of fourth order, Runge–Kutta and spectral deferred corrections, are those of topic 7. Discontinuous Galerkin methods are only named.

## 2. Methods

### 2.1 Averages, point values and quadrature

A Taylor expansion about the centre of a cell, whose odd terms cancel in the average, relates the average $\langle Q\rangle$ to the value $Q$ at the centre to fourth order ([Felker and Stone](#felker-stone-2018) 2018, eqs. 3 and 4):

$$\langle Q\rangle_{i,j} = Q_{i,j} + \frac{\Delta x^2}{24}\,\nabla^2 Q_{i,j}, \qquad Q_{i,j} = \langle Q\rangle_{i,j} - \frac{\Delta x^2}{24}\,\nabla^2\langle Q\rangle_{i,j},$$

with the five-point Laplacian $\nabla^2$ on square cells of width $\Delta x$, and alike on a face with the Laplacian transverse to its normal, $\nabla^2_\perp$. Here, unlike in topic 5, angle brackets mark averages and plain symbols point values. Products of averages equal averages of products only to second order, so that every nonlinear operation, such as the conversion to primitive variables or the evaluation of a flux, needs a correction. Quadrature integrates a function from point values: the trapezoid rule converges at second order and Simpson's rule, with the weights $\tfrac{1}{6}(1, 4, 1)$ on a pair of intervals, at fourth ([Zingale's text](#zingale-2025), eqs. 1.10 to 1.13). **[GK]** A Gauss rule of $n$ points, at the zeros of a Legendre polynomial, is exact for polynomials of degree up to $2n - 1$.

Detail: [Zingale 2.1.4](../references/computational-hydrodynamics-synthesis.md#214-integration), [pyro 2.1.9](../references/pyro-synthesis.md#219-averages-and-centres), [Athena 2.7.1](../references/athena-synthesis.md#271-finite-volumes-of-fourth-order).

### 2.2 Finite volumes of fourth order

The method of McCorquodale and Colella (2011) evaluates the quadratures with finite differences, so that each face needs two Riemann solutions instead of the several points of a Gauss rule. A stage of the method of lines runs as follows (Felker and Stone 2018, eqs. 7 to 18).

1. Convert the averages of the conserved variables to centre values, $\mathbf{U}_{i,j} = \langle\mathbf{U}\rangle_{i,j} - (\Delta x^2/24)\nabla^2\langle\mathbf{U}\rangle_{i,j}$.
2. Form the fourth-order averages of the primitive variables, $\langle\mathbf{W}\rangle = \mathbf{W}(\mathbf{U}) + (\Delta x^2/24)\nabla^2\mathbf{W}(\langle\mathbf{U}\rangle)$, from the pointwise conversion and the conversion of the averages, with floors on density and pressure.
3. Reconstruct the face averages with the stencil $\tfrac{7}{12}(\langle\mathbf{W}\rangle_{i-1} + \langle\mathbf{W}\rangle_i) - \tfrac{1}{12}(\langle\mathbf{W}\rangle_{i-2} + \langle\mathbf{W}\rangle_{i+1})$ and a limiter of PPM that preserves smooth extrema (topic 5).
4. Convert the face averages to values at the face centres with $\nabla^2_\perp$, and solve the Riemann problem there for the pointwise flux $\mathbf{F}_\mathrm{c}$.
5. Solve a second Riemann problem between the face averages, and correct the pointwise flux to a face average, $\langle\mathbf{F}\rangle = \mathbf{F}_\mathrm{c} + (\Delta x^2/24)\nabla^2_\perp\mathbf{F}(\langle\mathbf{W}\rangle)$.
6. Update the averages by the divergence of the face-averaged fluxes, with a Runge–Kutta method of fourth order.

Athena++ selects the method with `xorder` 4 and RK4 or the five-stage SSPRK(5,4), with four ghost cells, on uniform Cartesian meshes without refinement, and turns the centre values of an initial condition into averages on request. pyro uses RK4, the limiter of McCorquodale and Colella (2011, eqs. 24 to 32) and their artificial viscosity, which on a compressing face adds $\alpha\nu(\langle\mathbf{U}\rangle_i - \langle\mathbf{U}\rangle_{i-1})$ to the flux, with $\nu = \Delta x\,\lambda\min[(\Delta x\,\lambda)^2/(\beta\gamma p/\rho), 1]$ for the divergence $\lambda < 0$ of the velocity and $\alpha = \beta = 0.3$. Characteristic variables suppress oscillations in some shock tubes of MHD, and Athena++ projects with the eigenvectors of each cell the whole stencil of that cell, which is costly. **[GK]** pyro converts its sources to averages with the sign of the conversion to centres, which leaves them of second order, and its fourth-order solver drops passive scalars from the reconstruction.

Detail: [pyro 2.1.8](../references/pyro-synthesis.md#218-fourth-order-interface-states), [pyro 2.2.3](../references/pyro-synthesis.md#223-the-fourth-order-solver), [pyro 2.4.9](../references/pyro-synthesis.md#249-the-fourth-order-solver), [Athena 2.7.1](../references/athena-synthesis.md#271-finite-volumes-of-fourth-order).

### 2.3 Finite differences with WENO and flux splitting

The conservative finite-difference method keeps the update $-(F_{i+1/2} - F_{i-1/2})/\Delta x$, but reads it as a direct approximation of $\partial f/\partial x$ at the point $x_i$, so that each numerical flux still serves two points and the scheme conserves (Zingale's text, eq. 5.70). **[GK]** The numerical flux approximates $h(x_{i+1/2})$ for a function $h$ whose average over a cell is the flux, so that the point values of the flux play the role of cell averages and the reconstruction formulas of finite volumes carry over, above second order on uniform grids only ([Shu](#shu-1997) 1997, §2.1.2).

The reconstruction of WENO assumes one direction of propagation, which flux splitting supplies (Zingale's text, eqs. 6.26 to 6.29):

$$f = f^+ + f^-, \qquad f^\pm(u) = \tfrac{1}{2}\left[f(u) \pm \alpha_\mathrm{LF}\,u\right], \qquad \alpha_\mathrm{LF} \ge \max|\partial f/\partial u|,$$

the splitting of Lax and Friedrichs, with $\partial f^+/\partial u \ge 0$ and $\partial f^-/\partial u \le 0$. WENO of topic 5 reconstructs $f^+$ at each face from the left and $f^-$ from the right, their sum is the flux, and the method of lines integrates. For a system, $\alpha_\mathrm{LF}$ is the largest speed of all waves, and the split fluxes are reconstructed component by component, which can oscillate even in moderate tests, or in characteristic fields, projected with the left eigenvectors of the Jacobian at an average state and returned with the right ones, which is safer but needs the eigensystem at every face. A local splitting, with $\alpha_\mathrm{LF}$ the largest speed within the stencil, dissipates less. The finite differences keep their order in several dimensions with sweeps of the method of lines and no transverse Riemann problems. pyro advects with $f^\pm = \tfrac{1}{2}(v_x \pm |\mathbf{v}|)\,u$ and WENO of three or five points, under RK4.

Detail: [Zingale 2.3.18](../references/computational-hydrodynamics-synthesis.md#2318-high-order-finite-differences), [Zingale 2.4.6](../references/computational-hydrodynamics-synthesis.md#246-weno-with-flux-splitting), [Zingale 2.5.23](../references/computational-hydrodynamics-synthesis.md#2523-weno-for-the-euler-equations), [pyro 2.2.2](../references/pyro-synthesis.md#222-method-of-lines-solvers).

### 2.4 Upwind constrained transport of fourth order

Constrained transport of second order, as in Athena (topic 10), caps any scheme at second order: its electric fields at the cell corners come from one-dimensional Riemann solutions on the faces and midpoint values. [Londrillo and Del Zanna](#londrillo-del-zanna-2004) (2004) frame upwind constrained transport (UCT) like the fluxes of a Godunov scheme, in a reconstruction and an upwinding, for the electric field at the corners. Felker and Stone (2018, §4) build a UCT of fourth order on the finite volumes of 2.2 in four steps.

1. Reconstruct the velocity and the field from the faces to the corners with transverse PPM of fourth order, $B_y$ along $x$ and $B_x$ along $y$, so that each component stays single-valued on its own faces and four corner states arise.
2. Upwind the electric field over the four states by a Riemann solver of HLL type in two dimensions, with the extreme speeds of the four Riemann solutions on the faces beside the corner.
3. Update the face averages of the field by the theorem of Stokes, which keeps $\nabla\cdot\mathbf{B}$ at round-off.
4. Recompute the cell averages of the field at fourth order from the face averages without limiting.

The scheme reduces to the HLL fluxes of the field for plane-parallel flows. The copy of Athena++ refuses the fourth order with MHD, as this part is not yet merged.

Detail: [Athena 2.7.3](../references/athena-synthesis.md#273-upwind-ct-of-fourth-order).

## 3. Tests

Advection and Burgers' equation show when WENO reaches its order (Zingale's text). A Gaussian travels five times around a periodic domain with three to six stencils under RK4 and under an adaptive integrator of eighth order, and a smooth profile of Burgers' equation is evolved before a shock forms and compared with the solution found by characteristics. After a shock forms, and in Sod's problem and the double rarefaction, WENO meets the piecewise linear method and PPM.

Felker and Stone (2018, §3) validate the fourth order of Athena++ for hydrodynamics against VL2 with PLM. A slotted cylinder of a passive velocity rotates, oblique sound and entropy waves of amplitude $10^{-6}$ cross the periodic domain once on $8 \times 4$ to $128 \times 64$ cells, and the shock of Shu and Osher meets a sinusoidal density. The regression tests require rates of convergence near 2 for the combinations of second order and from 3.4 to 3.95 for those of fourth.

The tests of MHD of Felker and Stone (2018, §5), which the copy cannot repeat, run linear waves and the circularly polarised Alfvén wave for convergence, a field loop advected obliquely in three dimensions for the divergence, the shock tubes of Brio and Wu and of Ryu and Jones for discontinuities, and the vortex of Orszag and Tang, a blast wave and the rotor for robustness.

Detail: [Zingale 2.3.20](../references/computational-hydrodynamics-synthesis.md#2320-convergence-of-weno), [Zingale 2.4.7](../references/computational-hydrodynamics-synthesis.md#247-comparison-and-convergence), [Zingale 2.5.23](../references/computational-hydrodynamics-synthesis.md#2523-weno-for-the-euler-equations), [Athena 2.7.2](../references/athena-synthesis.md#272-tests-of-the-hydrodynamic-subsystem), [Athena 2.7.4](../references/athena-synthesis.md#274-tests-of-mhd).

## 4. Assessment

With RK4, WENO of three stencils converges at fifth order on the Gaussian, but five stencils reach only fourth, as the error in time dominates. At a shock, the piecewise linear method with MC matches WENO, and on Sod's problem WENO captures the contact less cleanly than PPM, while its heating at the contact of the double rarefaction is as bad as that of piecewise constant states. Felker and Stone (2018) find RK4 with PPM on $16 \times 8$ cells as accurate as VL2 with PLM on $128 \times 64$ for the linear waves of hydrodynamics, and four orders of magnitude below it for the MHD waves on 128 cells. The circularly polarised wave keeps nearly its full amplitude at fourth order on $32 \times 16$ cells, where the second order loses over half, $B_z$ of the field loop stays at round-off, the shock tube of Brio and Wu needs characteristic reconstruction, and in three dimensions the cost relative to VL2 with PLM rises well above that in two. **[GK]** Fourth order pays off in smooth flow and long runs, where it trades many cheap cells for fewer expensive ones, and its many operations per memory access suit modern processors. At discontinuities it gains little, needs limiters that preserve extrema, characteristic projection or artificial viscosity to stay free of oscillations, and loses positivity more easily. Its cost per cell update is several times that of second order, with two Riemann solutions per face, conversions with Laplacians and wider stencils, and its restriction to uniform Cartesian meshes in pyro and Athena++, although McCorquodale and Colella formulate it on refined grids, bars it from much of astrophysics for now. Open are whether the shocks and mixing layers of production runs leave smooth regions large enough to repay the fourth order, how it combines with mesh refinement and curvilinear grids, and whether the fourth-order constrained transport, not yet in Athena++, is worth taking on.

## 5. Sources

- <a id="felker-stone-2018"></a>Felker, K. G. and Stone, J. M., A fourth-order accurate finite volume method for ideal MHD via upwind constrained transport, Journal of Computational Physics 375, 1365–1400 (2018), [arXiv:1711.07439](https://arxiv.org/abs/1711.07439), [doi:10.1016/j.jcp.2018.08.025](https://doi.org/10.1016/j.jcp.2018.08.025).
- <a id="londrillo-del-zanna-2004"></a>Londrillo, P. and Del Zanna, L., On the divergence-free condition in Godunov-type schemes for ideal magnetohydrodynamics: the upwind constrained transport method, Journal of Computational Physics 195, 17–48 (2004), [doi:10.1016/j.jcp.2003.09.016](https://doi.org/10.1016/j.jcp.2003.09.016).
- <a id="mccorquodale-colella-2011"></a>McCorquodale, P. and Colella, P., A high-order finite-volume method for conservation laws on locally refined grids, Communications in Applied Mathematics and Computational Science 6, 1–25 (2011), [doi:10.2140/camcos.2011.6.1](https://doi.org/10.2140/camcos.2011.6.1).
- <a id="shu-1997"></a>Shu, C.-W., Essentially non-oscillatory and weighted essentially non-oscillatory schemes for hyperbolic conservation laws, technical report (1997). **[GK]** ICASE Report 97-65, NASA/CR-97-206253, [ntrs.nasa.gov/citations/19980007543](https://ntrs.nasa.gov/citations/19980007543).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

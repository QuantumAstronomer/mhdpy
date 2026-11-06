# Shock tubes and interacting blast waves

## 1. Overview

A shock tube is a Riemann problem: two uniform states meet at a plane, and the waves that leave it have an exact solution in hydrodynamics, against which the speeds, jumps and widths of shocks, contacts and rarefactions are measured. Harder problems in one dimension let shocks collide with each other, with contacts or with smooth structure, approach a vacuum, or launch every family of MHD waves, and oblique tubes in two and three dimensions test whether a planar solution stays planar. All five references run shock tubes: Zingale's text and pyro for Burgers' equation and gas dynamics, Ulula for Sod's problem, ZEUS-2D for Sod's problem, the interacting blast waves and the problem of Brio and Wu, and Athena and Athena++ for a wide set of hydrodynamic and MHD problems. Shocks in several dimensions follow in topic 31, and the Riemann solvers whose differences these problems expose in topic 7.

## 2. Problems

### 2.1 Shocks and rarefactions of Burgers' equation

Two problems of Burgers' equation on 256 cells show its two kinds of wave: a velocity jump from 1 to 2 spreads into a rarefaction, and a sinusoidal bump steepens into a shock that moves right ([Zingale's text](#zingale-2025), eqs. 6.19 and 6.20). Differencing the nonconservative form $u_t + uu_x = 0$, as with an upwind difference for $u_x$, instead of the conservative one gives the wrong speed of the shock. pyro runs a shock along the diagonal of a square, whose speed a script compares with the exact $2\sqrt{2}$, and with viscosity the same shock smeared as it moves.

Detail: [Zingale 2.4.4](../references/computational-hydrodynamics-synthesis.md#244-tests-and-the-conservative-form), [pyro 2.3.3](../references/pyro-synthesis.md#233-problems-and-tests).

### 2.2 Sod's shock tube

The problem of [Sod](#sod-1978) (1978), with $\gamma = 1.4$, separates gas at rest with $\rho = 1$ and $p = 1$ from gas with $\rho = 0.125$ and $p = 0.1$, and launches a rarefaction to the left and a contact and a weak shock to the right. It shows whether a code gets the speed of the shock and the jump conditions right, and stably, and runs along each direction of the grid. Zingale's text adds that flipping the states should mirror the solution to round-off, which a branch such as `if u > 0` that lumps $u = 0$ with $u < 0$ breaks. ZEUS-2D runs it on 100 zones ([Stone and Norman](#stone-norman-1992a) 1992a, §5.4), Athena on 100 cells with reconstruction of third order and HLLC ([Stone et al.](#stone-et-al-2008) 2008, §8.1), and Ulula, pyro and the regression of Athena++ along each axis, the last bounding the error on two grids and their ratio.

Detail: [Zingale 2.5.19](../references/computational-hydrodynamics-synthesis.md#2519-test-problems), [pyro 2.4.12](../references/pyro-synthesis.md#2412-problems-and-tests), [Ulula 2.8.4](../references/ulula-synthesis.md#284-the-shock-tube), [ZEUS 2.7.3](../references/zeus-synthesis.md#273-the-sod-shock-tube), [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

### 2.3 Strong rarefactions

The double rarefaction of [Toro](#toro-1997) (1997), gas with $\rho = 1$ and $p = 0.4$ flowing apart at $\pm 2$, which the text describes as creating a vacuum in the middle (§8.9.1). [Einfeldt et al.](#einfeldt-et-al-1991) (1991) designed such problems to expose weaknesses of Riemann solvers, and Athena runs their test 1-2-0-3, the same states, on 200 cells to $t = 0.1$ (Stone et al. 2008, §8.1). Roe's solver returns negative densities and pressures between the waves, so that the problem tests the fallback of topic 7.

Detail: [Zingale 2.5.19](../references/computational-hydrodynamics-synthesis.md#2519-test-problems), [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

### 2.4 Slow-moving shocks

Slow-moving or stationary shocks can leave oscillations behind them, as [Colella and Woodward](#colella-woodward-1984) (1984) discuss (Zingale's text, §8.9.4). Setting the shock speed to zero in the jump conditions gives the pre-shock velocity for a chosen pre-shock state and pressure jump, and the post-shock state follows, so that a shock can be placed at rest on the grid. The problem shows the noise that a shock emits as it moves slowly across cells.

Detail: [Zingale 2.5.19](../references/computational-hydrodynamics-synthesis.md#2519-test-problems).

### 2.5 Interacting blast waves

The interacting blast waves of [Woodward and Colella](#woodward-colella-1984) (1984) start from gas at rest with $\rho = 1$ between reflecting walls a unit apart, with $p = 1000$ for $x < 0.1$, $p = 100$ for $x > 0.9$ and $p = 0.01$ between. The two shocks reflect from the walls and collide, and by $t = 0.038$ shocks and rarefactions have met several times, which makes the problem react strongly to how a method handles shocks that run into contacts and rarefactions. A computation at very high resolution serves as the reference. ZEUS-2D runs it on 1200 zones with the van Leer method and PPA, and Athena on 400 cells against a reference of 9600.

Detail: [ZEUS 2.7.4](../references/zeus-synthesis.md#274-strong-shocks), [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

### 2.6 A shock in a smooth flow

In the problem of [Shu and Osher](#shu-osher-1989) (1989), a strong shock runs into gas at rest whose density varies as $1 + 0.2\sin(5\pi x)$, and compresses the waves into short oscillations behind it. How sharply these are resolved measures the numerical diffusion of a scheme. Athena runs it on 200 and 800 cells with its limiters of PPM and of Colella and Sekora, and Athena++ on 200 cells with VL2 and PLM against RK3 and PPM, both against references on many more cells ([Stone et al.](#stone-et-al-2020) 2020, §3.3.3).

Detail: [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

### 2.7 The MHD shock tube of Brio and Wu

The MHD analogue of Sod's problem by [Brio and Wu](#brio-wu-1988) (1988) adds a field with $B_x = 0.75$ that reverses its transverse component across the interface, with $\gamma = 2$. The equations of MHD are not convex, so that a slow rarefaction and a slow shock can join into a compound wave, and the problem has no analytic solution; a fast rarefaction and the compound wave move left, and a contact, a slow shock and a fast rarefaction right ([Stone and Norman](#stone-norman-1992b) 1992b, §4.2). ZEUS-2D runs it on 800 zones, Athena on 800 cells against a reference of $10^4$, and Athena++ on 256 cells with primitive and characteristic reconstruction. Athena also runs a nearly coplanar problem of [Torrilhon](#torrilhon-2003) (2003), whose exact ideal solution has no compound wave, although dissipative schemes form one at moderate resolution.

Detail: [ZEUS 2.9.2](../references/zeus-synthesis.md#292-the-mhd-riemann-problem), [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

### 2.8 The problems of Ryu and Jones

[Ryu and Jones](#ryu-jones-1995) (1995) devised many shock tubes of MHD. Their problem 2a launches a discontinuity of every family from the initial state: fast and slow shocks and rotational discontinuities to both sides, and a contact. Their problem 4d contains a slow rarefaction that switches the transverse field on and a slow shock, which tests a solver without an explicit slow wave such as HLLD. Athena runs both on 512 cells with reconstruction of third order, and the regression of Athena++ bounds the error of 2a against its exact solution, which the problem generator holds.

Detail: [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

### 2.9 Oblique shock tubes

Rotated against the grid, a shock tube tests whether a planar solution stays planar and whether CT keeps the normal field constant, which requires a balance of the electric fields along the discontinuity ([Gardiner and Stone](#gardiner-stone-2005) 2005, §5.3). Gardiner and Stone run problem 1a of Ryu and Jones at $\tan^{-1}2$ to a grid of $256 \times 128$ cells, where [Tóth](#toth-2000) (2000) showed that schemes which violate the divergence constraint produce a jump of the normal field at a shock. In three dimensions the discontinuity is inclined so that translations by whole cells leave the solution invariant, which shrinks the transverse extent to a few cells ([Gardiner and Stone](#gardiner-stone-2008) 2008, §6.4), and Athena repeats problem 2a on $768 \times 8 \times 8$ cells.

Detail: [Athena 2.16.4](../references/athena-synthesis.md#2164-shock-tubes).

## 3. Assessment

Burgers' shock is almost infinitely thin without explicit viscosity, and only the conservative form gets its speed right (Zingale's text). In Sod's problem ZEUS-2D spreads the shock and the contact over about four zones, smooths the edges of the rarefaction slightly, which PPA hardly improves, and gets the amplitude of the specific internal energy behind the shock wrong, while agreeing exactly with earlier comparisons of the same algorithms (Stone and Norman 1992a). Athena spreads them over two or three cells and holds that the test no longer discriminates between algorithms (Stone et al. 2008). In the blast waves, ZEUS-2D places all shocks and contacts correctly on 1200 zones, PPA with sharper contacts and a density spike closer to the reference of about 6.5, and Athena on 400 cells follows the reference but smears the contact near $x = 0.6$, apparently a trait of direct Eulerian methods. In the problem of Shu and Osher, the limiters of Colella and Sekora match a WENO scheme of third order where those of PPM clip the extrema, and RK3 with PPM clearly outperforms VL2 with PLM. Roe's solver always fails on the problems of Einfeldt et al., so that Athena falls back to HLLE, needed at a single face in the first step of test 1-2-0-3. ZEUS-2D reproduces the problem of Brio and Wu qualitatively very well, except for an overshoot at the foot of each fast rarefaction, since it is not upwind in the magnetosonic characteristics, and does substantially better than flux-corrected transport and the methods of Lax. Athena captures its discontinuities in two or three cells, with small oscillations at third order, Athena++ needs characteristic reconstruction to avoid strong oscillations behind the fast rarefaction, and on Torrilhon's problem Athena converges to the ideal solution faster than a central scheme. Problem 2a of Ryu and Jones comes out with every discontinuity in two to four cells. In the oblique tubes, the normal field stays constant to round-off along the diagonal of the cells, and at $\tan^{-1}2$ its centred values oscillate by about 10 per cent at the fast shocks, but agree to round-off after averaging over the period of the grid. **[GK]** The exact solution of Ulula lacks a division by the sound speed of the right state, so that its plotted shock runs about 0.1 per cent fast, and the double rarefaction of Toro is a near-vacuum rather than a vacuum. Sod's problem catches gross errors but no longer separates schemes; the blast waves separate the treatment of contacts, the problem of Shu and Osher the dissipation, the strong rarefactions the positivity of solvers, the problem of Brio and Wu the need for characteristic reconstruction, and the oblique tubes CT. For the hydrodynamics of the production runs, Sod's problem with its mirror symmetry, the blast waves, the problem of Shu and Osher and the strong rarefaction form the core.

## 4. Sources

- <a id="brio-wu-1988"></a>Brio, M. and Wu, C. C., An upwind differencing scheme for the equations of ideal magnetohydrodynamics, Journal of Computational Physics 75, 400–422 (1988), [doi:10.1016/0021-9991(88)90120-9](https://doi.org/10.1016/0021-9991%2888%2990120-9).
- <a id="colella-woodward-1984"></a>Colella, P. and Woodward, P. R., The piecewise parabolic method (PPM) for gas-dynamical simulations, Journal of Computational Physics 54, 174–201 (1984), [doi:10.1016/0021-9991(84)90143-8](https://doi.org/10.1016/0021-9991%2884%2990143-8).
- <a id="einfeldt-et-al-1991"></a>Einfeldt, B., Munz, C. D., Roe, P. L. and Sjögreen, B., On Godunov-type methods near low densities, Journal of Computational Physics 92, 273–295 (1991), [doi:10.1016/0021-9991(91)90211-3](https://doi.org/10.1016/0021-9991%2891%2990211-3).
- <a id="gardiner-stone-2005"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport, Journal of Computational Physics 205, 509–539 (2005), [arXiv:astro-ph/0501557](https://arxiv.org/abs/astro-ph/0501557), [doi:10.1016/j.jcp.2004.11.016](https://doi.org/10.1016/j.jcp.2004.11.016).
- <a id="gardiner-stone-2008"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport in three dimensions, Journal of Computational Physics 227, 4123–4141 (2008), [arXiv:0712.2634](https://arxiv.org/abs/0712.2634), [doi:10.1016/j.jcp.2007.12.017](https://doi.org/10.1016/j.jcp.2007.12.017).
- <a id="ryu-jones-1995"></a>Ryu, D. and Jones, T. W., Numerical magnetohydrodynamics in astrophysics: algorithm and tests for one-dimensional flow, ApJ 442, 228 (1995), [doi:10.1086/175437](https://doi.org/10.1086/175437).
- <a id="shu-osher-1989"></a>Shu, C.-W. and Osher, S., Efficient implementation of essentially non-oscillatory shock-capturing schemes, II, Journal of Computational Physics 83, 32–78 (1989), [doi:10.1016/0021-9991(89)90222-2](https://doi.org/10.1016/0021-9991%2889%2990222-2).
- <a id="sod-1978"></a>Sod, G. A., A survey of several finite difference methods for systems of nonlinear hyperbolic conservation laws, Journal of Computational Physics 27, 1–31 (1978), [doi:10.1016/0021-9991(78)90023-2](https://doi.org/10.1016/0021-9991%2878%2990023-2).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="toro-1997"></a>Toro, E. F., Riemann Solvers and Numerical Methods for Fluid Dynamics, Springer (1997), [doi:10.1007/978-3-662-03490-3](https://doi.org/10.1007/978-3-662-03490-3).
- <a id="torrilhon-2003"></a>Torrilhon, M., Non-uniform convergence of finite volume schemes for Riemann problems of ideal magnetohydrodynamics, Journal of Computational Physics 192, 73–94 (2003), [doi:10.1016/S0021-9991(03)00347-4](https://doi.org/10.1016/S0021-9991%2803%2900347-4).
- <a id="toth-2000"></a>Tóth, G., The $\nabla \cdot \mathbf{B} = 0$ constraint in shock-capturing magnetohydrodynamics codes, Journal of Computational Physics 161, 605–652 (2000), [doi:10.1006/jcph.2000.6519](https://doi.org/10.1006/jcph.2000.6519).
- <a id="woodward-colella-1984"></a>Woodward, P. R. and Colella, P., The numerical simulation of two-dimensional fluid flow with strong shocks, Journal of Computational Physics 54, 115–173 (1984), [doi:10.1016/0021-9991(84)90142-6](https://doi.org/10.1016/0021-9991%2884%2990142-6).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

# Advection and linear waves

## 1. Overview

Advection and linear waves are the smooth tests of the whole scheme: a profile carried by a uniform flow, or a small eigenmode of the equations, returns to a known state, so that the error measures dissipation, dispersion and the order of convergence, and symmetries catch coding errors. Discontinuous profiles test the limiters, and nonlinear waves with exact solutions test the scheme beyond linear theory. Zingale's text, pyro and Ulula advect profiles of density and run sound waves, ZEUS-2D measures convergence and the propagation of shear Alfvén waves, and Athena and Athena++ run linear waves of every mode of MHD in one, two and three dimensions and the circularly polarised Alfvén wave. The norms and procedures of convergence follow in topic 25, the slotted cylinder in topic 18 and the advection of a field loop in topic 10.

## 2. Problems

### 2.1 Smooth advected profiles

A profile of density at uniform pressure and velocity moves without dynamics and returns after one period, so that any difference from its initial state is numerical error. Zingale's text advects a Gaussian with the parameters of [Fryxell et al.](#fryxell-et-al-2000) (2000) for ten periods ([Zingale's text](#zingale-2025), §8.9.3). pyro advects a Gaussian diagonally through a periodic square for one period, with the limiter off and steps fixed in proportion to the cell width for convergence, also on a spherical grid, and its solvers of scalar advection the same Gaussian on $32^2$ cells. Ulula advects a sine wave through a periodic line and a sum of sines through a periodic square, the former for its convergence study (topic 25).

Detail: [Zingale 2.5.19](../references/computational-hydrodynamics-synthesis.md#2519-test-problems), [pyro 2.2.5](../references/pyro-synthesis.md#225-problems-and-tests), [pyro 2.4.12](../references/pyro-synthesis.md#2412-problems-and-tests), [Ulula 2.8.2](../references/ulula-synthesis.md#282-advection-in-one-dimension), [Ulula 2.8.8](../references/ulula-synthesis.md#288-advection-in-two-dimensions).

### 2.2 Discontinuous advected profiles

A top hat tests the limiters and Riemann solvers, as its edges show how fast a scheme diffuses and whether it oscillates. pyro's scalar advection carries a circular top hat across a periodic square, and Ulula a top hat of density in one dimension on 100 cells and a circular one in two on $100 \times 100$ cells. Ulula runs each with twelve combinations of integrator, reconstruction, limiter and Riemann solver, which its docstring calls perhaps the simplest meaningful test of a scheme. The edges of a two-dimensional top hat diffuse into the surroundings at a speed that the solver sets.

Detail: [pyro 2.2.5](../references/pyro-synthesis.md#225-problems-and-tests), [Ulula 2.8.2](../references/ulula-synthesis.md#282-advection-in-one-dimension), [Ulula 2.8.8](../references/ulula-synthesis.md#288-advection-in-two-dimensions).

### 2.3 Sound waves and the acoustic pulse

Ulula drives a sound wave of relative amplitude 0.01 and frequency 1 Hz into air from the left boundary of a domain 1 km long, in physical units, and compares it with the linear wave up to its front. The setup shows that sound waves exist, how fast they travel and how they steepen at larger amplitudes. pyro runs the acoustic pulse of [McCorquodale and Colella](#mccorquodale-colella-2011) (2011), a smooth isentropic bump of density at rest in a periodic square, on 64 to 512 cells with steps scaled by the cell width, for the convergence of its solvers of fourth order.

Detail: [Ulula 2.8.3](../references/ulula-synthesis.md#283-the-sound-wave), [pyro 2.4.12](../references/pyro-synthesis.md#2412-problems-and-tests).

### 2.4 Linear waves of hydrodynamics and MHD

Each eigenmode of the equations, with an amplitude of $10^{-6}$ on a uniform state chosen for well separated speeds, travels one wavelength through a periodic domain, and the norm of the difference from the initial state gives its error ([Stone et al.](#stone-et-al-2008) 2008, §8.1 and §8.2). In one dimension Athena runs the sound, contact and shear waves and the fast, Alfvén, slow and entropy waves of MHD, whose speeds are 2, 1 and 1/2, and checks that waves travelling left and right err identically to every digit and that a background moving at $-c_\mathrm{s}$ turns a sound wave into a standing one. In two dimensions the wave travels at $\tan^{-1}2$ to the grid and in three along a rotated direction with exactly one period along each axis ([Gardiner and Stone](#gardiner-stone-2005) 2005, §5.4; [2008](#gardiner-stone-2008), §6.2). Athena++ repeats the three-dimensional test with its integrators and reconstructions, and its regression tests bound the errors on two grids, their ratio and the agreement of left- and right-going waves ([Stone et al.](#stone-et-al-2020) 2020, §3.3.1).

Detail: [Athena 2.16.1](../references/athena-synthesis.md#2161-linear-waves).

### 2.5 Circularly polarised Alfvén waves

The circularly polarised Alfvén wave of [Tóth](#toth-2000) (2000) solves the nonlinear equations of ideal MHD exactly, travelling, or standing in a flow along the field at the Alfvén speed. Gardiner and Stone (2005, 2008) run it obliquely in two and three dimensions, where the truncation error of the transverse field perturbs the magnetic pressure and drives compressive waves, and see no sign of the parametric instability that has limited its use. Stone et al. (2008, §8.4) follow it for five crossing times at several resolutions. The regression of Athena++ runs it isothermally with static refinement and requires an error below $2 \times 10^{-4}$, a ratio between two grids of at most 0.3 and nearly equal errors for the two polarisations.

Detail: [Athena 2.16.2](../references/athena-synthesis.md#2162-circularly-polarised-alfvén-waves).

### 2.6 Shear Alfvén waves

ZEUS-2D launches square pulses of transverse velocity and field in a region of a Cartesian grid threaded by a uniform field, which travel in opposite directions along the field lines, as in the magnetic braking of [Mouschovias and Paleologou](#mouschovias-paleologou-1980) (1980) with a shear in place of a rotation ([Stone and Norman](#stone-norman-1992b) 1992b, §4.6). In a fluid at rest the pulses should keep their shape, and in a fluid moving at 1.5, with an Alfvén speed of 1, their fronts should travel at 0.5 and 2.5. The test compares the original electric fields of CT, upwinded with the fluid velocity, with those of the method of characteristics (topic 10).

Detail: [ZEUS 2.9.7](../references/zeus-synthesis.md#297-shear-alfvén-waves).

### 2.7 Convergence on a smooth wind

ZEUS-2D measures the convergence of its whole code of MHD on a one-dimensional magnetised wind, which has no discontinuities, by the three kinds of test of [Hawley](#hawley-1989) (1989) (Stone and Norman 1992b, §4.3). A single step from the analytic solution, with the mean absolute error per unit time, is cheap enough for very high resolution and isolates single terms, an extended evolution compares with the analytic solution at a fixed time, and self-convergence compares runs at three resolutions where boundaries keep the code from the analytic solution. The wind runs on 50 to 1000 radial points with the van Leer method, leaving out the points next to the boundaries.

Detail: [ZEUS 2.9.4](../references/zeus-synthesis.md#294-convergence-tests).

## 3. Assessment

The Gaussian of Zingale's text keeps its shape after ten periods but has its peak clipped. pyro's smooth profile converges close to second order, held below it by the limiters, and the error of its solver of fourth order falls by a factor of about 16 per doubling from 32 cells on. Ulula's top hat tells the methods apart clearly: constant states with the Euler integrator and HLL smear it into a hump of height 0.84, MC with the Euler integrator and HLLC oscillates up to 1.3, and MC with the Hancock step and HLLC gives the sharpest profile without visible oscillations; without reconstruction the two-dimensional top hat is extremely diffusive. In one dimension HLLC and Roe give nearly identical errors of linear waves that converge at second order, HLLE slightly larger ones that converge more slowly, and with 16 or more cells per wavelength diffusion dominates over dispersion (Stone et al. 2008). In three dimensions all families converge at second order, the fast wave with about twice the error of one dimension. In Athena++ convergence is strictly of second order with VL2 or PLM, while RK3 with PPM lowers the errors at least tenfold and approaches third order for some families, which suggests that errors in time dominate (Stone et al. 2020). The Alfvén wave keeps at least 0.8 of its amplitude on 8 cells per wavelength and more than 0.95 on 16 or more, converging at second order. The original electric fields of ZEUS-2D leave a large dispersion error in the shear pulses, while the method of characteristics propagates them accurately at the right speeds. On the wind, the single-step test gives rates of 1.0 and self-convergence rates of 1.5 to 2.2, for reasons left open, and the authors find single-step rates the best guide to the equation at fault. **[GK]** Ulula's sound wave fits the isothermal sound speed at 300 K rather than that of the ideal gas of its example, and pyro's measure of error for its fourth-order advection compares averages with centre values, which caps the measured order at two. Linear waves at small amplitude separate the order, dissipation and dispersion of schemes most precisely, oblique waves in several dimensions test the multidimensional integrator and CT, and exact symmetries catch bugs that a norm hides. Discontinuous profiles separate limiters and solvers but not orders, and the acoustic pulse is needed for schemes beyond second order. For mhdpy the two-dimensional oblique waves of hydrodynamics, with the left–right and standing-wave checks, serve the production runs first.

## 4. Sources

- <a id="fryxell-et-al-2000"></a>Fryxell, B., Olson, K., Ricker, P., Timmes, F. X., Zingale, M., Lamb, D. Q., MacNeice, P., Rosner, R., Truran, J. W. and Tufo, H., FLASH: an adaptive mesh hydrodynamics code for modeling astrophysical thermonuclear flashes, ApJS 131, 273–334 (2000), [doi:10.1086/317361](https://doi.org/10.1086/317361).
- <a id="gardiner-stone-2005"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport, Journal of Computational Physics 205, 509–539 (2005), [arXiv:astro-ph/0501557](https://arxiv.org/abs/astro-ph/0501557), [doi:10.1016/j.jcp.2004.11.016](https://doi.org/10.1016/j.jcp.2004.11.016).
- <a id="gardiner-stone-2008"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport in three dimensions, Journal of Computational Physics 227, 4123–4141 (2008), [arXiv:0712.2634](https://arxiv.org/abs/0712.2634), [doi:10.1016/j.jcp.2007.12.017](https://doi.org/10.1016/j.jcp.2007.12.017).
- <a id="hawley-1989"></a>Hawley, J. F., private communication to Stone and Norman (1989).
- <a id="mccorquodale-colella-2011"></a>McCorquodale, P. and Colella, P., A high-order finite-volume method for conservation laws on locally refined grids, Communications in Applied Mathematics and Computational Science 6, 1–25 (2011), [doi:10.2140/camcos.2011.6.1](https://doi.org/10.2140/camcos.2011.6.1).
- <a id="mouschovias-paleologou-1980"></a>Mouschovias, T. Ch. and Paleologou, E. V., Magnetic braking of an aligned rotator during star formation: an exact, time-dependent solution, ApJ 237, 877–899 (1980), [doi:10.1086/157936](https://doi.org/10.1086/157936).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="toth-2000"></a>Tóth, G., The $\nabla \cdot \mathbf{B} = 0$ constraint in shock-capturing magnetohydrodynamics codes, Journal of Computational Physics 161, 605–652 (2000), [doi:10.1006/jcph.2000.6519](https://doi.org/10.1006/jcph.2000.6519).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

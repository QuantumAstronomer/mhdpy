# Verification and testing

## 1. Overview

A simulation rests on a chain of approximations, from the choice of equations to their discretisation, so that its output is tested against problems with known solutions and against physical intuition, and never trusted blindly ([Zingale's text](#zingale-2025), §1.1). The references measure errors in norms, determine orders of convergence with and without exact solutions, check conservation, build suites of tests from single terms up to whole problems, and guard their codes by regression tests against stored results. Zingale's text sets out the errors, norms and convergence studies, Ulula checks conservation and convergence, ZEUS designs its suites of tests, and pyro and Athena++ run regression tests, Athena++ with continuous integration. The test problems themselves follow in topics 29 to 33.

## 2. Methods

### 2.1 Round-off and truncation error

Round-off error comes from representing numbers with a finite number of bits ([Goldberg](#goldberg-1991) 1991). Machine epsilon, the last $\epsilon$ halved from one for which $1 + \epsilon$ still differs from one, differs between single and double precision, and rearranging an expression, as $x^3 - y^3 = (x - y)(x^2 + xy + y^2)$, can reduce round-off but never remove it (Zingale's text, §1.2.1). Truncation error belongs to the algorithm: an operator is approximated by a series in a small quantity, and the dropped terms form the error, so that $\sin x \approx x - x^3/6$ is of fifth order. Measuring how the error falls as the small quantity shrinks is a convergence test. Since the systems are strongly nonlinear, a change of compiler or optimisation can change the numbers considerably, and trends matter more than precise values (§1.1). **[GK]** In double precision machine epsilon is $2^{-52} \approx 2.2 \times 10^{-16}$, the spacing of floating-point numbers just above one, which Goldberg halves to bound the error of rounding. The loss in a subtraction stems from operands that are close rather than large, whose leading digits cancel and expose their rounding errors.

Detail: [Zingale 2.1.1](../references/computational-hydrodynamics-synthesis.md#211-simulation-and-its-approximations), [Zingale 2.1.2](../references/computational-hydrodynamics-synthesis.md#212-round-off-and-truncation-error).

### 2.2 Norms and the order of convergence

A norm condenses the pointwise errors of $N$ cells into one number (Zingale's text, eqs. 1.16 to 1.19):

$$\|q\|_\infty = \max_i|q_i|, \qquad \|q\|_p = \left[\frac{1}{N}\sum_{i=0}^{N-1}|q_i|^p\right]^{1/p}.$$

The factor $1/N$ makes norms on grids of different resolution comparable. The maximum norm is local, giving one cell all the weight, while the others are global. With periodic boundaries, a profile advected for one period should return to its initial state, so that the norm of the difference is its error, absolute or relative to the norm of the initial state (eqs. 4.21 and 4.22). **[GK]** If the error scales as $\Delta x^p$, the errors on $N$ and $2N$ cells give the measured order $p = \log_2(\epsilon_N/\epsilon_{2N})$.

Detail: [Zingale 2.1.6](../references/computational-hydrodynamics-synthesis.md#216-norms), [Zingale 2.3.6](../references/computational-hydrodynamics-synthesis.md#236-errors-and-convergence).

### 2.3 Convergence without an exact solution

A code with several physical processes should be tested for its expected order of convergence, usually without an analytic solution (Zingale's text, §13.5).

1. Run the problem in pairs that differ in resolution by a factor of two.
2. Average the finer field onto the coarser grid and take the norm of the difference, $\epsilon = \|\phi_\mathrm{c} - \langle\phi_\mathrm{f}\rangle_\mathrm{c}\|$.
3. Let the finer run of one pair serve as the coarser of the next.
4. Take the order from the errors of two successive pairs, as in 2.2.

[Almgren et al.](#almgren-et-al-2008) (2008) and [McCorquodale and Colella](#mccorquodale-colella-2011) (2011) use this procedure. The problem must be smooth, since discontinuities do not converge with resolution and limiters act there. Alternatively, a benchmark at much higher resolution, averaged onto each coarser grid, serves as the reference, as for viscous Burgers' equation (topic 18). pyro's scripts restrict the finer of two outputs to the coarser grid and tabulate the maximum and $L_2$ norms of the differences, with an order between successive pairs and a plot against the number of cells.

Detail: [Zingale 2.9.2](../references/computational-hydrodynamics-synthesis.md#292-boundaries-time-steps-and-convergence), [pyro 3.4](../references/pyro-synthesis.md#34-output-analysis-and-testing).

### 2.4 Conservation, resolution and the design of suites

Ulula checks whether mass, momentum and energy are conserved where they should be ([Diemer](#diemer-2025) 2025, §4.2): outflow boundaries violate all three laws and walls that of momentum, gravitational sources break strict conservation, and otherwise the laws hold to machine precision. ZEUS-2D isolates single terms of the difference equations first and builds up to problems that use the whole code, from advection in one dimension through a shock tube to strong shocks in two dimensions ([Stone and Norman](#stone-norman-1992a) 1992a, §5). Tests catch coding errors first, but their main task is to benchmark the algorithms, showing their strengths and limits so that features of the physics can be told from artefacts of the numerics. For MHD, then a young field, ZEUS-2D assembled a new collection of tests, described in enough detail for others to calibrate their codes ([Stone and Norman](#stone-norman-1992b) 1992b, §4). Comparisons between codes build further confidence, as for the interaction of discs and planets, turbulent Rayleigh–Taylor mixing and the Santa Barbara cluster (Zingale's text, §1.1).

Resolution bounds what a test can show (Zingale's text, §13.1 to §13.4). A simulation that leaves the dissipation to the numerical diffusion of its method is an implicit large eddy simulation, which suffices for many flows, and a resolved inertial range of about a decade appears at around 512 cells on a side. Turbulence differs between two and three dimensions, boundaries belong far from the action, and the Courant condition ensures stability, not accuracy, so that sources such as vigorous reactions may need shorter steps.

Detail: [Ulula 2.8.17](../references/ulula-synthesis.md#2817-conservation-and-convergence), [ZEUS 2.7.1](../references/zeus-synthesis.md#271-approach-and-advection-tests), [ZEUS 2.9.1](../references/zeus-synthesis.md#291-approach-and-advection-tests), [Zingale 2.9.1](../references/computational-hydrodynamics-synthesis.md#291-approximations-and-resolution), [Zingale 2.9.2](../references/computational-hydrodynamics-synthesis.md#292-boundaries-time-steps-and-convergence).

### 2.5 Regression tests and reproducibility

pyro's regression tests run 16 problems of 14 solvers and compare each final state with a stored benchmark, variable by variable over the valid cells, to a relative tolerance of $10^{-12}$; unit tests and notebooks run under pytest. The [pyro paper](#zingale-2014) preferred an exact comparison, cell by cell, since a difference at the level of round-off then shows that the code or its environment has changed, at the price of benchmarks for each platform. Athena++ runs more than 60 regression tests, from checks of compilation to benchmarks of several modules, compared with analytic solutions where possible ([Stone et al.](#stone-et-al-2020) 2020). Each test consists of three functions.

1. Prepare: configure and compile the code with the options of the test.
2. Run: execute it with an input file and changed parameters, serially or under MPI.
3. Analyse: read the outputs, compute norms or differences on a common grid, and return whether the test passes.

A script runs all tests, those of chosen groups or single ones, and reports times and failures. The sources are checked for style, every change is tested by continuous integration with several compilers, architectures and versions of libraries, and coverage reaches about 65 per cent of the lines. Rerunning the same code does not make results correct: true reproducibility needs independent implementations or codes, which open development supports, and Athena++ bundles the inputs and scripts behind published results.

Detail: [pyro 3.4](../references/pyro-synthesis.md#34-output-analysis-and-testing), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [Athena 3.8](../references/athena-synthesis.md#38-regression-tests).

## 3. Tests

Ulula measures the convergence of three problems from 16 to 256 cells: the advection of a sine wave in one dimension, a blob in free fall under gravity, and the Gresho vortex. The error is the $L_1$ norm of the fractional difference of the density from the known solution after one unit of time, normalised to its value on 64 cells, so that the slope shows the order directly.

ZEUS-2D measures the convergence of the whole code of MHD on the winds of Weber and Davis, rotating magnetised outflows that test the coupling of velocity and field (Stone and Norman 1992b, §5). Athena++ turns convergence into regression tests across its modules, which require measured orders above thresholds such as 1.99 for diffusion or 1.8 for relativistic waves (topics 16 and 25).

Detail: [Ulula 2.8.17](../references/ulula-synthesis.md#2817-conservation-and-convergence), [ZEUS 2.9.8](../references/zeus-synthesis.md#298-conclusions-from-the-tests), [Athena 3.8](../references/athena-synthesis.md#38-regression-tests).

## 4. Assessment

Ulula's three errors fall slightly less steeply than the $N^{-2}$ of a perfect scheme of second order, from 8 to 14 times the error on 64 cells at 16 cells to about 0.1 times it at 256, which the paper takes as convergence essentially as expected (Diemer 2025). The whole MHD code of ZEUS-2D converges at less than second order on the winds, for reasons left open, and its authors stress that convergence tests quantify the performance of a code well and find subtle bugs. **[GK]** Runs of Ulula reproduce its figure only roughly, and its free fall can be compared only with the known solution, since the blob moves. pyro's script prints the square root of the ratio of successive norms as the order, which equals the order only for orders of 2 and 4, and its comparisons through `numpy.allclose` keep an absolute tolerance of $10^{-8}$, so that small values always agree. Both show that the tools of verification need tests of their own. For mhdpy, the criteria of correctness ask for measured orders that match the formal order on smooth problems and conservation to round-off, which the norms of 2.2, the self-convergence of 2.3 and the checks of conservation of 2.4 provide. Regression benchmarks with a tolerance survive changes of platform but hide changes of round-off, while exact benchmarks catch them at the cost of one benchmark per platform, and NumPy may change the last digits between versions. Open are the norms and variables by which orders are measured, the tolerance of regression comparisons, and whether exact benchmarks are kept for a reference platform.

## 5. Sources

- <a id="almgren-et-al-2008"></a>Almgren, A. S., Bell, J. B., Nonaka, A. and Zingale, M., Low Mach number modeling of type Ia supernovae. III. Reactions, ApJ 684, 449–470 (2008), [doi:10.1086/590321](https://doi.org/10.1086/590321).
- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="goldberg-1991"></a>Goldberg, D., What every computer scientist should know about floating-point arithmetic, ACM Computing Surveys 23, 5–48 (1991), [doi:10.1145/103162.103163](https://doi.org/10.1145/103162.103163).
- <a id="mccorquodale-colella-2011"></a>McCorquodale, P. and Colella, P., A high-order finite-volume method for conservation laws on locally refined grids, Communications in Applied Mathematics and Computational Science 6, 1–25 (2011), [doi:10.2140/camcos.2011.6.1](https://doi.org/10.2140/camcos.2011.6.1).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="zingale-2014"></a>Zingale, M., pyro: a teaching code for computational astrophysical hydrodynamics, Astronomy and Computing 6, 52–62 (2014), [arXiv:1306.6883](https://arxiv.org/abs/1306.6883), [doi:10.1016/j.ascom.2014.07.003](https://doi.org/10.1016/j.ascom.2014.07.003).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

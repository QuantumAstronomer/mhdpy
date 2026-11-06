# Equations of state

## 1. Overview

An equation of state (EOS) closes the equations of [topic 1](01-equations-and-their-variables.md). It gives the pressure from the density and the internal energy, the sound speed for the time step and the Riemann solvers, and the temperature where sources need it. All five references use the ideal gas, and Ulula and Athena++ also offer the isothermal one. pyro has only the ideal gas, while ZEUS, which evolves the internal energy, takes any $p(\rho, e)$ directly. Zingale's text and Athena++ treat a general EOS: the text after Colella and Glaz, who carry an extra index of the gas to the faces, and Athena++ through the framework of Coleman, which reduces any EOS that meets the conditions of 2.3 to three functions, analytic or tabulated, and tests it on eleven problems. The internal energy at high Mach numbers, the floors that keep density and pressure positive, and the root finding that inverts an EOS complete the topic. The temperatures of reactions and networks follow in [topic 19](19-reactions-chemistry-and-cooling.md), those of radiative cooling in [topic 20](20-radiative-cooling.md), and the relativistic equations of state in [topic 25](25-relativistic-mhd.md).

## 2. Methods

### 2.1 The ideal and the isothermal gas

An ideal gas has ([Diemer](#diemer-2025) 2025, eq. 4)

$$p = n k_\mathrm{B} T = \frac{\rho k_\mathrm{B} T}{\mu m_\mathrm{p}} = (\gamma - 1)\,\rho e, \qquad c_\mathrm{s}^2 = \frac{\gamma p}{\rho},$$

with the number density $n$, Boltzmann's constant $k_\mathrm{B}$, the temperature $T$ and the mean particle mass $\mu$ in units of the proton mass $m_\mathrm{p}$. The adiabatic index is $5/3$ for an atomic gas and $7/5$ for a diatomic molecular one. Ulula takes $5/3$ by default and pyro $1.4$, while Athena++ requires it to be given. An isothermal gas keeps $T$, and with it $e$, constant. It is barotropic, $p = c_\mathrm{s}^2\rho$ with the constant $c_\mathrm{s}^2 = p/\rho$, so that the energy equation is dropped. Ulula and Athena++ offer it, Athena++ with a given sound speed and Ulula with a given internal energy, which may be derived from a temperature.

In MHD the fast magnetosonic speed along $x$ enters the time step and the Riemann solvers. Athena++ computes it in a form that avoids the difference of two large terms:

$$c_\mathrm{fast}^2 = \frac{\gamma p + B^2 + \sqrt{(B^2 - \gamma p)^2 + 4\gamma p B_\perp^2}}{2\rho},$$

with the transverse field $B_\perp$, and with $c_\mathrm{s}^2\rho$ for $\gamma p$ in an isothermal gas. **[GK]** It equals the usual form, since $(\gamma p + B^2)^2 - 4\gamma p B_x^2 = (B^2 - \gamma p)^2 + 4\gamma p\,(B^2 - B_x^2)$, and $B^2 - B_x^2 = B_\perp^2$.

Detail: [Ulula 2.1.2](../references/ulula-synthesis.md#212-equations-of-state), [pyro 2.4.1](../references/pyro-synthesis.md#241-variables-and-equation-of-state), [Athena 2.2.1](../references/athena-synthesis.md#221-ideal-and-isothermal-gases).

### 2.2 The internal energy and floors

The temperature follows from the EOS as $T(\rho, e)$, with $\rho e = E - \rho v^2/2$ ([Zingale's text](#zingale-2025), eqs. 8.123 and 8.124). Where the kinetic energy dominates, at high Mach numbers, the truncation errors of the kinetic energy relative to $E$ can make $e$ negative, so that a floor or another way of finding $e$ is needed. [Bryan et al.](#bryan-et-al-1995) (1995) evolve both the total and the internal energy in each cell, and use the internal energy where the kinetic energy dominates. The internal energy obeys no conservation law, so that each switch to it leaves an error in the total energy.

Floors raise a density or a pressure that has fallen too low, at the cost of adding mass or energy. Athena++ applies them in its conversion to primitive variables, with defaults near $3.5 \times 10^{-18}$ in code units, and again to the reconstructed states at the faces.

1. Raise the density to its floor, $\rho \leftarrow \max(\rho, \rho_\mathrm{floor})$, leaving momentum and energy unchanged.
2. Divide the momentum by the density, $\mathbf{v} = (\rho\mathbf{v})/\rho$.
3. Compute the pressure, $p = (\gamma - 1)(E - \rho v^2/2 - B^2/2)$, with the field at the cell centres averaged from the faces.
4. Where $p < p_\mathrm{floor}$, set $p = p_\mathrm{floor}$ and raise $E$ to match.

For a general EOS the floor acts on the internal energy instead. Ulula stops with an error at a pressure that is not positive unless a floor is set, and then raises the pressures below the floor only when some pressure in the array is zero or negative, while pyro only asserts that density and internal energy are positive.

Detail: [Zingale 2.5.21](../references/computational-hydrodynamics-synthesis.md#2521-temperature-and-internal-energy), [pyro 2.4.1](../references/pyro-synthesis.md#241-variables-and-equation-of-state), [Ulula 2.1.2](../references/ulula-synthesis.md#212-equations-of-state), [Athena 2.2.1](../references/athena-synthesis.md#221-ideal-and-isothermal-gases), [Athena 2.2.3](../references/athena-synthesis.md#223-tables-and-the-eos-of-hydrogen).

### 2.3 The general equation of state

A finite-difference code such as ZEUS takes a general EOS easily, but a Godunov code must solve its Riemann problems with the same EOS ([Coleman](#coleman-2020) 2020, §1). The Riemann problem has a unique solution if $(\partial p/\partial\rho)_e > 0$ and $(\partial p/\partial e)_\rho > 0$ (eqs. 4 and 5). [Chen et al.](#chen-et-al-2019) (2019) solve it exactly for any EOS, at a cost too high for simulations, which use approximate solvers instead ([topic 7](07-riemann-solvers.md)), and show that its generalisation needs the exact adiabatic sound speed, $c_\mathrm{s}^2 = (\partial p/\partial\rho)_s$ at constant specific entropy (Coleman 2020, eq. 8). **[GK]** Coleman prints eq. 4 with the internal energy per volume, under which the ideal gas would fail it; with the specific energy of the notation page it holds.

Athena++ reduces any EOS that meets these conditions to three functions (Coleman 2020, eqs. 13 to 18), which replace the relations of the ideal gas:

$$p(\rho, \rho e) \;\text{for}\; (\gamma - 1)\rho e, \qquad \rho e(\rho, p) \;\text{for}\; \frac{p}{\gamma - 1}, \qquad c_\mathrm{s}^2(\rho, p) \;\text{for}\; \frac{\gamma p}{\rho}.$$

The first converts conserved to primitive variables, once the kinetic and magnetic energies are subtracted from $E$, the second converts back, and the third serves the time step and the Riemann solvers. Every occurrence of $\gamma$ in the code is replaced in this way, which keeps all the characteristic speeds of the Riemann problem (Chen et al. 2019, App. B). The one further change is to the estimates of the wave speeds in the Riemann solvers. Reconstruction in characteristic variables does not support a general EOS.

Colella and Glaz reduce the calls of a costly EOS by carrying an extra index with the primitive variables into the states at the faces and the Riemann problem ([Zingale's text](#zingale-2025), eqs. 8.125 and 8.126; [Colella and Glaz](#colella-glaz-1985) 1985, eq. 26):

$$\gamma_e = \frac{p}{\rho e} + 1, \qquad \frac{D\gamma_e}{Dt} = (\gamma_e - 1)(\gamma_e - \Gamma_1)\,\nabla\cdot\mathbf{v}.$$

$\Gamma_1$ sets only the sound speed, not the fluxes, and can be carried to the faces as piecewise constant without losing second order. Castro instead predicts $\rho e$ to the faces with $\rho$, $v_x$ and $p$, which over-specifies the thermodynamics but needs no $\gamma_e$ (eqs. 8.134 to 8.138). **[GK]** The equation for $\gamma_e$ follows from $Dp/Dt = -\Gamma_1 p\,\nabla\cdot\mathbf{v}$ and $D(\rho e)/Dt = -(\rho e + p)\,\nabla\cdot\mathbf{v}$: their difference gives $D\ln(\gamma_e - 1)/Dt = D\ln p/Dt - D\ln(\rho e)/Dt = (\gamma_e - \Gamma_1)\,\nabla\cdot\mathbf{v}$.

Detail: [Zingale 2.5.22](../references/computational-hydrodynamics-synthesis.md#2522-general-equations-of-state), [Athena 2.2.2](../references/athena-synthesis.md#222-the-general-eos).

### 2.4 Tables and the inversion of an equation of state

The three functions may be interpolated in a table ([Coleman](#coleman-2020) 2020, eqs. 19 to 28). Athena++ stores the dimensionless $\log[p/(\rho e)]$, $\log[\rho e/p]$ and $\log\Gamma_1$, with $\Gamma_1 = \rho c_\mathrm{s}^2/p$, on a regular grid in $\log\rho$ and in $\log(\rho e) + \eta\log\rho$ or $\log p + \eta\log\rho$, where $\eta = -1$ by default makes the second coordinate specific. Bilinear interpolation keeps the values monotonic between the points, and off the table they are extrapolated linearly, which floors and a large enough table should prevent. For an ideal gas the three quantities are the constants $\gamma - 1$, $1/(\gamma - 1)$ and $\gamma$, so that a table of two points in each direction reproduces it to machine precision.

An analytic EOS in density and temperature must be inverted for the temperature at each call, by root finding ([Zingale's text](#zingale-2025), eqs. 1.14 and 1.15). Newton–Raphson needs a good first guess and a derivative that does not vanish, and can fall into a cycle. The secant method replaces the derivative by a difference, bisection halves an interval that brackets the root, and Brent's method combines several methods into a robust one. Athena++ inverts its EOS of hydrogen by the method of Brent and Dekker to one part in $10^{12}$, between the bounds of complete and of no ionisation, and in the tests of Coleman (2020, §4.4) the Helmholtz EOS is inverted by steps of Newton–Raphson, secant and bisection that start from the last temperature found.

1. Start from a guess $T_0$, such as the last temperature found.
2. Correct it by Newton–Raphson, $\delta T = -[e(\rho, T_0) - e]/(\partial e/\partial T)_\rho$.
3. Repeat until $|\delta T|$ falls below the tolerance.
4. **[GK]** Where the iteration fails to converge, fall back on bisection between bounds that bracket the root.

Detail: [Zingale 2.1.5](../references/computational-hydrodynamics-synthesis.md#215-root-finding), [Athena 2.2.3](../references/athena-synthesis.md#223-tables-and-the-eos-of-hydrogen), [Athena 2.2.4](../references/athena-synthesis.md#224-tests-of-general-equations-of-state).

## 3. Tests

Tests 1 to 9 of Athena++ use an EOS of hydrogen with electrons, neutral hydrogen and protons in local thermal equilibrium ([Coleman](#coleman-2020) 2020, App. B). The Saha equation gives the ionisation fraction $x_\mathrm{ion} = 2/[1 + (1 + 4\tilde\rho\exp(1/\tilde T)\,\tilde T^{-3/2})^{1/2}]$, with $\tilde\rho = \rho/(m_\mathrm{p}n_q)$ and $\tilde T = T/T_\mathrm{ion}$, where $T_\mathrm{ion} = 157\,888$ K is the ionisation temperature and $n_q$ a number density set by it, and through the transition $\Gamma_1$ varies strongly. The EOS is evaluated analytically in every call, so that the resolution of a table cannot affect the convergence. Its units, $m_\mathrm{p}$, $T_\mathrm{ion}$ and $n_q$, define those of the tests.

Six Riemann problems with this EOS test the nonlinear hydrodynamics through ionisation (Coleman 2020, §4.1). Tests 1 and 2 are shock tubes like Sod's, tests 3 and 4 asymmetric double shocks with supersonic inflow from both sides, and tests 5 and 6 double rarefactions, all with the ionisation fraction and $\Gamma_1$ varying strongly. Exact solutions to arbitrary precision come from a solver after Chen et al. (2019). The $L_1$ and $L_2$ errors are taken on 64 to 2048 cells at a Courant number of 0.4, where discontinuities should give linear convergence.

Test 7 extends the problem to MHD, for which no published test with a general EOS had an exact solution (§4.2). It keeps the outer states of test 2a of [Ryu and Jones](#ryu-jones-1995) (1995), chosen so that all seven waves are discontinuities, with the EOS of hydrogen and units tuned for a large variation of $\Gamma_1$. The jump conditions across the seven waves give 49 equations for the six intermediate states and the seven mass fluxes, solved numerically.

Tests 8 and 9 are a sound wave and a fast magnetosonic wave in one dimension, run for exactly one crossing time (§4.3). The background sits within 1% of the temperature at which $|\partial\Gamma_1/\partial T|$ peaks, and each wave follows its right eigenvector with a relative amplitude of $10^{-6}$. Smooth data should converge at second order.

Tests 10 and 11, a shock tube like Sod's and a double shock, use the Helmholtz EOS of [Timmes and Swesty](#timmes-swesty-2000) (2000), common for stellar interiors and supernovae (§4.4). They stay at nonrelativistic sound speeds and where degeneracy does not dominate the pressure, which could then hardly be inverted for the temperature. Along adiabats there $\Gamma_1$ varies little, so that these tests try the code less than the hydrogen ones.

The regression tests of Athena++ run problems 1 to 6 with HLLC on 256 cells, the same problems as MHD, and test 7, each against the exact solution with thresholds on the $L_1$ difference. Further tests check that the general ideal EOS and tables of the ideal gas reproduce the adiabatic EOS on Sod's shock tube for three values of $\gamma$, and that tables of hydrogen match the analytic EOS.

Detail: [Athena 2.2.3](../references/athena-synthesis.md#223-tables-and-the-eos-of-hydrogen), [Athena 2.2.4](../references/athena-synthesis.md#224-tests-of-general-equations-of-state).

## 4. Assessment

Coleman (2020, §5) finds that all tests converge close to linearly, and the linear waves close to quadratically, except the double shocks of hydrogen. A cell that straddles a shock there passes averaged states to the EOS, which give too low a $\Gamma_1$ where it is not monotonic, perhaps a limit of finite volumes without front tracking. The estimate of the wave speeds affects convergence and accuracy substantially, above all in the double shocks: with HLLC the primitive-variable estimate did markedly better than the Roe average, HLLE converged in the double shocks with none of the estimates tried, and those for HLLD need further work. **[GK]** The ideal gas suffices for many astrophysical flows and costs one multiplication per conversion, while a general EOS costs a call of its functions in every cell at every conversion and for every sound speed, with a root finding where it is given in density and temperature and an interpolation where it is tabulated, and a table adds errors and loses accuracy beyond its range. An interface of three functions keeps a general EOS open at the price of a function call where the ideal gas multiplies by $\gamma - 1$. Athena++ refuses reconstruction in characteristic variables with it, although in primitive variables the eigenvectors depend on the EOS only through $c_\mathrm{s}^2$, which the third function supplies. Floors and the dual energy buy robustness at high Mach numbers with conservation, and their use shows only if it is counted. Open are which floors to apply and whether to report them, whether to evolve the internal energy beside the total energy for the supersonic clouds of the production runs, and whether the general EOS enters from the start or later.

## 5. Sources

- <a id="bryan-et-al-1995"></a>Bryan, G. L., Norman, M. L., Stone, J. M., Cen, R. and Ostriker, J. P., A piecewise parabolic method for cosmological hydrodynamics, Computer Physics Communications 89, 149–168 (1995), [doi:10.1016/0010-4655(94)00191-4](https://doi.org/10.1016/0010-4655%2894%2900191-4).
- <a id="chen-et-al-2019"></a>Chen, Z., Coleman, M. S. B., Blackman, E. G. and Frank, A., Solving the Riemann problem for realistic astrophysical fluids, Journal of Computational Physics 388, 490–517 (2019), [doi:10.1016/j.jcp.2019.03.016](https://doi.org/10.1016/j.jcp.2019.03.016).
- <a id="colella-glaz-1985"></a>Colella, P. and Glaz, H. M., Efficient solution algorithms for the Riemann problem for real gases, Journal of Computational Physics 59, 264–289 (1985), [doi:10.1016/0021-9991(85)90146-9](https://doi.org/10.1016/0021-9991%2885%2990146-9).
- <a id="coleman-2020"></a>Coleman, M. S. B., An extension of the Athena++ framework for general equations of state, ApJS 248, 7 (2020), [arXiv:1909.05274](https://arxiv.org/abs/1909.05274), [doi:10.3847/1538-4365/ab82ff](https://doi.org/10.3847/1538-4365/ab82ff).
- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="ryu-jones-1995"></a>Ryu, D. and Jones, T. W., Numerical magnetohydrodynamics in astrophysics: algorithm and tests for one-dimensional flow, ApJ 442, 228 (1995), [doi:10.1086/175437](https://doi.org/10.1086/175437).
- <a id="timmes-swesty-2000"></a>Timmes, F. X. and Swesty, F. D., The accuracy, consistency, and speed of an electron-positron equation of state based on table interpolation of the Helmholtz free energy, ApJS 126, 501–516 (2000), [doi:10.1086/313304](https://doi.org/10.1086/313304).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

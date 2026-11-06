# Diffusion

## 1. Overview

Diffusion moves a quantity down its gradient, with the flux $-\mathcal{D}\nabla\psi$ of Fick's law, which gives the parabolic equation $\partial\psi/\partial t = \nabla\cdot(\mathcal{D}\nabla\psi)$. In astrophysical flows it appears as viscosity, thermal conduction, Ohmic resistivity, ambipolar diffusion and the diffusion of species. It depends on time like advection but couples every cell to every other within a step, without a direction of upwinding, and an explicit step is limited by the square of the cell width. Zingale's text sets out explicit and implicit differencing, pyro solves diffusion and viscous Burgers' equation implicitly with multigrid, and Athena++ adds viscosity, conduction, resistivity, ambipolar diffusion and the diffusion of scalars explicitly in each stage or by super time-stepping. The elliptic solvers follow in topic 14, the implicit radiation of ZEUS in topic 23 and the splitting of processes in topic 18. Anisotropic and saturated conduction are not covered: Athena++ reads anisotropic coefficients without effect, and the Hall effect enters its time step but no electric field.

## 2. Methods

### 2.1 Explicit differencing

The explicit update $(\psi^{n+1}_i - \psi^n_i)/\Delta t = \mathcal{D}(\psi^n_{i+1} - 2\psi^n_i + \psi^n_{i-1})/\Delta x^2$ is of second order in space and first in time ([Zingale's text](#zingale-2025), eqs. 10.6 to 10.9). With $\sigma = \mathcal{D}\,\Delta t/\Delta x^2$, a Fourier mode of phase $\kappa\Delta x$ is multiplied by $1 - 2\sigma(1 - \cos\kappa\Delta x)$ per step, which stays within one in magnitude only for $\sigma \le 1/2$:

$$\Delta t \le \frac{\Delta x^2}{2\mathcal{D}} \ \ \text{in one dimension}, \qquad \Delta t \le \frac{\Delta x^2}{2D\,\mathcal{D}} \ \ \text{in } D \text{ dimensions},$$

the second as Athena++ applies it, with the factors 1/2, 1/4 and 1/6. As $\Delta t \propto \Delta x^2$, the error of first order in time also falls as $\Delta x^2$, whereas advection needs matching orders. A Gaussian stays a Gaussian, of growing width and falling amplitude, which makes the standard test (eq. 10.14). Dirichlet boundaries fix the value, and Neumann boundaries the gradient and so the flux. **[GK]** pyro's documentation gives the explicit limit as a Courant number of 1/2, which holds in one dimension; with the five-point Laplacian on square cells it is 1/4.

Detail: [Zingale 2.7.1](../references/computational-hydrodynamics-synthesis.md#271-the-diffusion-equation), [Zingale 2.7.2](../references/computational-hydrodynamics-synthesis.md#272-explicit-differencing), [pyro 2.7.1](../references/pyro-synthesis.md#271-the-implicit-step), [Athena 2.11.1](../references/athena-synthesis.md#2111-viscosity-thermal-conduction-and-non-ideal-mhd).

### 2.2 Implicit differencing

Evaluating the Laplacian at the new time removes the limit (Zingale's text, eqs. 10.15 to 10.35). Backward Euler is unconditionally stable and of first order, and centring the right-hand side in time gives the second-order Crank–Nicolson method,

$$-\frac{\sigma}{2}\psi^{n+1}_{i+1} + (1 + \sigma)\,\psi^{n+1}_i - \frac{\sigma}{2}\psi^{n+1}_{i-1} = \psi^n_i + \frac{\sigma}{2}\left(\psi^n_{i+1} - 2\psi^n_i + \psi^n_{i-1}\right),$$

a tridiagonal system in one dimension, whose first and last rows carry the boundary conditions. In several dimensions it is the Helmholtz equation $(1 - \tfrac{1}{2}\Delta t\,\mathcal{D}\nabla^2)\,\psi^{n+1} = \psi^n + \tfrac{1}{2}\Delta t\,\mathcal{D}\nabla^2\psi^n$, which multigrid solves without forming the matrix (topic 14). pyro takes this route for its diffusion solver, with a step of $C\min(\Delta x^2, \Delta y^2)/\mathcal{D}$ and $C = 2$ in its test, and for viscous Burgers' equation, which adds the explicit viscous term $\tfrac{1}{2}\Delta t\,\epsilon\nabla^2 q$ to its predicted states before the Crank–Nicolson step. Stability is not accuracy, and a smaller step follows the solution more closely. **[GK]** The amplification factor of Crank–Nicolson, $[1 - \sigma(1 - \cos\kappa\Delta x)]/[1 + \sigma(1 - \cos\kappa\Delta x)]$, tends to $-1$ for the shortest modes at large $\sigma$, which then flip sign every step and decay slowly: the method is A-stable but not L-stable, whereas backward Euler damps these modes strongly.

Detail: [Zingale 2.7.3](../references/computational-hydrodynamics-synthesis.md#273-implicit-differencing), [Zingale 2.7.4](../references/computational-hydrodynamics-synthesis.md#274-multigrid-for-implicit-diffusion), [pyro 2.3.2](../references/pyro-synthesis.md#232-the-viscous-solver), [pyro 2.7.1](../references/pyro-synthesis.md#271-the-implicit-step).

### 2.3 Variable and nonlinear coefficients

A coefficient that varies in space enters through the fluxes on the faces, with $\mathcal{D}_{i+1/2}$ the arithmetic mean $\tfrac{1}{2}(\mathcal{D}_i + \mathcal{D}_{i+1})$ or the harmonic mean, as the physics suggests (Zingale's text, eqs. 10.36 to 10.42). A coefficient that depends on $\psi$, as a conductivity on the temperature, makes Crank–Nicolson nonlinear, and a predictor and corrector keeps second order.

1. Diffuse with $\mathcal{D}(\psi^n)$ for a provisional $\psi^\star$.
2. Diffuse again with $\mathcal{D}(\psi^\star)$ in the term at the new time for $\psi^{n+1}$, after [Bell et al.](#bell-et-al-2004a) (2004).

In hydrodynamics conduction acts on the temperature while the code evolves the internal energy. With $e(\rho, T)$, $c_v = \partial e/\partial T|_\rho$ and $e_\rho = \partial e/\partial\rho|_T$, the chain rule gives $\nabla T = (\nabla e - e_\rho\nabla\rho)/c_v$, so that the advective terms are taken explicitly and the diffusion of $e$ implicitly (eqs. 10.43 to 10.47).

Detail: [Zingale 2.7.5](../references/computational-hydrodynamics-synthesis.md#275-non-constant-conductivity), [Zingale 2.7.6](../references/computational-hydrodynamics-synthesis.md#276-diffusion-in-hydrodynamics).

### 2.4 Physical diffusion in MHD

Athena++ adds isotropic viscosity, conduction, Ohmic resistivity and ambipolar diffusion to the fluxes of MHD ([Stone et al.](#stone-et-al-2020) 2020, eqs. 6 and 7). The momentum flux loses the viscous stress

$$\Pi_{ij} = \rho\nu\left(\frac{\partial v_i}{\partial x_j} + \frac{\partial v_j}{\partial x_i} - \frac{2}{3}\delta_{ij}\nabla\cdot\mathbf{v}\right),$$

the energy flux gains $-\Pi\cdot\mathbf{v}$, the heat flux $-\rho\kappa_\mathrm{T}\nabla T$ with $T = p/\rho$ and the thermal diffusivity $\kappa_\mathrm{T}$, and the Poynting fluxes of the electric fields $\eta_\mathrm{O}\mathbf{J}$ and $\eta_\mathrm{AD}\mathbf{J}_\perp$, with $\mathbf{J} = \nabla\times\mathbf{B}$ and $\mathbf{J}_\perp$ its part perpendicular to $\mathbf{B}$, which also join the electric fields of constrained transport (topic 11). The fluxes come from differences of second order on the faces, with the density and the coefficient averaged there, and enter as divergences, which conserves momentum, energy and magnetic flux. By default they are integrated explicitly and unsplit in every stage of the integrator, at its order in time, the most accurate choice. The coefficients are constant unless a problem enrols functions of position and state, and the diffusion of passive scalars, with the flux $-\nu_\mathrm{s}\bar\rho\nabla C$ of the concentration $C$, follows the same pattern (topic 21).

Detail: [Athena 2.1.2](../references/athena-synthesis.md#212-non-ideal-mhd-in-athena), [Athena 2.11.1](../references/athena-synthesis.md#2111-viscosity-thermal-conduction-and-non-ideal-mhd), [Athena 2.12.2](../references/athena-synthesis.md#2122-diffusion-and-tests).

### 2.5 Super time-stepping

The Runge–Kutta–Legendre methods of [Meyer, Balsara and Aslam](#meyer-et-al-2012) (2012, [2014](#meyer-et-al-2014)) advance the diffusion over a super step $\Delta\tau$ in $s$ explicit stages, which together reach $O(s^2)$ explicit steps:

$$\Delta\tau \le \Delta t_\mathrm{par}\,\frac{s^2 + s}{2} \ \ \text{(RKL1)}, \qquad \Delta\tau \le \Delta t_\mathrm{par}\,\frac{s^2 + s - 2}{4} \ \ \text{(RKL2)},$$

with $\Delta t_\mathrm{par}$ the explicit limit. Each stage of RKL1 combines the two before with the diffusive operator $M$, $Y_j = \mu_jY_{j-1} + (1 - \mu_j)\,Y_{j-2} + \tilde\mu_j\,\Delta\tau\,M(Y_{j-1})$ with $\mu_j = (2j - 1)/j$ and $\tilde\mu_j = 2\mu_j/(s^2 + s)$, and RKL2 adds terms in the initial state. Athena++ splits the diffusion off the MHD: RKL1 advances it by the whole step before the main integrator, and RKL2, the default, by half the step before and half after, with $s$ the smallest odd number that covers the step. The time step of the MHD then ignores the diffusive limit, unless a ratio caps it. **[GK]** The stages of these methods follow the recursion of Legendre polynomials, which keeps the amplification bounded over the long interval of the negative real axis that the stages cover.

Detail: [Athena 2.11.1](../references/athena-synthesis.md#2111-viscosity-thermal-conduction-and-non-ideal-mhd), [Athena 2.11.2](../references/athena-synthesis.md#2112-super-time-stepping).

## 3. Tests

A Gaussian diffused from a finite width checks the order of convergence, as its analytic solution is known in any number of dimensions. Zingale's text runs it on 64 cells with explicit, backward Euler and Crank–Nicolson steps at Courant numbers from 0.8 to 10, and on $128^2$ cells with Crank–Nicolson and multigrid. pyro runs it at $C = 2$ on $128^2$ cells, and Athena++ diffuses Gaussians of velocity, field and scalar concentration explicitly and with super time-stepping, its regression tests requiring orders of at least 1.99, or 0.99 for RKL1.

Athena++ damps a linear fast wave oblique to the grid by viscosity, resistivity and conduction at Reynolds numbers from 134 to 13,452 and fits the decay rate against that of [Ryu, Jones and Frank](#ryu-et-al-1995) (1995). An oblique C-shock of ambipolar diffusion with an adiabatic gas, after [Masson et al.](#masson-et-al-2012) (2012), tests the heating and energy flux of that term against its analytic profile.

Detail: [Zingale 2.7.2](../references/computational-hydrodynamics-synthesis.md#272-explicit-differencing), [Zingale 2.7.4](../references/computational-hydrodynamics-synthesis.md#274-multigrid-for-implicit-diffusion), [pyro 2.7.2](../references/pyro-synthesis.md#272-problems-and-tests), [Athena 2.11.1](../references/athena-synthesis.md#2111-viscosity-thermal-conduction-and-non-ideal-mhd), [Athena 2.11.2](../references/athena-synthesis.md#2112-super-time-stepping), [Athena 2.12.2](../references/athena-synthesis.md#2122-diffusion-and-tests).

## 4. Assessment

The explicit method follows the Gaussian at $\mathcal{C} = 0.8$, converges as $\Delta x^2$ once the initial data are resolved, and is unstable beyond $\mathcal{C} = 1$, in the units of eq. 10.9. Crank–Nicolson is the most accurate at $\mathcal{C} = 0.8$ and an order of magnitude better than backward Euler at $\mathcal{C} = 8$ on fine grids, but oscillates for under-resolved data at $\mathcal{C} = 10$, where codes often fall back on backward Euler. pyro's Gaussian agrees excellently with the analytic solution. The decay rates of Athena++ converge to the analytic ones, those of RK3 with PPM much faster than VL2 with PLM, at second order until the initial data, an eigenmode of ideal MHD, limit the error near $10^{-4}$, and the C-shock matches its profile even at low resolution. Super time-stepping gives speed-ups of about $s$. **[GK]** Explicit diffusion is simple, conservative and accurate while the diffusive time across a cell exceeds the hydrodynamic step, but thermal conduction in hot, tenuous gas, with a conductivity that grows steeply with temperature, can be orders of magnitude faster and cripple the step. Super time-stepping keeps the explicit, conservative fluxes at a cost of about the square root of the ratio of the limits, while implicit methods need a global solve per step and, for nonlinear coefficients, iteration. Open are which of the two suits the conduction of the production runs, how saturated and anisotropic conduction along the field, which no reference provides, would enter, and whether diffusion is split from the MHD or kept in its stages.

## 5. Sources

- <a id="bell-et-al-2004a"></a>Bell, J. B., Day, M. S., Rendleman, C. A., Woosley, S. E. and Zingale, M. A., Adaptive low Mach number simulations of nuclear flame microphysics, Journal of Computational Physics 195, 677–694 (2004), [doi:10.1016/j.jcp.2003.10.035](https://doi.org/10.1016/j.jcp.2003.10.035).
- <a id="masson-et-al-2012"></a>Masson, J., Teyssier, R., Mulet-Marquis, C., Hennebelle, P. and Chabrier, G., Incorporating ambipolar and Ohmic diffusion in the AMR MHD code RAMSES, ApJS 201, 24 (2012), [doi:10.1088/0067-0049/201/2/24](https://doi.org/10.1088/0067-0049/201/2/24).
- <a id="meyer-et-al-2012"></a>Meyer, C. D., Balsara, D. S. and Aslam, T. D., A second-order accurate super timestepping formulation for anisotropic thermal conduction, MNRAS 422, 2102–2115 (2012), [doi:10.1111/j.1365-2966.2012.20744.x](https://doi.org/10.1111/j.1365-2966.2012.20744.x).
- <a id="meyer-et-al-2014"></a>Meyer, C. D., Balsara, D. S. and Aslam, T. D., A stabilized Runge–Kutta–Legendre method for explicit super-time-stepping of parabolic and mixed equations, Journal of Computational Physics 257, 594–626 (2014), [doi:10.1016/j.jcp.2013.08.021](https://doi.org/10.1016/j.jcp.2013.08.021).
- <a id="ryu-et-al-1995"></a>Ryu, D., Jones, T. W. and Frank, A., Numerical magnetohydrodynamics in astrophysics: algorithm and tests for multidimensional flow, ApJ 452, 785 (1995), [doi:10.1086/176347](https://doi.org/10.1086/176347).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

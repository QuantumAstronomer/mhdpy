# Particles

## 1. Overview

Lagrangian particles move through the grid with velocities interpolated from the gas. Tracers follow the flow without mass, while solids such as dust feel the drag of the gas and push back on it. Each particle of solids stands for a swarm of real ones, a superparticle, so that a distribution of sizes or a largely collisionless population can be followed where a fluid of dust would fail. pyro moves massless tracers by a midpoint method, and Athena couples particles to the gas by drag, with a predictor and corrector that conserves momentum exactly and integrators of particles that are semi-implicit or fully implicit ([Bai and Stone](#bai-stone-2010) 2010). The copy of Athena++ has no module of particles, and Ulula, ZEUS and Zingale's text treat none. The shearing box in which the particles of Athena are tested follows in topic 24.

## 2. Methods

### 2.1 Tracer particles

pyro's tracers carry a position and a velocity and keep their initial positions, which colour them in plots and are written with the current ones. They start at random positions over the domain, on a regular array, or at given positions. After each update of the gas, a step moves every tracer by the midpoint method.

1. Interpolate the velocity of the gas bilinearly from the four nearest cell centres to the tracer, with one ghost cell.
2. Move the tracer by half a step with this velocity, and interpolate the velocity at the new position.
3. Move the tracer by a full step from its start with that velocity.
4. Remove it at outflow boundaries, wrap it round at periodic ones, and mirror it at reflecting ones.

The velocities are those of the grid at the time of the step. The solvers of advection, Burgers' equation, shallow water and incompressible flow carry tracers. **[GK]** Within half a cell of the lower boundaries, the interpolation takes cells one place too far in, and at version 4.5.1 the compressible solvers stop when tracers are switched on, since they pass their parameters where the number of tracers belongs.

Detail: [pyro 2.10.1](../references/pyro-synthesis.md#2101-generation-and-motion), [pyro 2.10.2](../references/pyro-synthesis.md#2102-use-in-the-solvers-and-tests).

### 2.2 Drag and feedback

Particle $i$ relaxes towards the velocity of the gas on the stopping time $t_\mathrm{stop}$, while the gas receives the opposite momentum (Bai and Stone 2010, eqs. 1 to 6):

$$\frac{d\mathbf{v}_i}{dt} = \mathbf{a}_i - \frac{\mathbf{v}_i - \mathbf{v}(\mathbf{x}_i)}{t_\mathrm{stop}}, \qquad \frac{\partial(\rho\mathbf{v})}{\partial t} + \nabla\cdot(\rho\mathbf{v}\mathbf{v} + p\mathsf{I}) = \rho\mathbf{g} + \frac{\rho_\mathrm{p}(\bar{\mathbf{v}}_\mathrm{p} - \mathbf{v})}{t_\mathrm{stop}}.$$

Here $\mathbf{a}_i$ and $\mathbf{g}$ are the accelerations of particle and gas by forces other than drag, $\rho_\mathrm{p}$ is the density of the particles and $\bar{\mathbf{v}}_\mathrm{p}$ their mean velocity, weighted by mass, in a fluid element. For particles smaller than the mean free path of the gas, in the regime of Epstein, $t_\mathrm{stop} = \rho_\mathrm{s}a/(\rho c_\mathrm{s})$ for the material density $\rho_\mathrm{s}$ and radius $a$ of a sphere, and $\Omega t_\mathrm{stop}$, with the orbital frequency $\Omega$, measures the coupling in a disc. The code admits any number of species, each with a stopping time of its own. In a shearing box, whose periodic radial boundaries forbid a radial gradient of pressure, a constant inward force on the particles replaces that gradient and leaves the integrator of the gas unchanged (topic 24).

Detail: [Athena 2.13.1](../references/athena-synthesis.md#2131-particles-coupled-to-the-gas-by-drag).

### 2.3 The hybrid predictor and corrector

The particles join the CTU integrator of Athena (topic 8), and their feedback enters the gas as a source term, with the transverse fluxes and the continuity equation unchanged (Bai and Stone 2010, §2.2). The weight function of the triangular-shaped cloud interpolates the gas to a particle and distributes its feedback to the grid. It is continuous and non-negative, whereas the cloud in cell is noisy and inaccurate and a quadratic polynomial discontinuous. A step runs as follows.

1. Predict the momentum of the gas at the half step from its other forces and the feedback $\Delta\mathbf{p}^\mathrm{pred}_i = m_i(\mathbf{v}_i - \mathbf{v})\,\Delta t/[2\max(t_\mathrm{stop}, \Delta t)]$ of each particle of mass $m_i$, which also corrects the velocities of the interface states between the two steps of CTU.
2. Advance each particle over the full step with the gas of the half step, interpolated to the particle (2.4).
3. Correct the momentum of the gas over the full step with the change of momentum of each particle less the impulse of its other forces, evaluated at the midpoint of its old and new positions, and distribute it from there.

The predictor is of first order for $t_\mathrm{stop} \le \Delta t$ and balances an equilibrium exactly otherwise, and the corrector conserves momentum exactly without evaluating the stiff drag. With an energy equation, each particle would deposit the heat of friction as $(\Delta p_i)^2t_\mathrm{stop}/(m_i\Delta t^2)$, which avoids the stiffness of $1/t_\mathrm{stop}$. The explicit feedback can turn unstable where particles dominate the mass: once $\sum_k(\rho_{\mathrm{p},k}/\rho)\,\Delta t/\max(t_{\mathrm{stop},k}, \Delta t)$ over the species $k$ exceeds about 3 to 5, both velocities can grow without physical cause. Athena can raise the stopping times where this sum is large, as the Pencil Code does, but leaves this off in practice, since the dust of a disc holds about one per cent of its mass; a reduced feedback of the predictor would also restore stability, at the price of first order. **[GK]** As the corrector is the impulse of drag on the particle, the gas must receive its negative, the sign that the predictor carries, whereas the paper adds it.

Detail: [Athena 2.13.1](../references/athena-synthesis.md#2131-particles-coupled-to-the-gas-by-drag).

### 2.4 The integrators of particles

Both integrators of particles are of second order and take the gas of the half step (Bai and Stone 2010, §3). The semi-implicit one follows Crank and Nicolson as a leapfrog of the form drift–kick–drift.

1. Drift by half a step, $\mathbf{x}' = \mathbf{x}^n_i + \tfrac{1}{2}\Delta t\,\mathbf{v}^n_i$.
2. Kick with the right-hand side $\dot{\mathbf{v}}_i$ of the equation of motion, drag included, at the mean of the old and new velocities and at $\mathbf{x}'$, $\mathbf{v}^{n+1}_i = \mathbf{v}^n_i + \Delta t\,\dot{\mathbf{v}}_i[\tfrac{1}{2}(\mathbf{v}^n_i + \mathbf{v}^{n+1}_i), \mathbf{x}']$, solved in closed form with its Jacobian.
3. Drift by another half step with the new velocity, and shift the position by the shear of the orbital motion.

It keeps the geometry of orbits without drag and is safe for $t_\mathrm{stop} \gtrsim 0.2\Delta t$, but for $t_\mathrm{stop} \ll \Delta t$ it leaves a difference between the velocities of particle and gas undamped. The fully implicit integrator, $\mathbf{y}^{n+1} = \mathbf{y}^n + \tfrac{1}{2}\Delta t\,\mathbf{R}(\mathbf{y}^{n+1}) + \tfrac{1}{2}\Delta t\,\mathbf{R}[\mathbf{y}^{n+1} - \Delta t\,\mathbf{R}(\mathbf{y}^{n+1})]$ for $d\mathbf{y}/dt = \mathbf{R}(\mathbf{y})$, is stable for any $t_\mathrm{stop} > 0$ but loses the geometry of orbits without drag. It therefore serves the particles with $t_\mathrm{stop} \lesssim \Delta t$, and the semi-implicit one all others. The approximation of short friction times of [Johansen and Klahr](#johansen-klahr-2005) (2005), which moves particles at their terminal velocity, is not implemented.

Detail: [Athena 2.13.2](../references/athena-synthesis.md#2132-the-integrators-of-particles).

## 3. Tests

pyro's unit tests check a single particle, the three ways of placing particles, motion at uniform velocity through periodic boundaries, and reflecting and outflow boundaries with velocities uniform in the four triangles between the diagonals of the domain. As the velocities are uniform near the particles, they cannot see the error of the interpolation near the lower boundaries. No test measures the order of the motion.

Without drag, a particle in the shearing sheet follows an epicycle of known energy. Bai and Stone (2010) follow one of amplitude 0.4 with a step of $0.4/\Omega$, large enough to show the errors, by both integrators and by an explicit one after the modified Euler method. The test measures the conservation of energy and the closure of the orbit.

Particles spread uniformly in a uniform gas, with drag and feedback, travel an analytic distance in the frame of zero total momentum. With fixed steps, $\rho_\mathrm{p}/\rho = 1$ and $t_\mathrm{stop} = 2$, the test measures the order of the hybrid scheme and the conservation of momentum. At $\Delta t = 1$ with $t_\mathrm{stop} = 0.2$ or 0.02, it shows how each integrator damps a drag that the step does not resolve.

The growing modes of the streaming instability of [Youdin and Johansen](#youdin-johansen-2007) (2007), on the equilibrium of solids and gas in an unstratified Keplerian disc, are the most stringent test. One particle per cell, shifted radially, seeds a mode of amplitude $10^{-6}$ in a periodic box of one wavelength. The modes linA and linB, with $\Omega t_\mathrm{stop} = 0.1$ and $\rho_\mathrm{p}/\rho$ of 3 and 0.2, grow at $0.4190204\Omega$ and $0.015476\Omega$, and two further modes test $\Omega t_\mathrm{stop}$ of 0.01 and 0.001. Their growth is measured on 16 to 128 cells per wavelength.

Runs in the radial–vertical plane repeat the saturated runs AB and BA of [Johansen and Youdin](#johansen-youdin-2007) (2007), with $\Omega t_\mathrm{stop}$ of 0.1 and 1, on $64^2$ to $2048^2$ cells with nine particles per cell, and on $256^2$ cells with 1 to 25 particles per cell. They measure the clumping of particles by the cumulative distribution of the density around each particle, the turbulence of the gas, and the radial drift and the diffusion of the particles.

Detail: [pyro 2.10.2](../references/pyro-synthesis.md#2102-use-in-the-solvers-and-tests), [Athena 2.13.3](../references/athena-synthesis.md#2133-tests-of-the-particle-method), [Athena 2.13.4](../references/athena-synthesis.md#2134-convergence-of-the-streaming-instability).

## 4. Assessment

The semi-implicit integrator conserves the energy of the epicycle exactly, with the shift by the orbital motion, and its orbit closes with an error of phase that falls as $\Delta t^2$, while the explicit integrator gains energy and the fully implicit one loses it and spirals inwards (Bai and Stone 2010). The hybrid scheme converges at second order in the test of drag, with momentum conserved to round-off. With unresolved drag, the fully implicit integrator damps the velocity by a factor of about $2(t_\mathrm{stop}/\Delta t)^2$ per step, while the semi-implicit one lets it oscillate with a factor of about $-(1 - 4t_\mathrm{stop}/\Delta t)$. The mode linA approaches its growth rate closely from 16 cells per wavelength on, linB needs about 64, and the modes of shorter stopping times about 128, rates close to those of other Godunov codes but less accurate than those of the Pencil Code of sixth order. In the saturated runs the gas converges at modest resolution but the clumping only on $512^2$ cells for AB and apparently $1024^2$ for BA, one particle per cell suffices, and the diffusion of particles is uncertain by about 20 per cent, in agreement with the Pencil Code. **[GK]** Tracers cost little and record the history of fluid elements without the numerical diffusion of a scalar (topic 21), which suits the diagnosis of mixing in the production runs, provided they are interpolated correctly near boundaries. Particles of dust lie in the eventual scope of mhdpy. The scheme of Bai and Stone ties its predictor to the half step of CTU, so that an integrator by the method of lines (topic 8) needs another placement of the feedback, which the references do not show. In Python, interpolation and deposition must be vectorised over the particles, for instance by sorting them by cell and accumulating with counts per cell, and their cost per particle then enters the rate of cell updates. Open are whether tracers enter with the first layers, which weight function serves both interpolation and deposition, and how the feedback enters the stages of the integrator.

## 5. Sources

- <a id="bai-stone-2010"></a>Bai, X.-N. and Stone, J. M., Particle-gas dynamics with Athena: method and convergence, ApJS 190, 297–310 (2010), [arXiv:1005.4980](https://arxiv.org/abs/1005.4980), [doi:10.1088/0067-0049/190/2/297](https://doi.org/10.1088/0067-0049/190/2/297).
- <a id="johansen-klahr-2005"></a>Johansen, A. and Klahr, H., Dust diffusion in protoplanetary disks by magnetorotational turbulence, ApJ 634, 1353–1371 (2005), [doi:10.1086/497118](https://doi.org/10.1086/497118).
- <a id="johansen-youdin-2007"></a>Johansen, A. and Youdin, A., Protoplanetary disk turbulence driven by the streaming instability: nonlinear saturation and particle concentration, ApJ 662, 627–641 (2007), [doi:10.1086/516730](https://doi.org/10.1086/516730).
- <a id="youdin-johansen-2007"></a>Youdin, A. and Johansen, A., Protoplanetary disk turbulence driven by the streaming instability: linear evolution and numerical methods, ApJ 662, 613–626 (2007), [doi:10.1086/516729](https://doi.org/10.1086/516729).

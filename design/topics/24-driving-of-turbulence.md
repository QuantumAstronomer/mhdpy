# The driving of turbulence

## 1. Overview

Athena++ alone among the references drives turbulence, by random perturbations of the velocity with a power-law spectrum, built in Fourier space with its FFT driver of self-gravity and subject to its restrictions on the mesh. The turbulence may decay from one perturbation, be driven by impulses at fixed intervals or continuously before every step. FFTs follow in topic 13 and the driver of a step in topic 33.

## 2. Methods

### 2.1 The spectrum of the forcing

Each component of the forcing $\mathbf{f}$ receives, at every wavevector $\mathbf{k}$ in a shell between two cut-offs, a random complex amplitude, a normally distributed number times a phase factor of uniform phase, scaled by $|\mathbf{k}|^{-(\alpha+2)/2}$, with $\alpha = 2$ by default and the mode $\mathbf{k} = 0$ empty. A weight $f_\mathrm{shear}$ between 0 and 1 splits the forcing into its compressive part $\hat{\mathbf{k}}(\hat{\mathbf{k}}\cdot\mathbf{f})$ and its solenoidal remainder and recombines them with the weights $1 - f_\mathrm{shear}$ and $f_\mathrm{shear}$; by default the forcing is kept as drawn. In the driven modes, a correlation time $t_\mathrm{corr}$ evolves the amplitudes by an Ornstein–Uhlenbeck process after [Lynn et al.](#lynn-et-al-2012) (2012, eq. 26):

$$\mathbf{f} \to e^{-\Delta t/t_\mathrm{corr}}\,\mathbf{f} + (1 - e^{-2\Delta t/t_\mathrm{corr}})^{1/2}\,\mathbf{f}',$$

with a freshly drawn field $\mathbf{f}'$ and $\Delta t$ the step or the interval of the impulses. Without a correlation time each perturbation is drawn afresh. The inverse transform gives the perturbation $\delta\mathbf{v}$ of the velocity, of which the driver keeps the real part. **[GK]** As the number of wavevectors in a shell of radius $k$ grows as $k^2$ in three dimensions, the energy spectrum of the forcing falls off as $k^{-\alpha}$.

Detail: [Athena 2.15.4](../references/athena-synthesis.md#2154-the-driving-of-turbulence).

### 2.2 Applying the forcing

The main loop applies the forcing before the integrator, outside every task list.

1. Remove the mass-weighted mean of $\delta\mathbf{v}$, so that the forcing adds no net momentum.
2. Find the factor $s$ that raises the kinetic energy of the domain by the chosen $\Delta E$, the positive root of $\tfrac{1}{2}s^2\sum\rho|\delta\mathbf{v}|^2 + s\sum\rho\mathbf{v}\cdot\delta\mathbf{v} = \Delta E/\Delta V$ over the cells of volume $\Delta V$, in a form free of cancellation.
3. Add $s\rho\,\delta\mathbf{v}$ to the momentum and, with an equation of state that is not barotropic, the corresponding kinetic energy to the total energy.

$\Delta E$ is a chosen energy in the decaying mode, and a rate of injection times the interval of the impulses or the step in the driven ones. The perturbation changes only the conserved variables of the active cells, so that the first stage of the step computes its fluxes from primitive variables and ghost cells of the state before it. By default each process draws the amplitudes of its own block of the FFT, so that the forcing depends on the decomposition; a fixed seed makes every process run through one sequence over all wavevectors, independent of the numbers of processes and cells, at a much higher cost. Restart files keep neither the amplitudes nor the time of the next impulse, and the driver assumes a three-dimensional mesh without checking it.

Detail: [Athena 2.15.4](../references/athena-synthesis.md#2154-the-driving-of-turbulence).

## 3. Tests

The problem of turbulence starts from a uniform gas at rest and lets turbulence decay on $32^3$ cells. The regression drives turbulence continuously with a fixed seed on $64 \times 32 \times 32$ cells in blocks of $16^3$ to $t = 0.3$, once serially and with one, two and four processes. It requires the history of the kinetic energy of each parallel run to differ from the serial one by less than $10^{-7}$, summed over the history, which tests the independence of the forcing from the decomposition.

Detail: [Athena 2.15.4](../references/athena-synthesis.md#2154-the-driving-of-turbulence).

## 4. Assessment

The references report no statistics of driven turbulence, only the agreement of the regression. **[GK]** Forcing in Fourier space with a chosen spectrum, ratio of compressive to solenoidal power and correlation time is the standard of studies of turbulence, and in Python it needs only the FFT of NumPy, without a further library. Applied outside the stages and without updating the primitive variables, the forcing enters the first stage inconsistently, which costs accuracy in time but not the statistics of a steady state. A forcing that depends on the decomposition makes runs irreproducible across machines, which the seeded mode avoids at a cost. The production runs drive no turbulence, which lies in the eventual scope for the interstellar medium. Open are whether the forcing becomes a source term within the stages, and how its random state enters restart files.

## 5. Sources

- <a id="lynn-et-al-2012"></a>Lynn, J. W., Parrish, I. J., Quataert, E. and Chandran, B. D. G., Resonance broadening and heating of charged particles in magnetohydrodynamic turbulence, ApJ 758, 78 (2012), [doi:10.1088/0004-637X/758/2/78](https://doi.org/10.1088/0004-637X/758/2/78).

# Reactions, chemistry and cooling

## 1. Overview

Reactions, chemistry and cooling change the composition and the internal energy of the gas within each cell, at rates set by the local density, temperature and abundances, and often on time scales far shorter than those of the flow. They add sources to the equations of the species and the energy, and their integration over a step solves stiff ordinary differential equations in every cell. Zingale's text sets out the equations of reactive flow, the integration of stiff systems and the structure of flames, and Athena++ integrates networks of interstellar chemistry with their heating and cooling. pyro's reacting solver holds only an outline of its burning, and neither Ulula nor ZEUS treats reactions. Among pyro, Ulula, ZEUS and Athena++, radiative cooling enters only through the networks of Athena++, while Athena in the simulations of 2016 and AthenaPK add the cooling functions of an optically thin plasma, which follow in [topic 20](20-radiative-cooling.md). The splitting from the hydrodynamics follows in [topic 18](18-operator-splitting-and-coupling-of-processes.md), the advection of species in [topic 21](21-passive-scalars.md) and radiation in [topic 23](23-radiation-transport.md).

## 2. Methods

### 2.1 The equations of reactive flow

Each species obeys a continuity equation, and with the mass fractions $X_s = \rho_s/\rho$ of the species $s$, of partial densities $\rho_s$, which sum to one, reactions enter as creation rates $\dot{\omega}_s$ with $\sum_s\dot{\omega}_s = 0$ ([Zingale's text](#zingale-2025), eqs. 12.1 to 12.6). The partial densities sum to the continuity equation, so that solving both over-specifies the system. The energy released per unit mass and time, $H_\mathrm{nuc}$, and thermal conduction add to the energy equation (eqs. 12.10 to 12.13):

$$\frac{\partial(\rho X_s)}{\partial t} + \nabla\cdot(\rho X_s\mathbf{v}) = \rho\dot{\omega}_s, \qquad \frac{\partial E}{\partial t} + \nabla\cdot[(E + p)\mathbf{v}] = \nabla\cdot(\kappa\nabla T) + \rho H_\mathrm{nuc},$$

with the conductivity $\kappa$.

The primitive system, from which face states are predicted ([topic 8, §2.2](08-time-integration.md#22-predictorcorrector-schemes-in-one-dimension)), gains a source proportional to the heating in the pressure equation, through derivatives of the equation of state, and $\dot{\omega}_s$ in the advection of $X_s$ (eqs. 12.14 to 12.29).

Detail: [Zingale 2.8.4](../references/computational-hydrodynamics-synthesis.md#284-reactive-hydrodynamics), [Zingale 2.8.5](../references/computational-hydrodynamics-synthesis.md#285-the-pressure-and-temperature-equations).

### 2.2 Stiff integration

Within a cell, the reactions form a system $d\mathbf{y}/dt = \mathbf{R}(\mathbf{y})$ for the abundances and the energy. It is stiff when its solutions change on widely different time scales, usually marked by a large spread in the eigenvalues of the Jacobian $\mathsf{J} = \partial\mathbf{R}/\partial\mathbf{y}$ (Zingale's text, §1.2.5). Explicit methods, such as Euler's or the classical Runge–Kutta method of fourth order, are simpler and cheaper per step, while implicit methods suit stiff systems. Backward Euler, $\mathbf{y}^{n+1} = \mathbf{y}^n + \Delta t\,\mathbf{R}(\mathbf{y}^{n+1})$, is solved by Newton iteration.

1. Start from the guess $\mathbf{y}^\star = \mathbf{y}^n$.
2. Solve $(\mathsf{I} - \Delta t\,\mathsf{J})\,\Delta\mathbf{y} = \mathbf{y}^n - \mathbf{y}^\star + \Delta t\,\mathbf{R}(\mathbf{y}^\star)$, with the Jacobian at the current iterate $\mathbf{y}^\star$, and replace $\mathbf{y}^\star$ by $\mathbf{y}^\star + \Delta\mathbf{y}$.
3. Stop once the correction is small against $\mathbf{y}^n$, and take $\mathbf{y}^{n+1} = \mathbf{y}^\star$.

A cheaper approximation to the Jacobian may suffice. Networks of nuclear reactions need such integrators ([Timmes](#timmes-1999) 1999), for instance VODE of [Brown, Byrne and Hindmarsh](#brown-et-al-1989) (1989), which takes a routine for the rates and one for the Jacobian, possibly by finite differences. Athena++ offers the external library CVODE, with relative and absolute tolerances, limits on the number of steps and the order, and an optional Jacobian from the network, or a forward Euler scheme of its own. The latter takes substeps of a set fraction of the shortest time in which an abundance or the internal energy would change by its own value at its current rate, with the abundances floored, up to a maximum number of substeps.

Detail: [Zingale 2.1.7](../references/computational-hydrodynamics-synthesis.md#217-ordinary-differential-equations), [Zingale 2.8.7](../references/computational-hydrodynamics-synthesis.md#287-reaction-networks-and-burning-modes), [Athena 2.15.3](../references/athena-synthesis.md#2153-chemistry).

### 2.3 The reactive step

Split from the hydrodynamics ([topic 18, §2.1](18-operator-splitting-and-coupling-of-processes.md#21-strang-splitting)), the reactive step integrates $dX_s/dt = \dot{\omega}_s$ and $d(\rho e)/dt = \rho H_\mathrm{nuc}$ in each cell, closed by the equation of state, since the rates depend on $\rho$, $T$ and $X_s$ (Zingale's text, eqs. 12.43 to 12.45). The temperature then follows $c_v\,dT/dt = H_\mathrm{nuc}$ or $c_p\,dT/dt = H_\mathrm{nuc}$, with the specific heat $c_v$ at constant volume or $c_p$ at constant pressure according to the effects to capture, a choice that arises because the step leaves out the hydrodynamic terms. Many codes neglect the change of the temperature during the step ([Fryxell et al.](#fryxell-et-al-2000) 2000). Athena++ integrates its networks in each cell over the whole step in the last stage of its integrator, with the abundances held in its first passive scalars, one per species ([topic 21, §2.1](21-passive-scalars.md#21-equations-and-variables)). pyro's reacting solver carries partial densities of fuel and ash as passive scalars, but its functions for burning and diffusion hold only comments.

Detail: [Zingale 2.8.7](../references/computational-hydrodynamics-synthesis.md#287-reaction-networks-and-burning-modes), [pyro 2.4.11](../references/pyro-synthesis.md#2411-reactions), [Athena 2.15.3](../references/athena-synthesis.md#2153-chemistry).

### 2.4 Interstellar chemistry with heating and cooling

Athena++ chooses its network at configuration: the network of hydrogen and carbon of [Gong, Ostriker and Wolfire](#gong-et-al-2017) (2017) with 12 species, a network of molecular hydrogen with two, a general network read in the format of the KIDA database, or the eight species of the shock tube with chemistry of [Grassi et al.](#grassi-et-al-2014) (2014). Each network supplies the rates of the abundances and, optionally, of the internal energy by heating and cooling, with the shielding of molecules, from parameters that include, for the network of Gong, Ostriker and Wolfire, the metallicity, the abundances of the elements and limits in temperature. Radiation drives the photochemistry, either constant, as the problem sets it, or attenuated along six rays.

1. Before each step, accumulate the column densities along $\pm x$, $\pm y$ and $\pm z$, passed from block to block by a boundary class and a task list of their own.
2. In every cell, attenuate the field incident on each face of the domain by the extinction of dust and, for the photodissociation of $\mathrm{H_2}$ and CO and the photoionisation of C, by shielding.
3. Optionally scale the rate of ionisation by cosmic rays by $N_0/N$ for a column density $N$ beyond $N_0 = 9.35 \times 10^{20}\,\mathrm{cm^{-2}}$.

Detail: [Athena 2.15.3](../references/athena-synthesis.md#2153-chemistry).

### 2.5 Flames

A deflagration, or flame, advances below the speed of sound by the balance of diffusion and reactions: conduction heats the fuel ahead of it to ignition, and the energy released keeps the ash hot (Zingale's text, §12.3.2). Equating the time of diffusion over a width $\ell_\mathrm{f}$, $\ell_\mathrm{f}^2/\mathcal{D}$ with $\mathcal{D} = \kappa/(\rho c_p)$, to the time of burning, $t_\mathrm{burn} = c_pT/H_\mathrm{nuc}$, gives the thickness $\ell_\mathrm{f} \sim (\kappa T/\rho H_\mathrm{nuc})^{1/2}$ and the speed $v_\mathrm{f} \sim \ell_\mathrm{f}/t_\mathrm{burn}$, which scale as $\sqrt{\kappa/H_\mathrm{nuc}}$ and $\sqrt{\kappa H_\mathrm{nuc}}$ (eqs. 12.46 to 12.53). Detonations, convective burning and explicit diffusion within the reactive step are headings without text. **[GK]** The speed of eq. 12.52 lacks a factor $c_p$ in its denominator, without which it does not have the units of a speed.

Detail: [Zingale 2.8.7](../references/computational-hydrodynamics-synthesis.md#287-reaction-networks-and-burning-modes).

## 3. Tests

Athena++ tests each network by regression. A uniform medium with the network of molecular hydrogen, integrated by forward Euler, must follow the analytic approach of atomic hydrogen to its equilibrium between the destruction of $\mathrm{H_2}$ by cosmic rays and its formation on grains within a relative error of $10^{-2}$. An advected, reacting Gaussian profile of atomic hydrogen on 32 to 1024 cells must reproduce reference errors against its analytic solution within a tenth ([Gong et al.](#gong-et-al-2023) 2023, §4.1).

The network of Gong, Ostriker and Wolfire (2017), integrated directly and through the KIDA format in a uniform medium, must reproduce reference abundances and energies to $10^{-3}$ and $10^{-2}$, and the shock tube with chemistry its reference pressure to $10^{-3}$. With six rays, a static photodissociation region must follow its reference abundances and temperature to a tenth (Gong et al. 2023, §4.2.1). These four tests need CVODE, as does the Gaussian profile.

Detail: [Athena 2.15.3](../references/athena-synthesis.md#2153-chemistry).

## 4. Assessment

The references report the tolerances of these tests rather than measured errors, and Zingale's text gives no results for reactive flow beyond the flame of [topic 18, §3](18-operator-splitting-and-coupling-of-processes.md#3-tests). In the simulations of 2016 the cooling time mostly exceeds the time scale of the hydrodynamics, and the step is limited to a tenth of it where cooling is very effective ([topic 37, §2.6](37-driver-and-control-of-time-step.md#26-limits-of-the-step-from-cooling-and-conduction)). **[GK]** Reactions and cooling are local to the cell, so that their integration vectorises across cells, which suits NumPy, while calls to an external solver cell by cell do not, and an external library such as CVODE adds a compiled dependency, whose wheels must exist for each platform and build of Python to keep the installation to a single command. Explicit substeps, as in the forward Euler scheme of Athena++, are simple and change no variable by more than a set fraction per substep, but their number grows without bound as the cooling becomes stiff, and near an equilibrium of heating and cooling they oscillate about it by up to about that fraction. Implicit methods are stable at any step for linear equations, but for non-linear cooling their equation can have several roots, so that the result jumps as the step varies ([topic 20, §2.5](20-radiative-cooling.md#25-integration-over-a-step)), and they need Jacobians and iterations whose number varies from cell to cell. A sequential split after the last stage, as in Athena++, is of first order in time. The production runs need the radiative cooling of an optically thin plasma, a tabulated function of temperature and metallicity, which [topic 20](20-radiative-cooling.md) sets out with its integration. Open are whether the production runs need a network beside the tables of [topic 20](20-radiative-cooling.md), and how a network couples to the hydrodynamics ([topic 18](18-operator-splitting-and-coupling-of-processes.md)).

## 5. Sources

- <a id="brown-et-al-1989"></a>Brown, P. N., Byrne, G. D. and Hindmarsh, A. C., VODE: a variable-coefficient ODE solver, SIAM Journal on Scientific and Statistical Computing 10, 1038–1051 (1989), [doi:10.1137/0910062](https://doi.org/10.1137/0910062).
- <a id="fryxell-et-al-2000"></a>Fryxell, B., Olson, K., Ricker, P., Timmes, F. X., Zingale, M., Lamb, D. Q., MacNeice, P., Rosner, R., Truran, J. W. and Tufo, H., FLASH: an adaptive mesh hydrodynamics code for modeling astrophysical thermonuclear flashes, ApJS 131, 273–334 (2000), [doi:10.1086/317361](https://doi.org/10.1086/317361).
- <a id="gong-et-al-2017"></a>Gong, M., Ostriker, E. C. and Wolfire, M. G., A simple and accurate network for hydrogen and carbon chemistry in the interstellar medium, ApJ 843, 38 (2017), [doi:10.3847/1538-4357/aa7561](https://doi.org/10.3847/1538-4357/aa7561).
- <a id="gong-et-al-2023"></a>Gong, M., et al., in preparation, cited by Stone et al. (2020, §5) for networks of chemical reactions. **[GK]** Published as Implementation of chemistry in the Athena++ code, ApJS 268, 42 (2023), [arXiv:2305.04965](https://arxiv.org/abs/2305.04965), [doi:10.3847/1538-4365/aceaf9](https://doi.org/10.3847/1538-4365/aceaf9).
- <a id="grassi-et-al-2014"></a>Grassi, T., et al., KROME – a package to embed chemistry in astrophysical simulations, MNRAS 439, 2386–2419 (2014), [doi:10.1093/mnras/stu114](https://doi.org/10.1093/mnras/stu114).
- <a id="timmes-1999"></a>Timmes, F. X., Integration of nuclear reaction networks for stellar hydrodynamics, ApJS 124, 241 (1999), [1999ApJS..124..241T](https://ui.adsabs.harvard.edu/abs/1999ApJS..124..241T/abstract).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

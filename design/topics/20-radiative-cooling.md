# Radiative cooling

## 1. Overview

Optically thin gas radiates the energy that collisions between electrons and ions excite, at a rate per unit volume proportional to the product of their densities and to a cooling function of temperature and composition, which radiation and the thermal history also change out of equilibrium. Cooling enters the equation of the energy as a local sink, and near the peak of the function at about $10^5$ K its time scale can fall far below that of the flow. The collection on conduction and cooling sets out tables in collisional ionisation equilibrium (Sutherland and Dopita 1993; Schure et al. 2009), out of equilibrium (Gnat and Sternberg 2007) and under radiation (Wiersma, Schaye and Smith 2009; Ploeckinger and Schaye 2020), and their integration over a step, explicitly with a limit of the step, as in Athena in 2016, or exactly after Townsend (2009). Networks of interstellar chemistry with their own cooling follow in topic 19, the splitting from the hydrodynamics in topic 18, the metallicity as a passive scalar in topic 21, and the clouds that cooling shapes in topic 34. Optically thick gas, which needs the radiation transport of topic 23, and cooling by dust lie outside it.

## 2. Methods

### 2.1 Cooling in the equation of the energy

The simulations of [Armillotta, Fraternali and Marinacci](#armillotta-et-al-2016) (2016, eq. 9) add a loss $-n^2\Lambda(T, Z)$ to the equation of the total energy, with $\Lambda$ from tables of temperature and metallicity $Z$. The tables differ in the densities that multiply $\Lambda$, in $\mathrm{erg\,cm^3\,s^{-1}}$: those of electrons and of all ions, $n_\mathrm{e}n_\mathrm{t}$, for [Sutherland and Dopita](#sutherland-dopita-1993) (1993, eqs. 51 to 58), and those of electrons and of hydrogen, $n_\mathrm{e}n_\mathrm{H}$, for [Gnat and Sternberg](#gnat-sternberg-2007) (2007) and [Schure et al.](#schure-et-al-2009) (2009), who also tabulate $\Lambda_\mathrm{hd} = (n_\mathrm{e}/n_\mathrm{H})\Lambda$ for a loss $n_\mathrm{H}^2\Lambda_\mathrm{hd}$ (eqs. 1 and 2). At constant density, with the mean masses per particle $\mu = \rho/n$, per electron $\mu_\mathrm{e} = \rho/n_\mathrm{e}$ and per hydrogen atom $\mu_\mathrm{H} = \rho/n_\mathrm{H}$, the temperature then falls as ([Townsend](#townsend-2009) 2009, eqs. 3 and 5)

$$\frac{\mathrm{d}T}{\mathrm{d}t} = -\frac{(\gamma - 1)\,\rho\,\mu\,\Lambda(T)}{k_\mathrm{B}\,\mu_\mathrm{e}\,\mu_\mathrm{H}},$$

on the cooling time $t_\mathrm{cool} = k_\mathrm{B}\mu_\mathrm{e}\mu_\mathrm{H}T/[(\gamma - 1)\rho\mu\Lambda(T)]$, with the mean masses fixed by the ionisation, as Townsend takes them above $10^4$ K. Codes of Godunov type split the energy equation into its adiabatic part, applied with the advection, and this cooling part, applied afterwards at constant density (topic 18). **[GK]** Paired with the wrong densities, a table errs by factors near 1.1 or 1.2 for ionised gas of solar composition, and the paper of 2016 does not say which densities multiply its $\Lambda$.

Detail: [Conduction and cooling 2.5.1](../references/conduction-and-cooling-synthesis.md#251-cooling-in-the-energy-equation), [Conduction and cooling 2.5.2](../references/conduction-and-cooling-synthesis.md#252-the-cooling-functions-of-sutherland-and-dopita), [Conduction and cooling 2.5.3](../references/conduction-and-cooling-synthesis.md#253-the-cooling-curve-of-spex), [Conduction and cooling 2.7.2](../references/conduction-and-cooling-synthesis.md#272-exact-integration-of-cooling).

### 2.2 Collisional ionisation equilibrium

Where collisions set the ionisation and the gas cools more slowly than it ionises and recombines, the balance depends on temperature alone, and $\Lambda$ on $T$ and the abundances. Sutherland and Dopita (1993) compute it with MAPPINGS II for 16 elements in all stages of ionisation and 1683 transitions, for $4.0 \le \log T \le 8.5$ in steps of 0.05 dex and eight series from $[\mathrm{Fe/H}] = +0.5$ to $-3.0$ and without metals, with primordial ratios and $[\mathrm{O/Fe}] = +0.5$ below $-1.0$. For solar abundances $\log\Lambda$ peaks at about $-20.96$ near $10^{5.3}$ K, from oxygen, beside a carbon shoulder near $10^{4.95}$ K, and falls to a minimum of $-22.73$ near $10^{7.4}$ K, beyond which free–free emission dominates. Schure et al. (2009) recompute the curve with SPEX, with 5466 lines from $10^{3.8}$ to $10^{8.16}$ K, give the contribution of each element so that other compositions follow by scaling (eq. 3), and continue below $10^4$ K with the rates of [Dalgarno and McCray](#dalgarno-mccray-1972) (1972), for an ionisation fraction set as a parameter. A code takes its rate from such a table.

1. Compute $T$ from $p$ and $\rho$ with the mean mass of the assumed ionisation (topic 2).
2. Interpolate $\log\Lambda$ linearly in $\log T$, and between the series of metallicity where $Z$ varies.
3. Form the loss per unit volume, $n_\mathrm{e}n_\mathrm{t}\Lambda$ or $n_\mathrm{e}n_\mathrm{H}\Lambda$ as the table is normalised.
4. Subtract it from the internal energy alone, which keeps errors of precision from making the energy negative (Schure et al. 2009, eq. 14).

Athena in 2016 uses the tables of Sutherland and Dopita, and AthenaPK that of Schure et al. for solar metallicity, switched off below $10^4$ K ([Brüggen, Scannapieco and Grete](#bruggen-et-al-2023) 2023).

Detail: [Conduction and cooling 2.5.2](../references/conduction-and-cooling-synthesis.md#252-the-cooling-functions-of-sutherland-and-dopita), [Conduction and cooling 2.5.3](../references/conduction-and-cooling-synthesis.md#253-the-cooling-curve-of-spex), [Conduction and cooling 3.4](../references/conduction-and-cooling-synthesis.md#34-athenapk-in-the-simulations-of-brüggen-scannapieco-and-grete).

### 2.3 Cooling out of equilibrium

Gas that cools faster than it recombines stays overionised and cools less, as it holds fewer of the ions that cool efficiently at its temperature. An ion relaxes on the time $1/(\alpha_\mathrm{rec} + S_\mathrm{coll})$ of its rates of recombination and collisional ionisation, longest for closed shells such as C V (Sutherland and Dopita 1993, eq. 63). Sutherland and Dopita follow isobaric slabs that start in equilibrium, and Gnat and Sternberg (2007) dust-free gas cooling isochorically or isobarically from above $5 \times 10^6$ K, for $10^{-3}$ to 2 times the solar metallicity, along a path of states.

1. Start in equilibrium above $5 \times 10^6$ K.
2. Lower the pressure, for isochoric cooling, or raise the density, for isobaric cooling, by a fraction of at most 0.05.
3. Compute $\Lambda$ from the current fractions of the ions, and the interval $\Delta t$ that the step needs (eq. 7).
4. Integrate the 103 equations of the fractions over $\Delta t$ with a solver that switches between stiff and non-stiff methods (eqs. 1 and 2; topic 19).
5. Repeat to $10^4$ K.

All rates scale as $n^2$, so that the fractions and $\Lambda$ depend on the temperature and the metallicity alone, and tables in $T$ and $Z$ suffice. Departures start where the cooling time falls below the time of recombination, near $10^6$ K for solar metallicity (eqs. 8 and 9). Sutherland and Dopita stress that heated gas departs the other way, so that no single function serves gas that both heats and cools, which would need its ionisation followed in time.

Detail: [Conduction and cooling 2.6.1](../references/conduction-and-cooling-synthesis.md#261-non-equilibrium-cooling-of-sutherland-and-dopita), [Conduction and cooling 2.6.2](../references/conduction-and-cooling-synthesis.md#262-time-dependent-ionisation-of-gnat-and-sternberg).

### 2.4 Cooling under radiation

Photoionisation also overionises gas, and makes the rates depend on density through the ionisation parameter. [Wiersma, Schaye and Smith](#wiersma-et-al-2009) (2009) tabulate them with Cloudy in $\log n_\mathrm{H}$, $\log T$ and redshift for the background of galaxies and quasars, element by element, and sum them for any abundances (eq. 4):

$$\Lambda = \Lambda_\mathrm{H,He} + \frac{n_\mathrm{e}/n_\mathrm{H}}{(n_\mathrm{e}/n_\mathrm{H})_\odot}\sum_{i > \mathrm{He}}\Lambda_{i,\odot}\,10^{[i/\mathrm{H}]},$$

where hydrogen and helium, which set the density of electrons, are tabulated together, and the metal lines scale with that density. [Ploeckinger and Schaye](#ploeckinger-schaye-2020) (2020) extend the tables to $1 \le \log T \le 9.5$ and $-8 \le \log n_\mathrm{H} \le 6$, with the shielding column of self-gravitating gas, $\log N_\mathrm{J} = 19.44 + 0.5(\log n_\mathrm{H} + \log T)$ (eq. 5), an interstellar field and cosmic rays that scale with that column, and dust. They couple the tables to a reduced network of hydrogen and helium.

1. Follow hydrogen and helium with the network, out of equilibrium.
2. Take the cooling and heating of the metals from the table.
3. Rescale the cooling of the metals by the ratio of the electron density of the network and the metals to that of the table.

Detail: [Conduction and cooling 2.6.3](../references/conduction-and-cooling-synthesis.md#263-cooling-under-photoionisation-element-by-element), [Conduction and cooling 2.6.4](../references/conduction-and-cooling-synthesis.md#264-cooling-tables-with-self-shielding-and-local-radiation).

### 2.5 Integration over a step

Athena in 2016 adds the cooling after the hydrodynamic step at first order, explicitly, and limits the step to a tenth of the cooling time (Armillotta et al. 2016, §2.2). Townsend (2009, eqs. 11 to 21) compares such updates for the cooling part of a zone. The explicit update $T^{n+1} = T^n(1 - \Delta t/t_\mathrm{cool})$ holds $\Lambda$ at its initial value and fails as $\Delta t$ nears $t_\mathrm{cool}$, and a step of Runge–Kutta costs one more evaluation of $\Lambda$ per order. Implicit updates need a root finder, whose equation can have several roots, five for $\Delta t = 0.3\,t_\mathrm{cool}$ at $10^6$ K, so that the result jumps as $\Delta t$ varies. Their unconditional stability holds for linear equations, and neighbouring zones may cool to quite different temperatures. The exact integration instead solves the cooling part over the whole step, through the temporal evolution function (eqs. 24 and 26)

$$Y(T) = \frac{\Lambda(T_\mathrm{ref})}{T_\mathrm{ref}}\int_T^{T_\mathrm{ref}}\frac{\mathrm{d}T'}{\Lambda(T')}, \qquad T^{n+1} = Y^{-1}\!\left[Y(T^n) + \frac{T^n}{T_\mathrm{ref}}\,\frac{\Lambda(T_\mathrm{ref})}{\Lambda(T^n)}\,\frac{\Delta t}{t_\mathrm{cool}}\right],$$

a normalised time to cool from a reference temperature $T_\mathrm{ref}$ to $T$.

1. Fit $\Lambda$ by a piecewise power law $\Lambda_k(T/T_k)^{\alpha_k}$ between nodes $T_k$, refitting a table where needed.
2. Compute the values $Y_k$ at the nodes once, downwards from $Y = 0$ at the highest node, which serves as $T_\mathrm{ref}$ (eqs. A4 to A7).
3. In each zone, compute $t_\mathrm{cool}$ from $T^n$ and $\rho$, and the argument of $Y^{-1}$ from the analytic $Y$ of the interval of $T^n$.
4. Invert $Y$ in the interval that holds the argument for $T^{n+1}$, and apply the floor of the table.
5. Change the internal energy at fixed density to match $T^{n+1}$.

**[GK]** The public C version of Athena instead adds cooling explicitly within its unsplit integrator, or by an implicit, split solver for one function.

Detail: [Conduction and cooling 2.7.1](../references/conduction-and-cooling-synthesis.md#271-operator-splitting-and-the-limit-on-the-time-step), [Conduction and cooling 2.7.2](../references/conduction-and-cooling-synthesis.md#272-exact-integration-of-cooling), [Conduction and cooling 3.1](../references/conduction-and-cooling-synthesis.md#31-athena-in-the-simulations-of-2016).

## 3. Tests

Townsend (2009, §3) cools a single zone from $10^6$, $10^7$ and $10^8$ K with a piecewise fit to the equilibrium efficiency of Gnat and Sternberg, for steps up to and beyond the cooling time, against the exact solution. His benchmark is the steady cooling layer behind a one-dimensional radiative shock at Mach 3, 10 and 100, after [Strickland and Blondin](#strickland-blondin-1995) (1995), resolved by 1, 10 or 100 zones and advanced by one Courant step (§4).

Schure et al. (2009, §5) follow the shell that the fast wind of a Wolf–Rayet star sweeps up in the slow wind of its red-supergiant phase, with AMRVAC on an axisymmetric grid, comparing their curve with that of MacDonald and Bailey, used in ZEUS-3D. The cooling compresses the shell beyond the factor of 4 of an adiabatic shock until it turns unstable. The tables are checked against each other: Cloudy against Gnat and Sternberg, Sutherland and Dopita and MAPPINGS III in equilibrium, the sums of eq. 4 against full calculations, and the fractions of Gnat and Sternberg against smaller steps of their path.

Detail: [Conduction and cooling 2.5.3](../references/conduction-and-cooling-synthesis.md#253-the-cooling-curve-of-spex), [Conduction and cooling 2.6.2](../references/conduction-and-cooling-synthesis.md#262-time-dependent-ionisation-of-gnat-and-sternberg), [Conduction and cooling 2.6.3](../references/conduction-and-cooling-synthesis.md#263-cooling-under-photoionisation-element-by-element), [Conduction and cooling 2.7.2](../references/conduction-and-cooling-synthesis.md#272-exact-integration-of-cooling).

## 4. Assessment

In equilibrium the tables agree to better than 0.3 dex, so that the rates are known within a factor of 2, with the largest differences near $10^5$ K (Wiersma et al. 2009), while SPEX cools more than Sutherland and Dopita between $10^4$ and $10^6$ K, by 0.5 dex at its hydrogen peak near $10^{4.2}$ K. Out of equilibrium the cooling falls by factors of 2 to 4 for solar metallicity, its maximum to $2.6 \times 10^{-22}\,\mathrm{erg\,cm^3\,s^{-1}}$ at $2.1 \times 10^5$ K, 1.8 times below equilibrium, while the carbon and oxygen peaks of Sutherland and Dopita fall 3 to 10 times. Radiation lowers it below $10^6$ K for ionisation parameters above about $10^{-1}$ and below $10^5$ K above $10^{-3}$, and the sums by element reproduce full calculations with median errors of 0.33, 1.6 and 6.1 per cent at 0.1, 1 and 10 times the solar metallicity. Behind the shock, where $\Delta t/t_\mathrm{cool}$ falls as the inverse of the number of zones, the errors with one zone at Mach 100 reach 38 per cent for the first-order explicit update, 12 per cent at second order and 99.9 per cent for all implicit ones, and they fall below 10 per cent with 10 zones in all cases but one and below 1 per cent with 100. Explicit updates take about 100 ns per zone, the exact integration about twice that and implicit ones 2.5 to 12 times. In the shell of Schure et al. the thermal losses converge with resolution, while its thickness follows the grid. **[GK]** The choice of table moves the rate by factors of 2 to 10 near $10^5$ K, more than any integrator errs on a resolved layer, and the gas mixed at the surface of a fountain cloud, cooling fast through that range, is the gas most likely to depart from equilibrium. A global limit of the step to a tenth of the cooling time, as in 2016, lets the fastest-cooling cell set the step of the whole grid, which sub-cycling by cell or the exact integration avoids. The exact integration vectorises in NumPy without an external library. Below $10^4$ K the equilibrium tables end or rest on assumed ionisation fractions, so that a floor or a source of heating closes them. Open are the table and its normalisation, the dependence on the metallicity that a scalar carries (topic 21), the floor and heating, the integrator, and the limit of the step by cooling (topic 37).

## 5. Sources

- <a id="armillotta-et-al-2016"></a>Armillotta, L., Fraternali, F. and Marinacci, F., Efficiency of gas cooling and accretion at the disc–corona interface, MNRAS 462, 4157–4170 (2016), [arXiv:1608.06290](https://arxiv.org/abs/1608.06290), [doi:10.1093/mnras/stw1930](https://doi.org/10.1093/mnras/stw1930).
- <a id="bruggen-et-al-2023"></a>Brüggen, M., Scannapieco, E. and Grete, P., The launching of cold clouds by galaxy outflows. V. The role of anisotropic thermal conduction, ApJ 951, 113 (2023), [arXiv:2304.09881](https://arxiv.org/abs/2304.09881), [doi:10.3847/1538-4357/acd63e](https://doi.org/10.3847/1538-4357/acd63e).
- <a id="dalgarno-mccray-1972"></a>Dalgarno, A. and McCray, R. A., Heating and ionization of H I regions, Annual Review of Astronomy and Astrophysics 10, 375–426 (1972), [doi:10.1146/annurev.aa.10.090172.002111](https://doi.org/10.1146/annurev.aa.10.090172.002111).
- <a id="gnat-sternberg-2007"></a>Gnat, O. and Sternberg, A., Time-dependent ionization in radiatively cooling gas, ApJS 168, 213–230 (2007), [arXiv:astro-ph/0608181](https://arxiv.org/abs/astro-ph/0608181), [doi:10.1086/509786](https://doi.org/10.1086/509786).
- <a id="ploeckinger-schaye-2020"></a>Ploeckinger, S. and Schaye, J., Radiative cooling rates, ion fractions, molecule abundances and line emissivities including self-shielding and both local and metagalactic radiation fields, MNRAS 497, 4857–4883 (2020), [arXiv:2006.14322](https://arxiv.org/abs/2006.14322), [doi:10.1093/mnras/staa2172](https://doi.org/10.1093/mnras/staa2172).
- <a id="schure-et-al-2009"></a>Schure, K. M., Kosenko, D., Kaastra, J. S., Keppens, R. and Vink, J., A new radiative cooling curve based on an up-to-date plasma emission code, A&A 508, 751–757 (2009), [arXiv:0909.5204](https://arxiv.org/abs/0909.5204), [doi:10.1051/0004-6361/200912495](https://doi.org/10.1051/0004-6361/200912495).
- <a id="strickland-blondin-1995"></a>Strickland, R. and Blondin, J. M., Numerical analysis of the dynamic stability of radiative shocks, ApJ 449, 727 (1995), [doi:10.1086/176093](https://doi.org/10.1086/176093).
- <a id="sutherland-dopita-1993"></a>Sutherland, R. S. and Dopita, M. A., Cooling functions for low-density astrophysical plasmas, ApJS 88, 253–327 (1993), [1993ApJS...88..253S](https://ui.adsabs.harvard.edu/abs/1993ApJS...88..253S/abstract), [doi:10.1086/191823](https://doi.org/10.1086/191823).
- <a id="townsend-2009"></a>Townsend, R. H. D., An exact integration scheme for radiative cooling in hydrodynamical simulations, ApJS 181, 391–397 (2009), [arXiv:0901.3146](https://arxiv.org/abs/0901.3146), [doi:10.1088/0067-0049/181/2/391](https://doi.org/10.1088/0067-0049/181/2/391).
- <a id="wiersma-et-al-2009"></a>Wiersma, R. P. C., Schaye, J. and Smith, B. D., The effect of photoionization on the cooling rates of enriched, astrophysical plasmas, MNRAS 393, 99–107 (2009), [arXiv:0807.3748](https://arxiv.org/abs/0807.3748), [doi:10.1111/j.1365-2966.2008.14191.x](https://doi.org/10.1111/j.1365-2966.2008.14191.x).

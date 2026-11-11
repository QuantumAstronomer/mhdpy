# Constants

**Prefix.** CONST.

**Status.** Agreed on 2026-11-11.

**Briefs.** [B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants).

## Scope

The constants are the physical and astronomical constants that the first pass needs, each held in cgs with the value of its current source in the module `mhdpy.infrastructure.constants`: Boltzmann's constant as the SI fixes it, the masses of the proton, the electron and the atomic mass unit after CODATA 2022, the astronomical unit and the parsec as the IAU defines them, and the Julian year. Their conversion into the code units of a run, and the named units that rest on them, such as the parsec and the megayear, are left to the units, and which mass measures the mean mass of a particle to the brief on equations of state. Later briefs add the constants that they need, as self-gravity the gravitational constant.

Each constant is a float of double precision, under a name in capitals after PEP 8 and typed `Final`, with its source cited in a comment beside it. A value given to round-off is bounded in terms of $\epsilon = 2^{-52}$, the machine epsilon of double precision. The module relies on the standard library alone.

## Physical constants

<a id="const01"></a>**CONST01** The module shall hold Boltzmann's constant as `BOLTZMANN`, $k_\mathrm{B} = 1.380649 \times 10^{-16}\,\mathrm{erg\,K^{-1}}$, the value that the SI fixes. The temperature of every cell follows from $p/\rho$ through $k_\mathrm{B}$ and the mean mass of a particle ([topic 2, §2.1](../../topics/02-equations-of-state.md#21-the-ideal-and-the-isothermal-gas)), and conduction and cooling act on that temperature ([topic 17, §2.1](../../topics/17-thermal-conduction.md#21-the-classical-flux-and-its-suppression), [topic 20, §2.1](../../topics/20-radiative-cooling.md#21-cooling-in-the-equation-of-the-energy)). Since the revision of the SI in 2019 the constant is exact, so that its digits are its definition ([B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants)).

<a id="const02"></a>**CONST02** The module shall hold the mass of the proton as `PROTON_MASS`, $m_\mathrm{p} = 1.67262192595 \times 10^{-24}\,\mathrm{g}$, the value of CODATA 2022. The mean mass of a particle is measured in the mass of the proton or in the atomic mass unit, as the brief on equations of state chooses, and the number densities on which cooling acts follow from the density through it ([topic 20, §2.1](../../topics/20-radiative-cooling.md#21-cooling-in-the-equation-of-the-energy)). CODATA 2022 gives the latest values of the measured constants ([B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants)).

<a id="const03"></a>**CONST03** The module shall hold the mass of the electron as `ELECTRON_MASS`, $m_\mathrm{e} = 9.1093837139 \times 10^{-28}\,\mathrm{g}$, the value of CODATA 2022. The saturated flux of conduction, which caps the classical flux where the gradient of temperature grows steep, rests on the speed of the electrons and so on their mass ([topic 17, §2.2](../../topics/17-thermal-conduction.md#22-saturation)).

<a id="const04"></a>**CONST04** The module shall hold the atomic mass unit as `ATOMIC_MASS_UNIT`, $m_\mathrm{u} = 1.66053906892 \times 10^{-24}\,\mathrm{g}$, the value of CODATA 2022. It is the other mass in which the mean mass of a particle may be measured, so that the brief on equations of state can choose between the two ([B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants)).

## Astronomical constants

<a id="const05"></a>**CONST05** The module shall hold the astronomical unit as `ASTRONOMICAL_UNIT`, $\mathrm{au} = 1.495\,978\,707 \times 10^{13}\,\mathrm{cm}$, the value that the IAU fixes. Resolution B2 of the IAU of 2012 defines it as 149 597 870 700 m exactly, and the parsec rests on it ([B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants)). **[GK]** The value is an integer in cgs of fewer than 53 bits, which double precision holds exactly.

<a id="const06"></a>**CONST06** The module shall hold the parsec as `PARSEC`, $\mathrm{pc} = (648\,000/\pi)\,\mathrm{au}$, to a relative difference of at most twice $\epsilon$. Resolution B2 of the IAU of 2015 defines the parsec exactly so ([B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants)), and the production run measures in it the cells of about 2 pc and the clouds of 100 pc of its reference ([topic 34, §2.6](../../topics/34-cold-clouds-and-mixing-layers.md#26-fountain-clouds-through-a-corona)). **[GK]** In double precision, the order of the division and the product moves the result by one unit in the last place, so that the bound admits every order, while a wrong factor fails by far.

<a id="const07"></a>**CONST07** The module shall hold the Julian year as `JULIAN_YEAR`, $\mathrm{yr} = 365.25 \times 86\,400\,\mathrm{s} = 3.15576 \times 10^{7}\,\mathrm{s}$. [B5D5](../../briefs/B05-parameters-and-units.md#b5d5-the-constants) measures times in Julian years, such as the 60 Myr in which the fountain cloud of 2016 condenses a quarter of its mass ([topic 34, §3](../../topics/34-cold-clouds-and-mixing-layers.md#3-assessment)). **[GK]** The value is an integer in seconds, which double precision holds exactly.

## Verification

None. The constants meet the criteria of [§1.3 of the overview](../../overview.md#13-success-criteria) only through the units and the physics that use them, whose tests check them there, the units against their constants among them.

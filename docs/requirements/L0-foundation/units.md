# Units

| | |
|---|---|
| Prefix | `UNI` |
| Layer | L0, foundation |
| Status | Draft |

## Purpose

mhdpy solves its equations in dimensionless code units. The unit system relates those code units to physical units (cgs). It is defined once, when a simulation is set up, by the code units of length, mass and time. From those it provides every other unit, the conversions in both directions, and physical constants expressed in code units. Modules whose physics depends on physical constants use it, as does everything that reads or writes physical values:

- cooling functions (in $\mathrm{erg\,cm^3\,s^{-1}}$) and Spitzer conduction;
- parameters given in physical units;
- the outputs, restart files and history, which record the unit system so that a file describes itself.

The kernels never see units: whatever they need arrives as dimensionless numbers, computed at set-up.

## Sources

- **D12.5:** a unit system set up with the simulation; the code stays dimensionless, and the unit system provides the conversions. Temperature through the mean molecular weight.
- **D12 §4:** unit conversions are tested against known physical values; a problem posed in code units gives the same results in any unit system.
- **D13.5, D14.2, D14.7:** restart files and outputs record the unit system; the reader returns units.
- **D15.2:** declared parameters carry a unit where relevant.
- **D04.4:** double precision throughout.

## Requirements

Each requirement is stated first, as the verifiable statement that tests check, and followed by its rationale.

### Definition

The equations of hydrodynamics and MHD involve only three independent dimensions: length, mass and time. Every other quantity is a product of powers of these three. Temperature is not an independent dimension here, because it enters only through the ideal-gas law, with Boltzmann's constant and the mean molecular weight (UNI08). Neither is the magnetic field, because in Gaussian units, with the factor $4\pi$ absorbed (UNI07), it is expressed in length, mass and time as well. Three numbers therefore define a unit system completely: the code units of length, mass and time, given in cgs.

The choice of those three numbers is the user's. A good choice makes the values of a problem of order unity: the density of a hot galactic corona is about $10^{-27}\,\mathrm{g\,cm^{-3}}$ and the size of a fountain cloud about $10^{20}\,\mathrm{cm}$, so in cgs the values of one simulation span dozens of orders of magnitude. Code units of order the problem's own scales keep the arithmetic well inside the range of double precision, and every verification problem in the literature is posed in such units anyway.

**UNI01.** A unit system is defined by three code units, of length, mass and time, each given in cgs as a positive, finite number. All other units derive from these three. A value that is zero, negative, infinite or not a number is refused when the unit system is created.
*Rationale:* A unit is a scale factor, so only positive, finite values make sense. A zero unit would turn every conversion into a division by zero, a negative one would flip the sign of every converted value, and an infinite or undefined one would spread through every conversion without any error being raised. Refusing such values when the unit system is created points directly at the cause, instead of at a strange result many steps later.

**UNI02.** The code unit of any quantity with dimensions $L^a M^b T^c$, for integer and half-integer exponents $a$, $b$, $c$, is available as the product of the three code units raised to those powers, to within 4 ulp. Half-integer exponents are needed for the magnetic field (UNI07). *(Changed 2026-10-13: the tolerance was 2 ulp, which the first test showed to be tighter than the arithmetic allows; see the rationale.)*
*Rationale:* A general rule, rather than only a list of named units, covers every quantity a module may need without the unit system having to anticipate it: the unit of a cooling rate per unit volume, of a conductivity or of a gravitational potential follows from its dimensions alone. The tolerance of 4 ulp is the bound of the arithmetic involved: each of the three powers is computed to within about 1 ulp (the C library's power function is accurate, but not exactly rounded), and each of the two multiplications that combine them adds at most half an ulp, $3 \times 1 + 2 \times 1/2 = 4$. The first version of this requirement asked for 2 ulp; checking all 4913 combinations of exponents from $-4$ to $4$ in steps of $1/2$ found one at 3 ulp, within the bound but beyond that tolerance. The tolerance is still tight: a wrong exponent changes a unit by orders of magnitude, and even a subtle error in how the product is formed would show as a difference far larger than 4 ulp.

**UNI03.** The code units of at least the following quantities are available by name, each equal to its product of base units (UNI02) to within 4 ulp:

- length, mass, time;
- velocity; acceleration;
- density; momentum density; mass flux;
- pressure, which is also energy density;
- energy; specific energy; energy flux.

The magnetic field is available by name as well, but its unit contains the factor $\sqrt{4\pi}$ and is specified by UNI07. *(Changed 2026-10-13: the magnetic field was listed above, although no product of base units contains $\sqrt{4\pi}$; found while writing the test.)*
*Rationale:* Named units make code readable and leave less room for mistakes than triplets of exponents: `system.density` says what is meant, while `system.unit(length=-3, mass=1)` has to be read and checked. The list covers what the conserved and primitive variables, their fluxes, gravitational accelerations and the outputs need. Requiring each named unit to equal its product of base units ties the names to the general rule, so that a named unit can never disagree with the unit computed from its dimensions. The list is a minimum; further names can be added without changing these requirements.

**UNI04.** Every unit available by name has a label of its cgs unit (for example `g cm^-3` for density), for the headers of the history and the attributes of outputs (D14).
*Rationale:* Outputs and the history describe themselves (D14.2, D14.4): a column of numbers is only useful when its unit is stated next to it. A label that belongs to each named unit means that every output spells a unit the same way, and that no writer has to compose labels of its own. The labels are plain text, readable by people and by programs alike.

### Conversions

Conversions happen at the edges of a simulation, never inside it. Parameters and initial conditions given in physical units are converted to code units at set-up. The reader converts values back to physical units for analysis (D14.7). Modules convert their physical constants once, at set-up (UNI10). The kernels in between work in code units only, so conversions cost nothing during a run, and their accuracy matters only in so far as converted values must be exact enough to be trusted and to survive a round trip.

One convention covers every conversion: a unit is the value of one code unit expressed in cgs. With that convention, a conversion is a single multiplication or division, and there is no doubt about which way a factor applies.

**UNI05.** A value converts from code units to cgs by multiplication with its unit, and from cgs to code units by division. This holds for Python floats and NumPy arrays alike: arrays are converted elementwise, keep their shape and are double precision.
*Rationale:* Defining a unit as the cgs value of one code unit makes every conversion one operation, and the direction follows from the definition rather than from a convention to remember for each function. Arrays matter as much as single values: initial conditions are often written for whole fields at once, and analysis converts whole snapshots. Elementwise conversion through NumPy keeps that as fast and as simple as converting a single number. Results are in double precision, as all of mhdpy is (D04.4), whatever the precision of the input.

**UNI06.** A round trip, code units to cgs and back or cgs to code units and back, reproduces the value to within 2 ulp, for every value whose magnitude, in both unit systems, lies between twice the smallest and half the largest normal double-precision number. *(Changed 2026-10-13: the domain was every value whose representations are finite, normal double-precision numbers, which fails at the very edges of the range; found by the test, see the rationale.)*
*Rationale:* A multiplication followed by a division rounds twice, so 2 ulp is the best floating-point arithmetic can guarantee; any larger difference would point at an error in the conversion itself. Round trips happen in practice: a parameter given in physical units is converted to code units and later reported back in physical units, and the two must agree. The restriction of the domain excludes values so extreme that they overflow or underflow in one of the two systems, where no conversion can be exact. It keeps a factor of two away from both ends of the range of normal numbers, because at the very edges a single rounding can cross a limit: the test of this requirement found that the largest double, converted to code units and back, overflows to infinity, although both of its representations are finite and normal. A factor of two is far more than one rounding can change a value by. Physical values in a sensible unit system stay hundreds of orders of magnitude away from either edge.

### Magnetic field

In Gaussian cgs, the magnetic pressure is $B^2/(8\pi)$ and the Lorentz force density is $(\nabla \times \mathbf{B}) \times \mathbf{B}/(4\pi)$. The factors $4\pi$ are a property of the unit system, not of the physics. Absorbing $\sqrt{4\pi}$ into the magnetic field removes them: the magnetic pressure becomes $B^2/2$, the Alfvén speed $B/\sqrt{\rho}$, and the induction and momentum equations contain no factor $4\pi$ anywhere. This is the convention of the state-of-the-art reference codes, and the magnetic test problems of the literature, such as the Orszag–Tang vortex and the advection of a field loop, are posed in it.

The convention has to be stated explicitly, because mixing it with plain Gaussian units is one of the classic errors in MHD: it changes field strengths by $\sqrt{4\pi} \approx 3.5$ and magnetic energies by $4\pi \approx 12.6$, and the result often still looks plausible.

**UNI07.** The factor $4\pi$ is absorbed into the magnetic field, so that no factor $4\pi$ (or $\sqrt{4\pi}$) appears anywhere in the equations in code units: the magnetic pressure and the magnetic energy density are $B^2/2$. The code unit of the magnetic field is therefore $\sqrt{4\pi\,p_\mathrm{u}}$ gauss, with $p_\mathrm{u}$ the code unit of pressure. A field $B$ in gauss and its value $B_\mathrm{code}$ in code units satisfy $B^2/(8\pi) = (B_\mathrm{code}^2/2)\,p_\mathrm{u}$ in $\mathrm{erg\,cm^{-3}}$, to within 4 ulp.

*Rationale:* Absorbing the factor makes the equations in code units truly dimensionless: they contain no constant that belongs to a particular unit system. The unit of the magnetic field then follows from the requirement that the magnetic pressure in code units, $B_\mathrm{code}^2/2$, is a pressure like any other. The relation in the requirement is the physical check of the convention: the magnetic energy density of a given field must be the same physical quantity whether it is computed in gauss or in code units. It tests the convention itself rather than the formula for the unit, so an error in either shows. The tolerance of 4 ulp allows for the square root and the squares involved.

### Temperature

Temperature does not appear in the equations of hydrodynamics in code units, which evolve density, momentum and energy; the pressure follows from them. It is needed by physics modules, since cooling functions are tabulated in temperature and the Spitzer conductivity grows as $T^{5/2}$, and by users, who think of gas as hot or cold rather than as having a high ratio of pressure to density. For an ideal gas, the two are related by $p = \rho\, k_\mathrm{B} T/(\mu\, m_\mathrm{H})$, with $\mu$ the mean molecular weight: the average mass per particle in units of the mass of the hydrogen atom.

The mean molecular weight is not a constant of a simulation. It drops from about 1.3 in neutral atomic gas to about 0.6 in fully ionised gas of solar composition, and it depends on the metallicity: in the thesis problem, metal-rich fountain gas mixes with a metal-poor corona, so $\mu$ varies from cell to cell. The temperature conversion must therefore take $\mu$ as it is, cell by cell, rather than assume a value.

**UNI08.** Temperature converts from the ratio of pressure to density in code units through $T = \mu\, m_\mathrm{H}\, (p/\rho)/k_\mathrm{B}$, and back by the inverse relation. The mean molecular weight $\mu$ is in units of the mass of the hydrogen atom $m_\mathrm{H}$, as is usual in astrophysics. It is an argument of the conversion, a positive finite number given as a scalar or as an array of the shape of the values. It is an argument rather than a property of the unit system, because $\mu$ depends on composition and ionisation, and in astrophysical problems often on metallicity. For values whose magnitude lies between $10^{-100}$ and $10^{100}$, the conversion agrees with its formula, evaluated exactly from the code unit of specific energy and the constants, to within 4 ulp, and a round trip from temperature to $p/\rho$ and back reproduces the temperature to within 6 ulp. *(Changed 2026-10-13: the tolerances were not stated; added when the tests were written.)*
*Rationale:* The ratio $p/\rho$ has the dimensions of a specific energy, so its code unit is that of the square of a velocity, and the conversion to temperature needs only $k_\mathrm{B}$, $m_\mathrm{H}$ and $\mu$ in addition. The tolerances are those of the arithmetic: the conversion takes four roundings, one per multiplication or division, and each is at most one ulp of the result. A round trip takes eight, but the product $\mu\, m_\mathrm{H}$ is the same in both directions and its rounding cancels, which leaves six. The range of values covers every physical temperature by a wide margin, while keeping the intermediate values of the conversion clear of the ends of the range of double precision, where digits would be lost. The mass of the hydrogen atom is the reference most of the astrophysical literature uses for $\mu$, and with it the published values of $\mu$ and the temperatures of cooling tables can be used as they are. The atomic mass unit, the other common choice, is 0.8 % smaller; mixing the two would shift every temperature by that amount, a systematic error that is easy to make and hard to notice. Accepting $\mu$ as an array lets a module compute it per cell, from the local metallicity and ionisation, and convert a whole field of temperatures at once.

**UNI09.** A default mean molecular weight can be given when the unit system is created; a temperature conversion without $\mu$ then uses it. Without a default, a temperature conversion without $\mu$ is refused. No value of $\mu$ is assumed silently.
*Rationale:* Many problems do have a single mean molecular weight, and a default spares them from passing it to every conversion. A default chosen by mhdpy itself, however, would be wrong for many problems without anyone noticing: the common value 0.6 for ionised gas gives temperatures a factor of two too low for neutral gas. Requiring the value to be stated, once at creation or at each conversion, makes the assumption visible in the set-up of every simulation that relies on it.

### Physical constants

Modules with physical content need physical constants: Boltzmann's constant and the mass of the hydrogen atom for temperatures, the gravitational constant for self-gravity, the speed of light and the radiation constant for radiative processes. If each module typed in its own values, two modules could use slightly different values of the same constant, and the results would depend on which module happened to use which. One table of constants, from cited sources, converted to code units by the unit system, rules that out.

Since the redefinition of the SI in 2019, several constants are exact by definition, and their values in cgs follow exactly from the SI values. The other constants are measured, and their recommended values are revised every four years by CODATA. Recording which revision is used (UNI14) keeps results traceable.

**UNI10.** At least the following physical constants are available, in cgs and in code units: the speed of light $c$, the gravitational constant $G$, Boltzmann's constant $k_\mathrm{B}$, Planck's constant $h$, the atomic mass unit $m_\mathrm{u}$, the mass of the hydrogen atom $m_\mathrm{H}$, the proton mass $m_\mathrm{p}$, the electron mass $m_\mathrm{e}$, the Stefan–Boltzmann constant $\sigma_\mathrm{SB}$ and the radiation constant $a_\mathrm{rad}$. Their values are those of CODATA 2022; $m_\mathrm{H}$ is the atomic mass of $^1\mathrm{H}$ of the Atomic Mass Evaluation 2020 in units of $m_\mathrm{u}$. Constants that are exact by the definition of the SI ($c$, $h$, $k_\mathrm{B}$), and those that follow exactly from them ($\sigma_\mathrm{SB}$, $a_\mathrm{rad}$), are the double-precision numbers nearest to their exact values in cgs. Every other constant is the double-precision number nearest to its published value in cgs, and $m_\mathrm{H}$ the one nearest to the exact product of its two published values. Temperatures are in kelvin in both cases: code units have no temperature dimension (see the introduction to the definition), so a constant that contains the kelvin, such as $k_\mathrm{B}$, $\sigma_\mathrm{SB}$ or $a_\mathrm{rad}$, keeps it in code units; $k_\mathrm{B}$ in code units is a code unit of energy per kelvin. *(Changed 2026-10-13: only $c$, $h$ and $k_\mathrm{B}$ were named as exact, although CODATA 2022 lists $\sigma_\mathrm{SB}$ as exact and $a_\mathrm{rad} = 4\sigma_\mathrm{SB}/c$ follows; the nearest double was required for the exact constants only. Found while writing the tests.)*
*Rationale:* The list covers the physics in scope (architecture.md §1.2): temperature and ionisation ($k_\mathrm{B}$, $m_\mathrm{H}$, $m_\mathrm{p}$, $m_\mathrm{e}$), self-gravity ($G$), and radiative processes and cooling ($c$, $h$, $\sigma_\mathrm{SB}$, $a_\mathrm{rad}$). CODATA is the international reference for the values of the fundamental constants, and the Atomic Mass Evaluation for the masses of atoms, which CODATA does not list. For every constant, the nearest double-precision number is the best any program can do, and it makes the values testable bit for bit against their sources. It also means that a constant derived from others, such as $\sigma_\mathrm{SB}$ or $m_\mathrm{H}$, is written out rather than computed from them in double precision: computing it would add rounding errors of its own, of an ulp or so, and the result would depend on the order of the operations. Keeping the kelvin in code units follows from temperature not being a dimension of the code units: there is no code unit of temperature to convert to, and temperatures enter only through the conversion of UNI08.

**UNI11.** At least the following astronomical units are available as constants in cgs: the astronomical unit, parsec, kiloparsec and megaparsec; the solar mass, radius and luminosity; the Julian year, megayear and gigayear; and the kilometre per second. Their values follow the IAU: the astronomical unit of IAU 2012 Resolution B2, the parsec as $648000/\pi$ astronomical units (IAU 2015 Resolution B2), and the nominal solar values of IAU 2015 Resolution B3, with the solar mass derived from the nominal solar mass parameter and $G$ (UNI10). Each is the double-precision number nearest to its exact value in cgs, and the solar mass the one nearest to the exact quotient of the nominal solar mass parameter and $G$. *(Changed 2026-10-13: the precision of the values was not stated; added when the tests were written, as for UNI10.)* A unit system can thus be defined as, for example, $1\,\mathrm{kpc}$, $10^5\,M_\odot$ and $1\,\mathrm{Myr}$.
*Rationale:* Astrophysical problems are posed in astronomical units, not in centimetres and grams, and a unit system is most naturally defined in them. The IAU resolutions fix these units unambiguously: the astronomical unit and the parsec are exact by definition since 2012 and 2015, and the nominal solar values replace the slightly different solar values that circulate in the literature. The solar mass itself is known only through the product $G M_\odot$, which is measured far more precisely than $G$; deriving it from the nominal $G M_\odot$ and the CODATA value of $G$ is the standard procedure, and keeps it consistent with $G$ as used by self-gravity. The nearest double-precision numbers follow UNI10. The kiloparsec and megaparsec are therefore not computed as $10^3$ and $10^6$ parsecs in double precision, which misses the nearest double-precision number for the megaparsec by one digit in the last place.

### Records

The unit system is part of what a simulation is. Outputs record it, so that the values they hold, which are in code units, can be read as physical quantities later (D14.2). Restart files record it, so that a continued run converts exactly as the original did (D13.5). Both require the unit system to be fixed for the whole run and to survive being written to a file and read back without the smallest change.

**UNI12.** A unit system cannot be changed once it is created.
*Rationale:* Every value in code units, every converted parameter and every constant converted at set-up depend on the unit system. Changing it during a run would silently change the meaning of all of them at once, and the constants already converted by modules would no longer match. A different unit system is a different simulation, created anew.

**UNI13.** Two unit systems are equal if and only if their code units of length, mass and time and their default mean molecular weights are equal.
*Rationale:* Equality is how a restart, or a comparison of outputs, checks that it deals with the same unit system. It compares the defining values only, since every derived unit and converted constant follows from them (UNI02, UNI10). The default mean molecular weight is part of the comparison because it changes the result of temperature conversions (UNI09).

**UNI14.** A unit system converts to a record of plain values, for outputs and restart files (D13.5, D14.2), and is created again from such a record. The round trip gives an equal unit system (UNI13), with every value identical bit for bit. The record also names the sources of the constants (CODATA 2022, AME 2020, IAU 2012/2015), so that a file states which values were used.
*Rationale:* A restarted run continues bit for bit only if it converts exactly as before (D02.3, D13.5), so the record must preserve every value exactly; E13.2 showed how a difference in the last digits of a restart file breaks the bit-for-bit continuation. A record of plain values (numbers and text) can be written in any format, HDF5 attributes included. Naming the sources of the constants matters for files read years later: CODATA revises its values every four years, and a file that states which values it used can be interpreted exactly even after mhdpy has moved to a newer revision.

### Dimensionless simulations

Most verification problems (D02), such as shock tubes, blast waves, linear waves and the Orszag–Tang vortex, are dimensionless: their initial conditions and results are given in code units, and physical units would add nothing. Requiring a unit system for them would be pointless. Problems with physical processes, such as cooling, depend on physical constants and cannot run without one. The unit system therefore has to be optional, and the cases that need it have to be recognised before a run starts.

**UNI15.** A simulation without a unit system is dimensionless: it runs, and every quantity stays in code units.
*Rationale:* A dimensionless simulation is a valid simulation, not an incomplete one. Making it the case without a unit system keeps the verification problems, and every user's first steps, free of a choice that does not matter for them.

**UNI16.** A module that needs physical constants or unit conversions declares so as part of its integration contract (D12.1). Setting up a dimensionless simulation (UNI15) with such a module is refused before the run starts, naming the module.
*Rationale:* A module that needs physical constants cannot do anything meaningful in a dimensionless simulation, and the alternatives to refusing are worse. Failing in the middle of a run wastes the run. Silently treating code units as cgs would make a cooling module compute rates for a density of $1\,\mathrm{g\,cm^{-3}}$, which is absurd but might not crash. The integration contract of D12.1 is where a module states what it needs, so the check costs nothing and happens at set-up, and naming the module tells the user which part of the set-up asks for units.

**UNI17.** A problem posed in code units gives the same results whatever unit system is attached to it, or none: its state in code units is identical bit for bit (D12 §4). The unit system changes how values are presented, never how they are computed.
*Rationale:* This is the guarantee that the unit system only translates and never takes part in the computation. It makes the dimensionless verification problems valid for every unit system, and it catches errors in which units leak into the computation, such as a module that converts a value it should not, or a kernel that receives a constant in cgs instead of code units. Because the code-unit state must be identical bit for bit, even a conversion and its inverse applied somewhere along the way would be noticed.

### Dependencies

The functionality required here is small: three numbers, a table of constants, and multiplications and divisions. General-purpose libraries for units, such as astropy's, do much more: they attach units to every array and check dimensions in every operation. That has its place in analysis, but it costs time in every operation and adds a large dependency to the installation (architecture.md §1.3, one command).

**UNI18.** The unit system depends on nothing beyond Python's standard library and NumPy.
*Rationale:* Keeping the unit system free of further dependencies keeps the installation small and fast, and leaves nothing that has to be available for free-threaded Python (D05.4) beyond what mhdpy needs anyway. Its values are plain floats and arrays, so users who prefer astropy's quantities in their analysis can attach units to them themselves.

## Open points

- **Electromagnetic constants.** The elementary charge and other electromagnetic constants have no single cgs value: Gaussian units give the charge in statcoulomb, which differs in dimensions from the SI coulomb. No module needs them yet: hydrodynamics, cooling, conduction, ideal MHD and resistivity (a diffusivity in $\mathrm{cm^2\,s^{-1}}$) do without. When a module first needs them (Hall MHD, ambipolar diffusion, cosmic-ray transport), they are added in Gaussian cgs, consistent with the magnetic field in gauss (UNI07).
- **UNI16 and UNI17** can only be tested once modules and the driver exist; they are stated here because they belong to the unit system's contract.

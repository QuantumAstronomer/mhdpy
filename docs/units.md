# The units

The units give each run the system of code units in which it computes, from three base units given in cgs. They convert into it the values that a declaration names in physical units, and give in it the constants that the physics needs. They are the module `mhdpy.infrastructure.units`, with the frozen dataclass `Units`, the table `NAMED_UNITS` and its entries `NamedUnit`. This document explains the module to a reader new to the repository. The requirements that it meets, with their reasons, are [UNIT01](../design/requirements/infrastructure/units.md#unit01) to [UNIT12](../design/requirements/infrastructure/units.md#unit12) in the [requirements of the units](../design/requirements/infrastructure/units.md), and the decision behind them is taken in [B5D4](../design/briefs/B05-parameters-and-units.md#b5d4-the-system-of-units).

## What the code units serve

A run does not compute without units. It computes in code units, a system of units chosen for each run so that the values of its problem lie near unity. A floor or a tolerance of fixed size then keeps its meaning in every problem, whereas in cgs the corona of the production run, with a density of about $\rho = 10^{-27}\,\mathrm{g\,cm^{-3}}$, would lie nine orders of magnitude below the default floors of Athena++ ([topic 2, §2.2](../design/topics/02-equations-of-state.md#22-the-internal-energy-and-floors)). Each number in code units still stands for a definite amount in cgs, which the base units of the run fix.

By default the code units are those of cgs, so that a run without units of its own, such as a shock tube, computes exactly as in cgs ([UNIT01](../design/requirements/infrastructure/units.md#unit01)). Temperature keeps the kelvin in every system, as mass, length and time give it no scale ([UNIT03](../design/requirements/infrastructure/units.md#unit03)). The temperature of a cell, computed from $p/\rho$ with the constants in code units, therefore comes out in kelvin, in which cooling and conduction take it.

## The base units

A `Units` holds the three base units $M_0$, $L_0$ and $T_0$ of a run, the code units of mass, length and time in grams, centimetres and seconds, as its fields `mass`, `length` and `time`, each 1 by default ([UNIT01](../design/requirements/infrastructure/units.md#unit01)). Athena++ derives every unit from the same three ([Athena 3.1](../design/references/athena-synthesis.md#31-configuration-build-and-the-main-loop)). A run that wants the density $\rho_0$ and the velocity $V_0$ of its flow near unity takes $M_0 = \rho_0 L_0^3$ and $T_0 = L_0/V_0$. A base unit that is not a positive and finite number, such as zero, a negative number, an infinity or a NaN, is refused with a `ValueError` that names the field and its value, so that the fault shows before any block is built ([UNIT02](../design/requirements/infrastructure/units.md#unit02)).

A dimension is a tuple of four integer exponents $(a, b, c, d)$ of mass, length, time and temperature, as $(1, 2, -2, -1)$ for $\mathrm{erg\,K^{-1}}$. The method `code_unit` returns its code unit $M_0^a L_0^b T_0^c$, the size in cgs of one code unit of that dimension, in which the exponent $d$ of temperature takes no part ([UNIT03](../design/requirements/infrastructure/units.md#unit03)). A value in code units, multiplied by the code unit of its dimension, gives the value in cgs.

## The named units

The table `NAMED_UNITS` holds the units that a declaration may name, so that inputs and records read in physical units whatever the system of the run ([UNIT04](../design/requirements/infrastructure/units.md#unit04)). Each entry is a `NamedUnit`, a frozen dataclass of its value in cgs and its dimension:

| Name | Value in cgs | Dimension |
|---|---|---|
| `g` | 1 | $(1, 0, 0, 0)$ |
| `cm` | 1 | $(0, 1, 0, 0)$ |
| `pc` | `constants.PARSEC` | $(0, 1, 0, 0)$ |
| `s` | 1 | $(0, 0, 1, 0)$ |
| `yr` | `constants.JULIAN_YEAR` | $(0, 0, 1, 0)$ |
| `Myr` | `1e6 * constants.JULIAN_YEAR` | $(0, 0, 1, 0)$ |
| `cm/s` | 1 | $(0, 1, -1, 0)$ |
| `km/s` | `1e5` | $(0, 1, -1, 0)$ |
| `g/cm^3` | 1 | $(1, -3, 0, 0)$ |
| `cm^-3` | 1 | $(0, -3, 0, 0)$ |
| `K` | 1 | $(0, 0, 0, 1)$ |
| `erg/cm^3` | 1 | $(1, -1, -2, 0)$ |

These are the units in which the grid, the floors, cooling, conduction and the production problem are expected to declare their parameters, as cells of about 2 pc, a cloud at 75 km/s and a corona of millions of kelvin ([topic 34, §2.6](../design/topics/34-cold-clouds-and-mixing-layers.md#26-fountain-clouds-through-a-corona)). The parsec, the year and the megayear take their values from [the constants](constants.md), so that no digit is repeated where it could drift ([UNIT05](../design/requirements/infrastructure/units.md#unit05)). A number density converts as a unit of $L^{-3}$ alone, as the density that it implies needs the mean mass of a particle, which belongs to the physics. The gram stands in the table for the declaration of the units themselves ([UNIT12](../design/requirements/infrastructure/units.md#unit12)).

The table is fixed in stratum 1, and later briefs add the units that they need in the code. It is read-only, a `MappingProxyType` around its dictionary, so that no module can add to it or change it while a run is built, which would bring back the registry filled at import that [B5D1](../design/briefs/B05-parameters-and-units.md#b5d1-the-declaration-of-parameters) set aside.

The method `factor` returns the factor of a named unit, its value in cgs divided by the code unit of its dimension, by which a value given in that unit is multiplied to give its value in code units ([UNIT06](../design/requirements/infrastructure/units.md#unit06)). The conversion runs one way. No method converts back, as the parameters keep each value as given beside its value in code units ([PARAM09](../design/requirements/infrastructure/parameters.md#param09)), and an output in physical units multiplies by `code_unit` itself. A name that the table does not hold, such as the misspelt `km/sec`, is refused with a `ValueError` that lists the units of the table, which shows the spelling meant ([UNIT07](../design/requirements/infrastructure/units.md#unit07)).

## The constants in code units

A `Units` gives Boltzmann's constant, the mass of the proton, the mass of the electron and the atomic mass unit in code units, as its attributes `boltzmann`, `proton_mass`, `electron_mass` and `atomic_mass_unit`, each the constant in cgs divided by the code unit of its dimension ([UNIT08](../design/requirements/infrastructure/units.md#unit08)). The formulas of cooling and conduction then keep the form of the papers in the code units of the run, as in Athena++. Each is a cached property, computed on its first read and kept in the instance thereafter. The cache is no field, so that the representation, the equality and the declaration of a `Units` hold its base units alone, and a new `Units` computes its own. The astronomical constants enter as named units instead ([UNIT05](../design/requirements/infrastructure/units.md#unit05)).

## The declaration of the table units

`Units` is also the declaration by which the parameters read the base units of a run from the table `units` of its inputs. Its class variable `table` names that table ([UNIT11](../design/requirements/infrastructure/units.md#unit11)), and its fields name their units `g`, `cm` and `s` under the key `unit` of their metadata ([UNIT12](../design/requirements/infrastructure/units.md#unit12)), as [PARAM01](../design/requirements/infrastructure/parameters.md#param01) asks of every declaration. The parameters read this table first and without converting it, and convert every other value by the factors of the units that result ([PARAM07](../design/requirements/infrastructure/parameters.md#param07)). The units read no input themselves.

## What the units leave out

Named systems of units, such as that of Athena++ for the interstellar medium, are left to the brief that first needs one, as the density of such a system rests on the mean mass that the brief on equations of state chooses. The reading of the base units from the inputs and the conversion of each parameter are left to the parameters, and the values of the constants in cgs to the constants. The magnetic field has no named unit yet. The gauss has half-integer exponents in cgs and, in the form in which Athena++ keeps the field, a factor of $\sqrt{4\pi}$ besides, which the brief on magnetic fields settles.

## The form of the module

`NamedUnit` and `Units` are frozen dataclasses, which refuse every assignment after construction, so that the code units of a run cannot change once values have been converted with them. `NamedUnit` compares equal only to another `NamedUnit`, unlike a named tuple, which would compare equal to any tuple of the same values. The class variable `table` is typed `ClassVar`, which keeps it out of the fields and the constructor, and the table is typed `Final`, as the constants are. The base units are checked in `__post_init__`, which the generated constructor calls last. The module relies on the constants and on the standard library alone.

## The tests

The tests in `tests/infrastructure/test_units.py` are grouped in the classes `TestCodeUnits`, `TestNamedUnits`, `TestConstants`, `TestDeclaration` and `TestVerification`, after the five sections of the requirements and in their order. Most take the base units 2 g, 4 cm and 8 s. Products and quotients of powers of two are exact in double precision, so that each expected value, worked out by hand in the comment above it, is compared exactly. The test of the refused base units runs every pair of the three fields and six faulty values, zero of either sign, a negative number, both infinities and a NaN, as a case of its own.

The two tests of verification check the units as a whole. Under the default base units, every factor of the table and every constant in code units equals its value in cgs exactly, as every code unit is a product of powers of 1 ([UNIT09](../design/requirements/infrastructure/units.md#unit09)). The temperature $T = m_\mathrm{u} p/(\rho k_\mathrm{B})$ of a corona, with a pressure of $p = 3 \times 10^{-13}\,\mathrm{erg\,cm^{-3}}$ and a density of $\rho = 10^{-27}\,\mathrm{g\,cm^{-3}}$, comes out the same in code units as in cgs, to a relative difference below $k\epsilon$ with $k = 2^5$, where $\epsilon = 2^{-52}$ is the machine epsilon of double precision ([UNIT10](../design/requirements/infrastructure/units.md#unit10)). It is computed for 336 sets of base units, whose decimal logarithms run over the ranges of UNIT10 with their ends, from the units of the laboratory to those of galaxies, each a case of its own. The worst case lies near twice $\epsilon$, while a factor that multiplies where it should divide errs by many orders of magnitude. Such a factor passes only where the decimal logarithms of length and time are both 25, as the fault then cancels in $p/\rho$, and the grid over the whole range keeps that coincidence from deciding the test. These are the first of the tests of the units against their constants that close stratum 1 ([§3.1 of the overview](../design/overview.md#31-infrastructure)).

## Working with the units

A run of the interstellar medium might take the parsec, the kilometre per second and a density of $\rho_0 = 10^{-24}\,\mathrm{g\,cm^{-3}}$ as its units:

```python
from mhdpy.infrastructure import constants
from mhdpy.infrastructure.units import Units

length = constants.PARSEC
units = Units(mass = 1e-24 * length**3, length = length, time = length / 1e5)

units.factor("pc")        ## 1.0, so that 2 pc are 2.0 in code units
units.factor("km/s")      ## 1.0
units.factor("g/cm^3")    ## 1e24, up to round-off
units.factor("Myr")       ## about 1.02, as the code unit of time is about 0.98 Myr
units.boltzmann           ## Boltzmann's constant in code units
```

Code that computes in code units takes its constants from `Units`, not from the constants in cgs. A new named unit is added to `NAMED_UNITS` with its value in cgs, taken from the constants where they hold it, and its dimension, by the brief that needs it, and the test of verification under cgs checks it with the rest. The tests of the units run alone with:

```bash
uv run pytest tests/infrastructure/test_units.py
```

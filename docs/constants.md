# The constants

The constants are the physical and astronomical constants that the first pass of mhdpy needs, each held in cgs in the module `mhdpy.infrastructure.constants` with the value of its current source. The units build the code units of a run on them, and the physics uses them where it needs a temperature, a number density or a length in parsecs. This document explains the module to a reader new to the repository. The requirements that it meets, with their reasons, are [CONST01](../design/requirements/infrastructure/constants.md#const01) to [CONST07](../design/requirements/infrastructure/constants.md#const07) in the [requirements of the constants](../design/requirements/infrastructure/constants.md), and the decision behind them is taken in [B5D5](../design/briefs/B05-parameters-and-units.md#b5d5-the-constants).

## What the constants serve

The module converts nothing itself. Its values are held in cgs, and their conversion into the code units of a run is left to the units of [B5D4](../design/briefs/B05-parameters-and-units.md#b5d4-the-system-of-units). The class `Units` gives Boltzmann's constant and the three masses in code units ([UNIT08](../design/requirements/infrastructure/units.md#unit08)), and its named units `pc`, `yr` and `Myr` take their values from `PARSEC` and `JULIAN_YEAR`, so that no digit is repeated where it could drift ([UNIT05](../design/requirements/infrastructure/units.md#unit05)).

The physics needs the constants first of all for the temperature. The temperature of every cell follows from $p/\rho$ through $k_\mathrm{B}$ and the mean mass of a particle ([topic 2, §2.1](../design/topics/02-equations-of-state.md#21-the-ideal-and-the-isothermal-gas)), and conduction and cooling act on that temperature ([topic 17, §2.1](../design/topics/17-thermal-conduction.md#21-the-classical-flux-and-its-suppression), [topic 20, §2.1](../design/topics/20-radiative-cooling.md#21-cooling-in-the-equation-of-the-energy)). The masses also give the number densities on which cooling acts. The mass of the electron sets the saturated flux of conduction, which caps the classical flux where the gradient of temperature grows steep ([topic 17, §2.2](../design/topics/17-thermal-conduction.md#22-saturation)). Both the mass of the proton and the atomic mass unit are held, since the brief on equations of state will choose which of them measures the mean mass of a particle.

The module holds what the first pass needs, not every constant of physics. Later briefs add the constants that they need, as self-gravity will add the gravitational constant.

## The physical constants

Boltzmann's constant $k_\mathrm{B}$ and the masses of the proton, $m_\mathrm{p}$, the electron, $m_\mathrm{e}$, and the atomic mass unit, $m_\mathrm{u}$, are constants of physics:

| Name | Value | Unit | Source |
|---|---|---|---|
| `BOLTZMANN` | `1.380649e-16` | erg/K | the SI, exact since 2019 ([CONST01](../design/requirements/infrastructure/constants.md#const01)) |
| `PROTON_MASS` | `1.67262192595e-24` | g | CODATA 2022 ([CONST02](../design/requirements/infrastructure/constants.md#const02)) |
| `ELECTRON_MASS` | `9.1093837139e-28` | g | CODATA 2022 ([CONST03](../design/requirements/infrastructure/constants.md#const03)) |
| `ATOMIC_MASS_UNIT` | `1.66053906892e-24` | g | CODATA 2022 ([CONST04](../design/requirements/infrastructure/constants.md#const04)) |

Since the revision of the SI in 2019, Boltzmann's constant is exact, so that its digits are its definition. The masses are measured, and CODATA 2022 gives their latest values ([Mohr et al.](../design/briefs/B05-parameters-and-units.md#mohr-et-al-2025) 2025). Each mass is its value in kilograms with the exponent raised by three, so that the conversion into grams is made in the digits and rounds nothing.

## The astronomical constants

The astronomical unit, the parsec and the Julian year are fixed by definitions:

| Name | Value | Unit | Source |
|---|---|---|---|
| `ASTRONOMICAL_UNIT` | `1.495978707e13` | cm | Resolution B2 of the IAU of 2012 ([CONST05](../design/requirements/infrastructure/constants.md#const05)) |
| `PARSEC` | `648_000 / math.pi * ASTRONOMICAL_UNIT` | cm | Resolution B2 of the IAU of 2015 ([CONST06](../design/requirements/infrastructure/constants.md#const06)) |
| `JULIAN_YEAR` | `365.25 * 86_400` | s | 365.25 days of 86 400 s ([CONST07](../design/requirements/infrastructure/constants.md#const07)) |

The IAU defines the astronomical unit as 149 597 870 700 m exactly ([IAU 2012](../design/briefs/B05-parameters-and-units.md#iau-2012-b2)). In centimetres it is an integer of fewer than 53 bits, which a double holds exactly. The parsec is defined as $\mathrm{pc} = (648\,000/\pi)\,\mathrm{au}$ exactly ([Mamajek et al.](../design/briefs/B05-parameters-and-units.md#mamajek-et-al-2015) 2015, note 4). The module computes it from that definition rather than holding its digits, and the order of the division and the product moves the result by at most one unit in the last place. The Julian year of 365.25 days of 86 400 s is an integer number of seconds, which a double also holds exactly.

## The choice of sources

[B5D5](../design/briefs/B05-parameters-and-units.md#b5d5-the-constants) weighed two other sources. The values of Athena++ would keep a run of mhdpy from departing from one of Athena++ by its constants, but they date from 1986 and stand in no current table, and Boltzmann's constant among them lies 6.5 parts in a million above its exact value. SciPy keeps the constants of CODATA 2022, but it would join the dependencies at run time with some 70 MB for ten numbers, against [B4D4](../design/briefs/B04-packaging.md#b4d4-the-dependencies). A module of mhdpy gives every value a current source against which its test checks it, at the price of values kept by hand. A new release of CODATA changes the masses in their last digits, which a release of mhdpy takes up and the record of its version names ([B4D6](../design/briefs/B04-packaging.md#b4d6-the-version-and-its-record)).

## The form of the module

Each constant is a float of double precision, under a name in capitals after PEP 8 and typed `Final`. Pyright infers the type `float` from the value, and refuses to bind the name again within the module and where the name is imported, though not through an attribute of the module, as in `constants.PARSEC = 0.0`. Python itself enforces nothing at run time. The unit, the source and the requirement of each constant stand in one comment above it, as `## the mass of the proton in g, after CODATA 2022 (CONST02)`, in the form that [§1 of the rules of the requirements](../design/templates/requirements-rules.md#1-files-and-identifiers) gives a single step. The module relies on the standard library alone, and on `math` for $\pi$.

## The tests

The tests in `tests/infrastructure/test_constants.py` are grouped in the classes `TestPhysical` and `TestAstronomical`, after the two sections of the requirements, and each compares its constant with its source. A value given by its digits is compared exactly, as the same digits in the test and in the module round to the same double, so that a tolerance would only widen what passes. The astronomical unit and the year are compared exactly with their integers, 149 597 870 700 m in centimetres and 31 557 600 s.

The parsec, the one value that the module computes, is compared with its definition to within twice $\epsilon$, where $\epsilon = 2^{-52}$ is the machine epsilon of double precision. The bound admits every order of the operations, while the parsec of nine digits of Athena++, or one of 206 265 astronomical units, fails it by far. The three astronomical tests also require a float, as an integer of the right size passes an exact comparison, and an integer parsec of 19 digits lies within the bound.

The constants have no verification of their own. They meet the criteria of [§1.3 of the overview](../design/overview.md#13-success-criteria) only through the units and the physics that use them, whose tests check them there, the tests of the units against their constants among them ([UNIT09](../design/requirements/infrastructure/units.md#unit09)).

## Working with the constants

The module is imported whole, and each constant is read through it:

```python
from mhdpy.infrastructure import constants

constants.PARSEC
```

Code that computes in the code units of a run takes Boltzmann's constant and the masses from `Units` instead, converted ([UNIT08](../design/requirements/infrastructure/units.md#unit08)). A new constant is added with its unit, source and requirement in the comment above it, and with a test that compares it with its source. The tests of the constants run alone with:

```bash
uv run pytest tests/infrastructure/test_constants.py
```

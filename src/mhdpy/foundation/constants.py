"""Physical constants and astronomical units of mhdpy, in cgs.

One table of constants, from cited sources, serves every module, so that no two modules can use different values of
the same constant. The unit system (``units.py``) converts them to code units. The requirements are UNI10 and UNI11 in
``docs/requirements/L0-foundation/units.md``. Only the constants the temperature conversion (UNI08) needs are here so
far; the others of UNI10 and UNI11 follow with their tests, which are in the accompanying test module
``tests/test_constants.py``.

Each constant is NumPy's double-precision number np.float64, like the units, so that conversions stay in double
precision.
"""

import numpy as np

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["ATOMIC_MASS_UNIT", "BOLTZMANN_CONSTANT", "HYDROGEN_MASS"]

## Boltzmann's constant, exact since the redefinition of the SI in 2019: 1.380649e-23 J/K = 1.380649e-16 erg/K.
BOLTZMANN_CONSTANT = np.float64(1.380649e-16)

## The atomic mass unit (unified atomic mass unit), CODATA 2022: 1.66053906892(52)e-27 kg = 1.66053906892e-24 g.
ATOMIC_MASS_UNIT = np.float64(1.66053906892e-24)

## The mass of the hydrogen atom, the atomic mass of 1H of the Atomic Mass Evaluation 2020, 1.007825031898(14) u,
## converted to grams with the atomic mass unit above.
HYDROGEN_MASS = 1.007825031898 * ATOMIC_MASS_UNIT

"""The unit system of mhdpy, with its notation and the physical constants (requirements UNI01-UNI20).

mhdpy computes in dimensionless code units, and relates them to physical units (cgs) at the edges of a simulation: when
physical values are given, when physics modules receive physical constants, and when outputs label their values. This
package holds everything that relation needs, in three modules that divide the work by what each depends on:

- ``notation.py``, how a unit is written: the unit symbols with their dimensions, the labels of the named units, and
  the reader of values with a unit such as "100 pc". It needs nothing beyond Python's standard library, so that the
  parameters can check the units of their declarations without NumPy (UNI18, PAR21).
- ``constants.py``, the physical constants and astronomical units in cgs, each with its source and its dimensions.
- ``system.py``, the unit system itself: three code units, every unit derived from them, and every conversion, of
  numbers, arrays, temperatures, constants and values with a unit. It needs the constants and NumPy.

The modules are imported by their own names, the unit system as ``from mhdpy.foundation.units.system import
UnitSystem`` and the others as ``from mhdpy.foundation.units import constants, notation``. This file imports none of
them on purpose: Python runs it before any module of the package, so a single import of the unit system here would load
NumPy with the notation as well.

The requirements are in ``docs/requirements/L0-foundation/units.md``, and the tests are in the test package ``tests/``
next to the modules, one test module per group of requirements.
"""

# `mhdpy.foundation`

<!-- Generated from the docstrings of this package and its modules by `uv run nox -s readmes`: edit the docstrings, not this file. `uv run nox` checks that the two agree. -->

Layer L0 of mhdpy, the foundation: the services every other layer builds on.

The foundation is the bottom layer of mhdpy's layered architecture (``docs/architecture.md`` §3). It holds what every
higher layer needs and what depends on nothing above it: the unit system with its notation and the physical constants,
the parameters, and, as they are built, the compute kernels in compiled and uncompiled form, the worker threads and
reductions, and logging. Nothing in this layer knows about meshes, physics modules or simulations.

Each component of the layer is a package of its own, such as ``units`` and ``parameters``, with its tests in a package
``tests/`` next to its modules (D01.4). Every package and module describes its purpose in its docstring. The layer's
``README.md`` collects these docstrings in one place, a section per component; it is generated from them with ``uv run
nox -s readmes``, and ``uv run nox`` checks that the two agree.

## `mhdpy.foundation.parameters`

The parameters of mhdpy: declared, given values, checked and recorded (requirements PAR01-PAR23).

Every choice a run makes is a parameter: the size of the mesh, the Courant number, the Riemann solver, the end time,
the outputs and their schedules, the parameters of a problem's initial conditions. Modules, problems, the driver and the
outputs each declare the parameters they need, with a type, a default, documentation, a unit for every number and,
optionally, a check (D12.1, D15.2). This component resolves the values a run uses from the defaults, a parameter file
in TOML and overrides, refuses every mistake before the run starts, all at once and with a suggestion for a misspelt
name, and records the result exactly, so that outputs describe how they were made and a restart continues with the same
values (D13, D14). Physical values are given with their unit, such as "100 pc", and converted to code units by the unit
system of the run.

The component knows nothing of what the parameters mean. It sits in the foundation (layer L0) because every higher
layer declares parameters, and it depends on nothing beyond Python's standard library and the notation of units
(``mhdpy.foundation.units.notation``), with which it checks the units of declarations. The unit system itself, with
NumPy behind it, is passed in by a run that has one, for the conversions (PAR21).

The component is being built test-first: its requirements are in ``docs/requirements/L0-foundation/parameters.md``,
and its tests, in the test package ``tests/`` next to this file, are written one by one before the code that fulfils
them.

## `mhdpy.foundation.units`

The unit system of mhdpy, with its notation and the physical constants (requirements UNI01-UNI20).

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

### `mhdpy.foundation.units.constants`

Physical constants and astronomical units of mhdpy, in cgs.

Physics modules need physical constants: Boltzmann's constant and the mass of the hydrogen atom for temperatures, the
gravitational constant for self-gravity, the speed of light and the radiation constant for radiative processes. This
module is the one table of them in mhdpy, so that no two modules can use different values of the same constant. Every
value comes from a cited source: CODATA 2022 for the physical constants, the Atomic Mass Evaluation 2020 for the mass of
the hydrogen atom, and the IAU resolutions of 2012 and 2015 for the astronomical units. The sources are named in
``SOURCES``, which the record of a unit system carries into outputs and restart files, so that a file states which
values it was made with even after they have been revised.

The values are in cgs. The unit system (``system.py``) converts a physical constant to code units by its dimensions,
listed in ``DIMENSIONS``; a constant that contains the kelvin keeps it, since code units have no temperature dimension.
The astronomical units serve to define unit systems in the units astrophysical problems are posed in, such as 1 kpc,
1e5 solar masses and 1 Myr; they are not converted to code units themselves.

Every constant is the double-precision number nearest to its value in cgs: the value its source publishes, or, for a
constant derived from published values (such as the parsec or the solar mass), the value derived from them exactly.
Constants are therefore written as literals, with their source and derivation in the comment above them; computing them
here in double precision would add rounding errors of its own. Each is NumPy's double-precision number np.float64,
like the units, so that conversions stay in double precision.

The requirements are UNI10 and UNI11 in ``docs/requirements/L0-foundation/units.md``, tested in
``tests/test_constants.py``.

### `mhdpy.foundation.units.notation`

The notation of units in mhdpy: how a unit is written, and what dimensions it has.

Physical values enter mhdpy as text, written with their unit: a parameter such as a cloud radius of "100 pc" or an
ambient density of "1e-27 g cm^-3" (PAR09). Values leave it with their unit as text too: the headers of the history and
the attributes of outputs label every quantity with its cgs unit, such as "g cm^-3" for a density (D14). Both use one
notation, defined here: a unit expression is one or more factors separated by spaces, each a unit symbol with an
optional exponent written with ^, so that every label mhdpy writes is also a unit a user can write (UNI19).

This module knows how units are written, not what they are worth. It holds the unit symbols with their dimensions, the
labels of the named units, a reader for values with a unit, and the dimensions of a unit expression: everything needed
to check that a value has the right dimensions, and nothing needed to convert it. The values of the symbols in cgs,
which come from the physical constants, and the conversion to code units are the unit system's (``system.py``).

The split is what lets the parameters check their declarations without the unit system (PAR21). A module declares the
unit of each numeric parameter, and the parameters check that a named unit exists and that a default such as "100 pc"
has the dimensions declared, as soon as the module is declared. The unit system, with NumPy behind it, is needed only to
convert, and is passed to the parameters by a run that has one. This module therefore depends on nothing beyond Python's
standard library (UNI18).

For example, reading a value with a unit and finding its dimensions::

    from mhdpy.foundation.units import notation

    number, factors = notation.parse("1e-27 g cm^-3")    ## 1e-27, {"g": 1.0, "cm": -3.0}
    notation.dimensions(factors)                         ## {"mass": 1.0, "length": -3.0}
    notation.LABELS["density"]                           ## "g cm^-3"

The requirements this module fulfils are in ``docs/requirements/L0-foundation/units.md`` (UNI04, UNI18, UNI19, UNI20),
and they are tested with the unit system, in the test package ``tests/`` next to this module.

### `mhdpy.foundation.units.system`

The unit system of mhdpy: the relation between code units and physical units (cgs).

mhdpy computes in dimensionless code units. Every value that kernels, physics modules and the time integration work
with is a multiple of a code unit, and the equations contain no constant that belongs to a particular system of units
(D12). This has three benefits. Values of order unity keep the arithmetic well inside the range of double precision,
even for problems whose values span dozens of orders of magnitude in cgs. The verification problems of the literature
(D02), which are posed in code units, run as they are. And one problem in code units describes a whole family of
physical systems, related by a change of units.

A unit system relates code units to cgs. It is defined by three numbers, the code units of length, mass and time, from
which every other unit follows; the factor 4 pi is absorbed into the magnetic field, so that no 4 pi appears in the
equations either. It converts numbers and arrays between code units and cgs, converts between temperature and the ratio
of pressure to density through the mean molecular weight, and converts the physical constants of ``constants.py`` to
code units. It also converts values written with a unit, such as "100 pc" or "1e-27 g cm^-3", to code units, refusing
a value whose dimensions are not those expected; how such values are written, and their dimensions, is the notation's
(``notation.py``), while their values in cgs and their conversion are the unit system's. It cannot be changed once
created, and it converts to a record of plain values and back, bit for bit.

Within mhdpy, the unit system belongs to the foundation (layer L0) and is used at the edges of a simulation, never in
its computation. Physics modules that need physical constants, such as cooling or self-gravity, receive them converted
to code units at set-up (D12). Outputs and the history record the unit system and label their values with cgs units
(D14), and restart files record it, so that a continued run converts exactly as the original did (D13). A simulation
without a unit system is dimensionless and runs entirely in code units; with one, it computes the same state, bit for
bit (UNI15-UNI17). Physical values enter a run as parameters written with their unit, which the unit system of the run
converts (PAR09).

For example, a unit system of 1 kpc, 1e5 solar masses and 1 Myr, and some of its conversions::

    from mhdpy.foundation.units import constants
    from mhdpy.foundation.units.system import UnitSystem

    system = UnitSystem(length=constants.KILOPARSEC, mass=1e5 * constants.SOLAR_MASS, time=constants.MEGAYEAR)
    density_cgs = density * system.density          ## code units to g cm^-3
    temperature = system.temperature(pressure / density, mu=0.6)
    G = system.constant("GRAVITATIONAL_CONSTANT")   ## G in code units
    radius = system.to_code_units("100 pc", "length")  ## 0.1 in code units of length

The requirements this module fulfils are in ``docs/requirements/L0-foundation/units.md`` (UNI01-UNI20), and they are
tested in the test package ``tests/`` next to this module, one module per group of requirements.

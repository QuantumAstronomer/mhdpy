# `mhdpy.foundation`

<!-- Generated from the docstrings of this package and its modules by `uv run nox -s readmes`: edit the docstrings, not this file. `uv run nox` checks that the two agree. -->

Layer L0 of mhdpy, the foundation: the services every other layer builds on.

The foundation is the bottom layer of mhdpy's layered architecture (``docs/architecture.md`` §3). It holds what every
higher layer needs and what depends on nothing above it: the switch between compiled and uncompiled kernels, the unit
system with its notation and the physical constants, the parameters, and, as they are built, the worker threads and
reductions, and logging. Nothing in this layer knows about meshes, physics modules or simulations.

Each component of the layer is a package of its own, such as ``kernels``, ``units`` and ``parameters``, with its tests
in a package ``tests/`` next to its modules (D01.4). Every package and module describes its purpose in its docstring.
The layer's ``README.md`` collects these docstrings in one place, a section per component; it is generated from them
with ``uv run nox -s readmes``, and ``uv run nox`` checks that the two agree.

## `mhdpy.foundation.kernels`

The kernels of mhdpy, compiled or uncompiled: the switch between the two, and the first kernel (decision D04).

A kernel is a function that does the numerical work on the arrays of a block: a reconstruction, a Riemann solver, an
update. Kernels are written once, as ``.py`` files in Cython's pure Python mode, and run in two ways (D04.1, D04.3).
Compiled, by meson into extension modules, they run at the speed a production run needs; uncompiled, as plain Python,
they can be measured for coverage and stepped through in a debugger. The tests check that both ways give bit-for-bit
identical results. The kernels themselves belong to the layers that use them; this package holds what every kernel
relies on:

- ``mode.py``, the switch: the environment variable ``MHDPY_KERNELS`` selects compiled kernels (the default) or
  uncompiled ones, for the whole package, when mhdpy is imported.
- ``backend.py``, the first and simplest kernel: it reports whether the kernels run compiled, and in doing so shows
  that the build compiles kernels at all.

Like every component, this package imports none of its modules itself; ``mhdpy/__init__.py`` imports the switch, before
any kernel is imported. The tests are in the test package ``tests/`` next to the modules.

### `mhdpy.foundation.kernels.backend`

The first kernel of mhdpy: facts about the compute backend that the rest of the package needs at run time.

This module is compiled by meson like every kernel (D04.1), and it is the simplest one possible: a function that reports
whether it runs compiled. Since all kernels run in the same mode (``mode.py``), that tells the rest of mhdpy, and the
tests, how every kernel runs. It is also the proof that the build compiles kernels at all: a wheel whose kernels failed
to compile would report False here, and its tests would fail.

The type checker reads the stub ``backend.pyi`` next to this file, because it cannot interpret Cython's types in a
kernel's source.

### `mhdpy.foundation.kernels.mode`

The switch between compiled and uncompiled kernels: run mhdpy's kernels compiled (the default) or as plain Python.

Kernels are written in Cython's pure Python mode, so every kernel exists twice in an installation: as a compiled
extension module and as its ``.py`` source, installed next to it under the same name (D04.1). Python always imports the
compiled module. Setting the environment variable ``MHDPY_KERNELS=uncompiled`` before mhdpy is imported makes every
module of mhdpy load from its source instead (D04.3).

The uncompiled kernels are there for checking, not for running simulations. Coverage is measured with them, because
coverage cannot look inside compiled code, and a debugger can step through them; the tests of each kernel check that
both ways give bit-for-bit identical results, comparing the selected kernels with an uncompiled copy loaded next to
them. ``uv run nox`` runs every test both ways and combines the coverage of the two runs (D16).

The switch acts when mhdpy is imported: ``mhdpy/__init__.py`` calls ``install`` before any kernel is imported, and an
unknown value of ``MHDPY_KERNELS`` is refused there and then. The tests are in ``tests/test_backend.py``.

## `mhdpy.foundation.parameters`

The parameters of mhdpy: declared, given values, checked and recorded (requirements PAR01-PAR24).

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

### `mhdpy.foundation.parameters.declarations`

The declarations of parameters: what a module states about each parameter it needs.

A parameter exists in mhdpy because a module declares it (D12.1, D15.2). Its declaration states everything the rest of
mhdpy needs to know about it: its name, the type of its values, its value when nobody sets it, what it means, its unit,
optionally a condition every value must satisfy, and whether it may change when a run is restarted (PAR01). Users never
introduce parameters of their own; they only give values to declared ones, which is what makes it possible to refuse a
misspelt name instead of silently ignoring it (PAR11).

A declaration is checked as soon as it is made, so that a mistake in it is found in the module that made it, by that
module's own tests, rather than in a user's run. The declarations of all the modules in a run are then gathered into
one set, which is checked as a whole: no name may be declared twice, or be the start of another (PAR05).

A quantity that can be given in more than one way is declared as alternatives: named groups of declared parameters,
each of which gives the quantity, one of them the default, such as the density of the ambient medium as a mass density
or from a number density, a temperature and a metallicity (PAR22). Which group a run uses is decided when its
parameters are resolved, by the values it is given; the alternatives are checked with the set they belong to, since
only the set knows which parameters are declared.

Some combinations of values are wrong although each value is valid on its own, such as an inner radius larger than the
outer one. A module declares such a relation as a joint check: the parameters it involves, a condition on their values
and a description of it in words, as for the check of a single parameter (PAR23). The parameters must be declared in
the same set, and the condition is evaluated when the parameters of a run are resolved.

For example, the Courant number of the hydrodynamics::

    from mhdpy.foundation.parameters.declarations import Check, Declarations, Parameter

    cfl = Parameter(
        name="hydro.cfl",
        type=float,
        default=0.4,
        doc="The Courant number: the time step as a fraction of the time a signal takes to cross a cell.",
        unit="dimensionless",
        check=Check(lambda value: 0 < value <= 1, "in (0, 1]"),
        changeable=True,
    )
    declarations = Declarations(parameters=[cfl, ...])

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR01-PAR05,
PAR22-PAR24), and they are tested in ``tests/test_declarations.py``, ``tests/test_alternatives.py`` and
``tests/test_checks.py``.

### `mhdpy.foundation.parameters.resolution`

The resolution of parameters: the values a run uses, from its declarations, a parameter file and overrides.

The values of a run come in layers, each replacing the values of the layer below it for the parameters it gives: the
declared defaults, then a parameter file, then overrides (PAR06). The defaults suit most runs; a parameter file, in
TOML, holds the choices of one run and is kept with it; overrides vary one or two values without editing the file, for a
parameter scan or a quick test. Overrides come from the command line, as strings such as ``"hydro.cfl=0.3"``, or from
Python, as a dictionary; values in strings are read as TOML, the same as in a parameter file, and a value that is not
valid TOML, such as a bare word, as a string (PAR08).

A restarted run continues the original run. The record of the original run's parameters (PAR19), which the restart
file holds, then replaces the defaults as the lowest layer, so that every value not given anew is the one the original
run used, and the group each set of alternatives selected stays selected. A parameter declared since the restart file
was written keeps its default, and a recorded name that is no longer declared is ignored, so that a run can be
continued after its modules were updated; a recorded value that its declaration now refuses is refused with the other
mistakes (PAR15).

A number on its own is a value in code units. A value with a unit, a string such as ``"100 pc"`` given for a number in
any layer, is converted to code units by the unit system of the run (PAR09). It is refused if the run has no unit
system, if the parameter is dimensionless, or if its unit has other dimensions than the parameter's. The unit system is
passed in by the run; this module only asks it for its conversion, and never imports it, nor NumPy behind it (PAR21).

Resolving gives the parameters of the run as one read-only mapping from each name to its value, of its declared type and
in code units, with the value of a list parameter as a tuple, so that no value can be changed once resolved, not even in
place (PAR18). The parameters convert to a record of plain values, every value in code units and the selected groups,
which outputs store as JSON and a restart starts from, exactly (PAR19). The driver (L6) resolves the declarations of all
the modules in a run once, before the run starts, and hands each module the values it declared. Next to the values, the
parameters record the origin of each: the layer it came from, the parameter file by name, and the value as it was given
there, such as ``"100 pc"`` (PAR10). The driver logs the values that are not defaults when a run starts, and every
mistake is reported with its origin (PAR14).

Every value is checked against its declaration before the parameters are returned. A name that no module declared is
refused, with the closest declared name as a suggestion where one is close enough to be a likely misspelling, so that
a misspelt parameter never silently leaves its default in place (PAR11). A value must have its parameter's type, with
one conversion only: an integer given for a float becomes a float; a float is never taken for an integer, a boolean
never for a number, and a string never for anything but a string, or a value with a unit for a number (PAR12). A
value must then satisfy its parameter's check, if one is declared, in code units, and is refused with the condition in
the words of the declaration, such as "'hydro.cfl' must be in (0, 1], got 1.5" (PAR13). Before that check, every
float in code units must be finite, neither infinite nor NaN, as standard JSON, the format of the record, has neither
(PAR24). The mistakes are reported together, as one ParameterError that lists each with its origin (PAR14).

Where a quantity can be given in more than one way, the values a run is given select the group of each set of
alternatives: the group of the parameters given in the parameter file or the overrides, and the default group when
none is. The parameters state the selected groups by the names of their sets, in ``selected``, and the module that
declared the alternatives derives the quantity from the group selected. Values given for the parameters of two groups
are refused, among the other mistakes, since one of them would otherwise be silently ignored (PAR22).

Last, the joint checks are evaluated: the conditions on several parameters together, such as an inner radius smaller
than the outer one, on the values in code units. A joint check is evaluated only once every value it involves has
passed its own checks, so that a mistake is never reported twice, and is refused among the other mistakes with its
description and the values involved (PAR23).

For example, a run with a parameter file, one override and a unit system::

    from mhdpy.foundation.parameters.resolution import resolve

    parameters = resolve(declarations, file="run.toml", overrides=["hydro.cfl=0.3"], units=units)
    parameters["hydro.cfl"]                         ## 0.3
    parameters.origins["hydro.cfl"].source          ## "override"

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR06-PAR15,
PAR18-PAR19, PAR22-PAR24), and they are tested in ``tests/test_supplying_values.py``, ``tests/test_checks.py``,
``tests/test_restarts.py``, ``tests/test_records.py`` and ``tests/test_alternatives.py``.

### `mhdpy.foundation.parameters.values`

The types of the values of parameters: which types a parameter may have, and when a value is of its type.

A parameter's values are of one of four types, bool, int, float and str, or a list of one of them (PAR03): exactly the
types TOML writes without ambiguity and JSON records exactly, so that every value survives a parameter file and a record
unchanged (PAR19, PAR20). Whether a value is of its parameter's type is decided by the same rules everywhere: for a
default when a parameter is declared (PAR03), and for every value a run is given when its parameters are resolved
(PAR12). An integer is accepted for a float, and a string for a number only if it is a value with a unit, such as
``"100 pc"`` (PAR09); a boolean is never accepted for a number, nor a float for an integer. A float must also be
finite, neither infinite nor NaN, which standard JSON, the format of the record, cannot write (PAR24).

The rules live in this module of their own, rather than in either of the modules that apply them, so that the
declarations (``declarations.py``) and the resolution (``resolution.py``) share one copy. Like the rest of the
component, it depends on nothing beyond the standard library and the notation of units (PAR21).

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR03, PAR12, PAR24),
and they are tested through the modules that apply them, in ``tests/test_declarations.py`` and ``tests/test_checks.py``.

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
labels of the named units, a reader for values with a unit, the dimensions of a unit expression, and the dimensions of a
unit as a conversion or a parameter declares it (``"dimensionless"``, a named unit, or dimensions): everything needed to
check that a value has the right dimensions, and nothing needed to convert it. The values of the symbols in cgs, which
come from the physical constants, and the conversion to code units are the unit system's (``system.py``).

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

# `mhdpy.foundation`

<!-- Generated from the docstrings of this package and its modules by `uv run nox -s readmes`: edit the docstrings, not this file. `uv run nox` checks that the two agree. -->

Layer L0 of mhdpy, the foundation: the services every other layer builds on.

The foundation is the bottom layer of mhdpy's layered architecture (``docs/architecture.md`` §3). It holds what every
higher layer needs and what depends on nothing above it: the unit system and the physical constants, and, as they are
built, the compute kernels in compiled and uncompiled form, the worker threads and reductions, the declared parameters
and logging. Nothing in this layer knows about meshes, physics modules or simulations.

Each module of the layer describes its purpose in its docstring. The layer's ``README.md`` collects these docstrings in
one place; it is generated from them with ``uv run nox -s readmes``, and ``uv run nox`` checks that the two agree.

## `mhdpy.foundation.constants`

Physical constants and astronomical units of mhdpy, in cgs.

Physics modules need physical constants: Boltzmann's constant and the mass of the hydrogen atom for temperatures, the
gravitational constant for self-gravity, the speed of light and the radiation constant for radiative processes. This
module is the one table of them in mhdpy, so that no two modules can use different values of the same constant. Every
value comes from a cited source: CODATA 2022 for the physical constants, the Atomic Mass Evaluation 2020 for the mass of
the hydrogen atom, and the IAU resolutions of 2012 and 2015 for the astronomical units. The sources are named in
``SOURCES``, which the record of a unit system carries into outputs and restart files, so that a file states which
values it was made with even after they have been revised.

The values are in cgs. The unit system (``units.py``) converts a physical constant to code units by its dimensions,
listed in ``DIMENSIONS``; a constant that contains the kelvin keeps it, since code units have no temperature dimension.
The astronomical units serve to define unit systems in the units astrophysical problems are posed in, such as 1 kpc,
1e5 solar masses and 1 Myr; they are not converted to code units themselves.

Every constant is the double-precision number nearest to its value in cgs: the value its source publishes, or, for a
constant derived from published values (such as the parsec or the solar mass), the value derived from them exactly.
Constants are therefore written as literals, with their source and derivation in the comment above them; computing them
here in double precision would add rounding errors of its own. Each is NumPy's double-precision number np.float64,
like the units, so that conversions stay in double precision.

The requirements are UNI10 and UNI11 in ``docs/requirements/L0-foundation/units.md``, tested in
``tests/units/test_constants.py``.

## `mhdpy.foundation.units`

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
code units. It also reads values written with a unit, such as "100 pc" or "1e-27 g cm^-3", and converts them to code
units, refusing a value whose dimensions are not those expected. It cannot be changed once created, and it converts to
a record of plain values and back, bit for bit.

Within mhdpy, the unit system belongs to the foundation (layer L0) and is used at the edges of a simulation, never in
its computation. Physics modules that need physical constants, such as cooling or self-gravity, receive them converted
to code units at set-up (D12). Outputs and the history record the unit system and label their values with cgs units
(D14), and restart files record it, so that a continued run converts exactly as the original did (D13). A simulation
without a unit system is dimensionless and runs entirely in code units; with one, it computes the same state, bit for
bit (UNI15-UNI17). Physical values enter a run as parameters written with their unit, which the unit system of the run
converts (PAR09).

For example, a unit system of 1 kpc, 1e5 solar masses and 1 Myr, and some of its conversions::

    from mhdpy.foundation import constants
    from mhdpy.foundation.units import UnitSystem

    system = UnitSystem(length=constants.KILOPARSEC, mass=1e5 * constants.SOLAR_MASS, time=constants.MEGAYEAR)
    density_cgs = density * system.density          ## code units to g cm^-3
    temperature = system.temperature(pressure / density, mu=0.6)
    G = system.constant("GRAVITATIONAL_CONSTANT")   ## G in code units
    radius = system.to_code_units("100 pc", "length")  ## 0.1 in code units of length

The requirements this module fulfils are in ``docs/requirements/L0-foundation/units.md`` (UNI01-UNI20), and they are
tested in the accompanying test package ``tests/units/``, one module per group of requirements.

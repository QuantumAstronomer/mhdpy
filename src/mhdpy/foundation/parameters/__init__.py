"""The parameters of mhdpy: declared, given values, checked and recorded (requirements PAR01-PAR24).

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
"""

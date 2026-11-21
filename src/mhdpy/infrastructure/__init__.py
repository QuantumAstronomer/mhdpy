"""The infrastructure, stratum 1.

The code that every stratum runs on and that knows nothing of grids or physics: the physical and astronomical constants,
the code units of a run and its runtime parameters, the record of its code, the route of the kernels with their
execution in parallel, and the tools of testing. To the strata above, it provides the route in which they write their
loops over cells, compiled by Cython and checked against a version vectorised in NumPy.

The stratum rests on no other, while every stratum above may import it, and its tests lie in tests/infrastructure/. It
is closed by tests of its own: parameters with defaults, overrides and unknown names, a record that gives back every
value of its run, units against their constants, and the tools of testing on sequences of known order.

Contents
========================================================================================================================
constants
    The physical and astronomical constants in cgs, each with the value of its current source.
provenance
    The record of the code that a run uses.
units
    The code units of a run, from its base units in cgs, with the named units and the constants in code units.

Its requirements are in design/requirements/infrastructure/, and §3.1 of design/overview.md sets out the stratum.
"""

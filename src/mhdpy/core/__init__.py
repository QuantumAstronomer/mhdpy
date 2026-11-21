"""The numerical core, stratum 3.

The code that advances the equations of the gas: its variables, equations of state, reconstruction, Riemann solvers,
the integrator, source terms, the coupling of processes within a step, the passive scalar, and open boundaries. To the
physics above, it provides a registration by which a new process adds its source terms without changes to the core,
and to the driver the step that the Courant condition allows.

The stratum rests on the infrastructure and the mesh, while the physics and the driver may import it, and its tests lie
in tests/core/. It is closed by tests of its own: each Riemann solver against the exact solution, each reconstruction
by its order on smooth profiles, and a small loop that steps Sod's shock tube and a linear wave, which must converge at
second order and conserve mass, momentum and energy to round-off on a periodic domain.

Its requirements will lie in design/requirements/core/, and §3.3 of design/overview.md sets out the stratum.
"""

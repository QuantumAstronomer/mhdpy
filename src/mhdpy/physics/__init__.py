"""The physics, stratum 4.

The modules that add processes to the flow: diffusion and thermal conduction, and radiative cooling with the
integration of local, stiff sources. To the driver, it provides the limits that conduction and cooling put on the step
and the quantities of cooling and mixing that the problems record, and to problem setups the parameters of the cooling
table, the conductivity and its saturation.

The stratum rests on the infrastructure, the mesh and the numerical core, while the driver may import it, and its tests
lie in tests/physics/. It is closed by tests of its own, each stepped through a small loop: a Gaussian that diffuses
against its analytic profile, a plane conduction front against the self-similar solution of Reale, and a single cell
that cools against the exact solution for its cooling function.

Its requirements will lie in design/requirements/physics/, and §3.4 of design/overview.md sets out the stratum.
"""

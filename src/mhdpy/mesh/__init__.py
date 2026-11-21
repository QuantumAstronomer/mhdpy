"""The mesh and its data, stratum 2.

The code that holds the state on the grid: coordinates with a geometry kept general, the arrays of the state with room
for the face fields of MHD, and ghost cells with the standard boundaries and their exchange between blocks. To the
numerical core, it provides the cell averages of the conserved and primitive variables, each variable named and indexed
once for every stratum, the fluxes on the faces, and as many ghost cells as the widest stencil needs.

The stratum rests on the infrastructure alone, while the strata above may import it, and its tests lie in tests/mesh/.
It is closed by tests of its own: areas and volumes that sum to those of the domain, ghost cells that each standard
condition fills as its symmetry demands, and a domain split into blocks that fills them as one block would.

Its requirements will lie in design/requirements/mesh/, and §3.2 of design/overview.md sets out the stratum.
"""

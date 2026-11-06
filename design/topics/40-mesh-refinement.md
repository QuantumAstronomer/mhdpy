# Mesh refinement

## 1. Overview

Mesh refinement focuses resolution where the flow needs it, through a hierarchy of grids whose levels are finer by an integer factor and whose cells line up, so that conservation follows from corrections at the interfaces between levels. Grids can refine cell by cell, by patches of any size and shape, or by blocks of fixed size at fixed places; the transfers between levels must conserve where they set active cells, and in MHD keep the field free of divergence. Zingale's text names refinement as a direction for further study and sets out restriction and prolongation for multigrid, which pyro implements, and Athena++ refines by blocks of a tree, statically or adaptively, with flux correction, divergence-preserving prolongation of the field, one time step for all levels and balancing of the load. The blocks and their tree follow in [topic 36, §2.4](36-data-structures.md#24-blocks-of-a-tree), multigrid in [topic 14, §2.3](14-elliptic-solvers.md#23-multigrid) and the parallel decomposition in [topic 42, §2.4](42-parallelisation-and-performance.md#24-parallel-execution).

## 2. Designs

### 2.1 Approaches to refinement

A hierarchy of grids after [Berger and Colella](#berger-colella-1989) (1989) refines each level by an even integer factor over the next coarser one, with cells that line up, which makes conservation natural, and corrections at the interfaces between levels keep them consistent ([Zingale's text](#zingale-2025), §3.5). Of the three common approaches, refinement cell by cell, or by patches of any size and shape after [Berger and Oliger](#berger-oliger-1984) (1984) and Berger and Colella (1989), follows the features of the flow more closely, while refinement by blocks of fixed size at fixed places, as in FLASH and Athena++, is easier to implement and to optimise on parallel machines ([Stone et al.](#stone-et-al-2020) 2020, §2.2). In Athena++ a block refines into four blocks in two dimensions and eight in three, neighbouring blocks may differ by at most one level, and regions of static refinement come from the input file; the tree follows in [topic 36, §2.4](36-data-structures.md#24-blocks-of-a-tree).

Detail: [Zingale 2.2.6](../references/computational-hydrodynamics-synthesis.md#226-beyond-the-uniform-grid), [Athena 3.2](../references/athena-synthesis.md#32-arrays-the-mesh-and-its-blocks), [Athena 3.4](../references/athena-synthesis.md#34-mesh-refinement).

### 2.2 Restriction and prolongation

Restriction moves data to a coarser grid and prolongation to a finer one, and for conserved quantities both should conserve the total (Zingale's text, §9.4.1). In one dimension with a factor of 2, restriction averages two fine cells, and linear reconstruction with the centred slope at the fine centres gives the conservative prolongation $\phi^\mathrm{f}_{2i,\,2i+1} = \phi^\mathrm{c}_i \mp (\phi^\mathrm{c}_{i+1} - \phi^\mathrm{c}_{i-1})/8$ of a quantity $\phi$ of the cells, where the fine cells $2i$ and $2i + 1$ halve the coarse cell $i$; pyro restricts by plain averages of $2 \times 2$ or $4 \times 4$ cells and prolongs with unlimited centred slopes. Athena++ weights by volume and area (Stone et al. 2020, eqs. 2 and 3):

$$U_\mathrm{c} = \sum U_\mathrm{f}\,\frac{\Delta V_\mathrm{f}}{\Delta V_\mathrm{c}}, \qquad B_\mathrm{c} = \sum B_\mathrm{f}\,\frac{\Delta S_\mathrm{f}}{\Delta S_\mathrm{c}},$$

for the conserved variables in cells and the field on the faces shared with the coarse level. Its prolongation reconstructs linearly in several dimensions with slopes limited by minmod, less aggressive than the limiters of the solver, since sharper ones can produce unphysical structures at the boundaries between levels. At these boundaries it prolongs primitive variables, since conserved ones can give negative pressures, while new blocks prolong conserved variables, to conserve, with a floor where the pressure turns negative, which keeps mass and momentum but not the total energy. The field on faces is prolonged after [Tóth and Roe](#toth-roe-2002) (2002): faces on coarse faces are interpolated with limited slopes and keep any value they already have on the fine level, and internal faces follow from requiring each fine cell to keep the divergence of the coarse cell, zero, and the curl on internal edges to match its estimate from the coarse field, which preserves the divergence constraint.

Detail: [Zingale 2.6.5](../references/computational-hydrodynamics-synthesis.md#265-restriction-and-prolongation), [pyro 2.1.4](../references/pyro-synthesis.md#214-restriction-and-prolongation), [Athena 3.4](../references/athena-synthesis.md#34-mesh-refinement).

### 2.3 Communication and flux correction

Most of the complexity of refinement by blocks lies in the communication between levels (Stone et al. 2020, §2.1.3). A block has up to 12 neighbours in two dimensions and 56 in three, and data for a coarser neighbour travel at its resolution through coarse buffers. A finer block fills its ghost cells next to a coarser neighbour as follows.

1. Restrict its active cells that the coarser neighbour needs into its coarse buffer and send them, and receive coarse cells into the buffer.
2. Once all exchanges have completed, fill the cells beside those to be prolonged by restriction where they lie on its own level, since the slopes need them.
3. Convert the coarse conserved variables to primitive ones and apply the physical boundary conditions to the coarse buffer where needed.
4. Prolong the primitive variables into the ghost cells.

Only prolongation waits for all data, which the task lists express directly ([topic 18, §2.4](18-operator-splitting-and-coupling-of-processes.md#24-task-lists)). The fluxes integrated over a face that blocks on different levels share must agree exactly, so that the coarse fluxes are replaced by the sums of the fine fluxes weighted by area, after Berger and Colella (1989), and the electric fields along shared edges by the sums of the fine ones weighted by length, so that the magnetic flux through the shared face evolves consistently.

Detail: [Athena 3.4](../references/athena-synthesis.md#34-mesh-refinement).

### 2.4 Criteria and regridding

A problem enrols a function that flags each block for refinement, derefinement or neither, for instance where the curvature $\max(|\partial_x^2q + \partial_y^2q|\,\Delta x^2/q)$ of a quantity $q$, such as the density or the pressure, exceeds a threshold, after [Matsumoto](#matsumoto-2007) (2007), or where the shear or the relative gradient of the pressure does (Stone et al. 2020, eqs. 25, 27 and 28). After each step the mesh regrids.

1. Gather the flags of all processes; refine flagged blocks unless they lie on the finest level, and derefine a set of siblings only if all have been flagged for a number of steps in a row, ten by default, none lies on the root level and no neighbour is finer.
2. Update the tree and assign the blocks, with their costs, to processes in Z-order.
3. Move blocks that keep their level, prolong the data of a refined block into its children, and restrict the children of a derefined block into their parent.
4. Let new blocks take shared faces of the field from existing neighbours on their level, find their neighbours and exchange their boundaries anew.

All levels advance with one time step. Adaptive steps, $2^l$ times smaller on level $l$, would cut the cell updates by a factor of only about $N/2$ for $N$ levels with equal numbers of cells, need interpolation in time at the boundaries between levels, and hamper optimisation and balancing, although variable steps across levels and within blocks have sped up other codes by about a factor of ten, and may pay off for very deep hierarchies, small refined fractions of the volume or strongly varying steps within a level.

Detail: [Athena 3.4](../references/athena-synthesis.md#34-mesh-refinement).

## 3. Tests

Stone et al. (2020, §3.4) run the linear waves of MHD with one level refined where the perturbation exceeds 90 per cent of its peak, a condition chosen only to exercise the refinement, with blocks of $4^3$ to $64^3$ cells, and measure convergence and the overhead of refinement. A wrong cell at an edge or corner of a block shows as a lack of convergence of the maximum error, which makes the test sensitive. The regression of Athena++ runs a fast wave in two dimensions with two levels and bounds its error and the ratio of maximum to mean error.

The double Mach reflection, the Kelvin–Helmholtz instability in hydrodynamics and MHD, and a three-dimensional blast wave compare adaptive refinement with uniform grids of the same finest resolution, each with its own criterion. [Beckwith and Stone](#beckwith-stone-2011) (2011, §3.6) find the circularly polarised Alfvén wave and the advected field loop essential to verify that prolongation adds no divergence at the boundaries between levels, and relativistic problems test refinement in [topic 25, §3](25-relativistic-mhd.md#3-tests).

Detail: [Athena 3.4](../references/athena-synthesis.md#34-mesh-refinement).

## 4. Assessment

With refinement the linear waves converge at second order, with slightly lower errors than unrefined runs on the same root grid, and PPM lowers them further until the errors of second order of prolongation and restriction dominate (Stone et al. 2020). On four nodes the solver updates $132.5 \times 10^6$ cells per second without and $106.0 \times 10^6$ with refinement, an overhead of about 20 per cent, larger at low resolution and smaller with larger blocks. The double Mach reflection with refinement is essentially indistinguishable from the uniform grid at 4.4 times less cost, and larger blocks shorten the time to solution further. The densities of the Kelvin–Helmholtz instability are indistinguishable, but short sound waves are damped in the coarse regions, so that refinement in this form does not serve where such waves matter, and the blast keeps its symmetry and matches the uniform grid. **[GK]** pyro's transfers ignore the volumes of cells and so conserve only on uniform Cartesian grids. The production runs need no refinement, by the aim of the project, so that refinement lies in the eventual scope. Blocks of equal size, the first step towards it, cost little if a single block is the default ([topic 36, §4](36-data-structures.md#4-assessment)), while the communication between levels, the flux correction and the prolongation of the field carry the real cost in code, and in Python they break into many small operations, one per neighbour and case, each of which pays the fixed overhead of a call, the more so with many small blocks. Open are whether the first layers already provide for blocks of a tree, and which transfers and criteria a later layer of refinement adopts.

## 5. Sources

- <a id="beckwith-stone-2011"></a>Beckwith, K. and Stone, J. M., A second-order Godunov method for multi-dimensional relativistic magnetohydrodynamics, ApJS 193, 6 (2011), [arXiv:1101.3573](https://arxiv.org/abs/1101.3573), [doi:10.1088/0067-0049/193/1/6](https://doi.org/10.1088/0067-0049/193/1/6).
- <a id="berger-colella-1989"></a>Berger, M. J. and Colella, P., Local adaptive mesh refinement for shock hydrodynamics, Journal of Computational Physics 82, 64–84 (1989), [doi:10.1016/0021-9991(89)90035-1](https://doi.org/10.1016/0021-9991%2889%2990035-1).
- <a id="berger-oliger-1984"></a>Berger, M. J. and Oliger, J., Adaptive mesh refinement for hyperbolic partial differential equations, Journal of Computational Physics 53, 484–512 (1984), [doi:10.1016/0021-9991(84)90073-1](https://doi.org/10.1016/0021-9991%2884%2990073-1).
- <a id="matsumoto-2007"></a>Matsumoto, T., Self-gravitational magnetohydrodynamics with adaptive mesh refinement for protostellar collapse, PASJ 59, 905–927 (2007), [doi:10.1093/pasj/59.5.905](https://doi.org/10.1093/pasj/59.5.905).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="toth-roe-2002"></a>Tóth, G. and Roe, P. L., Divergence- and curl-preserving prolongation and restriction formulas, Journal of Computational Physics 180, 736–750 (2002), [doi:10.1006/jcph.2002.7120](https://doi.org/10.1006/jcph.2002.7120).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

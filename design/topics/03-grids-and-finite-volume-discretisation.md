# Grids and the finite-volume discretisation

## 1. Overview

A grid turns the continuous fields of [topic 1](01-equations-and-their-variables.md) into a finite set of numbers, and the finite-volume discretisation turns the conservation laws into an update of those numbers that conserves mass, momentum and energy to round-off. Gridless methods expand the fields in basis functions, as spectral methods do, or carry the mass on particles, as smoothed particle hydrodynamics does. Grids are structured, with one integer index per dimension and a direct map onto arrays, or unstructured, which fit irregular domains at the cost of complex data and slower access to memory. All five references use structured grids, which suit the boxes, discs and spheres of astrophysics. pyro, Ulula and Athena++ store cell averages on uniform grids, Athena++ also on nonuniform ones, while ZEUS uses a staggered mesh that may be nonuniform and may move. Ghost cells and boundaries follow in [topic 4](04-boundary-conditions-and-ghost-cells.md), reconstruction and the fluxes in [topic 6](06-reconstruction-and-limiting.md) and [topic 7](07-riemann-solvers.md), curvilinear grids in [topic 12](12-curvilinear-coordinates.md), mesh refinement in [topic 40](40-mesh-refinement.md) and the decomposition of the domain in [topic 42, §2.4](42-parallelisation-and-performance.md#24-parallel-execution). Among the five references, unstructured grids and the moving Voronoi meshes of codes such as Arepo are only named, by Zingale's text.

## 2. Methods

### 2.1 Differences and stencils

On values $f_i = f(x_i)$ at points of spacing $\Delta x$, Taylor expansion gives the differences of a derivative and their errors ([Zingale's text](#zingale-2025), eqs. 1.4 to 1.8 and 3.10):

$$\left.\frac{\partial f}{\partial x}\right|_i = \frac{f_{i+1} - f_i}{\Delta x} + \mathcal{O}(\Delta x) = \frac{f_{i+1} - f_{i-1}}{2\Delta x} + \mathcal{O}(\Delta x^2), \qquad \left.\frac{\partial^2 f}{\partial x^2}\right|_i \approx \frac{f_{i+1} - 2f_i + f_{i-1}}{\Delta x^2}.$$

The one-sided differences are of first order, with a leading error of $\tfrac{1}{2}\Delta x\,|\partial^2 f/\partial x^2|$, the centred difference of second. Every such difference is a linear combination of nearby values, its stencil, and a higher order generally buys a smaller error with a wider stencil. The centred difference of finite-volume data, which treats the averages as point values at the centres, stays of second order. For a function known analytically, the spacing of a difference balances truncation against round-off, for which $\sqrt{\epsilon}$, with the machine epsilon $\epsilon$, is a good rule of thumb, and differences at two spacings combine into a better one by Richardson extrapolation. **[GK]** The expansions $f_{i\pm1} = f_i \pm \Delta x\,f'_i + \tfrac{1}{2}\Delta x^2 f''_i \pm \tfrac{1}{6}\Delta x^3 f'''_i + \ldots$ give all three: their difference leaves the centred first derivative with the error $\tfrac{1}{6}\Delta x^2 f'''_i$, and their sum the second derivative with an error of order $\Delta x^2$.

Detail: [Zingale 2.1.3](../references/computational-hydrodynamics-synthesis.md#213-differentiation), [Zingale 2.2.3](../references/computational-hydrodynamics-synthesis.md#223-differences-and-stencils).

### 2.2 Grids and their data

Three structured grids hold the data differently (Zingale's text, eqs. 3.1 to 3.4). A finite-difference grid stores point values at $x_i = i\,\Delta x$, with a point on each boundary. A cell-centred grid divides the domain into $N$ cells and stores point values at their centres, $x_i = (i + 1/2)\,\Delta x$. A finite-volume grid has the same layout but stores the cell averages,

$$\langle f\rangle_i = \frac{1}{\Delta x}\int_{x_{i-1/2}}^{x_{i+1/2}} f(x)\,dx,$$

so that $\Delta x\,\langle f\rangle_i$ is the amount of $f$ in the cell. Average and central value agree to second order, $\langle f\rangle_i \approx f(x_i)$, so that pyro does not tell them apart, and its fourth-order methods convert between them ([topic 9, §2.1](09-methods-of-higher-order.md#21-averages-point-values-and-quadrature)). **[GK]** The Taylor expansion inside the integral gives $\langle f\rangle_i = f(x_i) + (\Delta x^2/24)\,f''(x_i) + \mathcal{O}(\Delta x^4)$.

An interpolation on a finite-volume grid must be conservative: averaged over a cell, it returns the average of that cell. The parabola through three neighbouring averages is (eqs. 3.5 to 3.9)

$$f(x) = \langle f\rangle_i - \frac{\delta^2 f_i}{24} + \frac{\langle f\rangle_{i+1} - \langle f\rangle_{i-1}}{2\Delta x}\,(x - x_i) + \frac{\delta^2 f_i}{2\Delta x^2}\,(x - x_i)^2, \qquad \delta^2 f_i = \langle f\rangle_{i+1} - 2\langle f\rangle_i + \langle f\rangle_{i-1}.$$

**[GK]** The term $-\delta^2 f_i/24$ makes it conservative: the square $(x - x_i)^2$ averages to $\Delta x^2/12$ over the cell, so that the last term contributes $+\delta^2 f_i/24$ to the average, which the constant cancels.

pyro and Ulula lay out $n_x$ uniform cells between the bounds $x_\mathrm{min}$ and $x_\mathrm{max}$ of the domain, of width $\Delta x = (x_\mathrm{max} - x_\mathrm{min})/n_x$, with $n_\mathrm{g}$ ghost cells on each side, so that cell $i$ is centred at $x_\mathrm{min} + (i - n_\mathrm{g} + 1/2)\,\Delta x$. Ulula's cells are square, and a single row of cells makes its domain one-dimensional.

Detail: [Zingale 2.2.1](../references/computational-hydrodynamics-synthesis.md#221-discretisation), [Zingale 2.2.2](../references/computational-hydrodynamics-synthesis.md#222-grids-and-their-data), [pyro 2.1.1](../references/pyro-synthesis.md#211-the-finite-volume-grid), [Ulula 2.2.1](../references/ulula-synthesis.md#221-the-domain-and-its-cells).

### 2.3 The conservative update

Integrating the conservation law over a cell turns it into an equation for the cell average, driven by the fluxes through its faces (Zingale's text, eqs. 3.11 to 3.14):

$$\frac{d\langle\mathbf{U}\rangle_i}{dt} = -\,\frac{\mathbf{F}_{i+1/2} - \mathbf{F}_{i-1/2}}{\Delta x}.$$

Neighbouring cells share each face flux with opposite signs, so that the sum over all cells telescopes and the conserved quantities change only by the fluxes through the boundary. Conservation is not accuracy, however: fluxes drawn from a random number generator would conserve just as well.

Integrating over a time step as well gives the update of Athena, and with the sources that of Ulula, exact as it stands ([Stone et al.](#stone-et-al-2008) 2008, eqs. 11 to 15; [Diemer](#diemer-2025) 2025, eq. 6):

$$\mathbf{U}^{n+1}_{i,j,k} = \mathbf{U}^{n}_{i,j,k} - \frac{\Delta t}{\Delta x}\left(\mathbf{F}^{n+1/2}_{i+1/2} - \mathbf{F}^{n+1/2}_{i-1/2}\right) - \frac{\Delta t}{\Delta y}\left(\mathbf{G}^{n+1/2}_{j+1/2} - \mathbf{G}^{n+1/2}_{j-1/2}\right) - \frac{\Delta t}{\Delta z}\left(\mathbf{H}^{n+1/2}_{k+1/2} - \mathbf{H}^{n+1/2}_{k-1/2}\right) + \Delta t\,\mathbf{S}^{n+1/2}_{i,j,k}.$$

Here $\mathbf{U}^n_{i,j,k}$ is the average over the cell, and each flux the average over its face and over the step. The superscript $n + 1/2$ marks that average in time, not a value at $t^{n+1/2}$, and a method lies wholly in how it approximates the averaged fluxes and sources. To second order, the averages equal the fluxes at the centres of the faces at the midpoint of the step (Zingale's text, eq. 5.41). Two routes reach second order in time: a predictor gives the states at the half step, or the method of lines integrates the semi-discrete equation as a system of ordinary differential equations ([topic 8](08-time-integration.md)). One step of the scheme runs as follows.

1. Reconstruct from the averages $\mathbf{U}^n_i$ the states on either side of each face, $\mathbf{W}_{\mathrm{L},i+1/2}$ and $\mathbf{W}_{\mathrm{R},i+1/2}$ ([topic 6](06-reconstruction-and-limiting.md)).
2. Approximate the flux averaged over each face and the step, $\mathbf{F}^{n+1/2}_{i+1/2}$, by a Riemann solver between the two states ([topic 7](07-riemann-solvers.md) and [topic 8](08-time-integration.md)).
3. Update every cell by the differences of its face fluxes and the sources, as above.

pyro, Ulula and Athena++ share this update. Athena++ stores the averages at the centres of the volumes, which in curvilinear coordinates differ from the geometric centres ([topic 12, §2.2](12-curvilinear-coordinates.md#22-finite-volumes-and-geometric-source-terms)), and holds the magnetic field as averages over the faces, for constrained transport ([topic 11, §2.1](11-constrained-transport.md#21-the-staggered-field)).

Detail: [Zingale 2.2.4](../references/computational-hydrodynamics-synthesis.md#224-conservation), [Zingale 2.3.7](../references/computational-hydrodynamics-synthesis.md#237-finite-volume-advection), [Zingale 2.3.13](../references/computational-hydrodynamics-synthesis.md#2313-finite-volumes-in-several-dimensions), [Ulula 2.3.1](../references/ulula-synthesis.md#231-the-godunov-update), [Athena 2.1.3](../references/athena-synthesis.md#213-the-finite-volume-discretisation).

### 2.4 The staggered mesh

ZEUS places its variables on a staggered mesh ([Stone and Norman](#stone-norman-1992a) 1992a, §4.1). An a-mesh holds the faces and a b-mesh the centres of the zones, and the spacings of both may be chosen freely, which allows nonuniform grids. Scalars, such as the density and the internal energy, sit at the centres, the components of vectors on the faces normal to them, and the off-diagonal components of tensors of rank two at the corners. Scalars and vectors share indices: the face that carries the index of a zone lies at its smaller coordinate, so that ZEUS's $x1a_i$ is $x_{i-1/2}$ here and its $v1_{i,j}$ is $v_{x,i-1/2,j}$. The dynamics is 2.5-dimensional: every variable depends on two coordinates, but vectors keep their third component, as rotating flows and the full set of MHD waves require. Two rows of ghost zones lie beyond each boundary.

The staggering centres most differences, and the transport step needs fewer interpolations, as the velocities on the faces give the flux into or out of a zone directly. Forming the momentum from density and velocity needs averages instead, and some boundary conditions become harder to apply.

Detail: [ZEUS 2.2.1](../references/zeus-synthesis.md#221-the-staggered-mesh).

### 2.5 Nonuniform and moving grids

ZEUS chooses its spacings freely, but the grid must stay orthogonal, so that a spacing chosen in $x$ holds across the whole range in $y$ ([Stone and Norman](#stone-norman-1992a) 1992a, §4.1). Index ranges that vary along the other direction let a domain leave out a corner, such as the region around a central object. The mesh may also move against the background, with grid velocities $v_\mathrm{g}$ on the faces, prescribed freely or following the fluid on a strip of zones, which makes the code semi-Lagrangian. To stay orthogonal, the grid velocity along $x$ may vary only with $x$. The methods of Athena extend to nonuniform grids, and Athena++ provides them, with cell sizes that vary smoothly along each dimension independently, uniform and logarithmic spacings built in and others supplied by the user. A fixed grid and a grid that follows the fluid are the special cases $dx/dt = 0$ and $dx/dt = v_x$ of the derivative $df/dt = \partial f/\partial t + (\partial f/\partial x)\,dx/dt$ along a path: the Eulerian frame, and the Lagrangian frame with $D/Dt = \partial/\partial t + v_x\,\partial/\partial x$ ([Zingale's text](#zingale-2025), eqs. 4.19 and 4.20).

On a moving grid the fluxes carry the velocity relative to the grid, and every variable is transported consistently with the mass, after [Norman, Wilson and Barton](#norman-et-al-1980) (1980). The flux of each variable is built from the mass flux, which limits the damage that numerical diffusion does to its local conservation, notably of the specific angular momentum. A sweep along $x$ runs as follows (Stone and Norman 1992a, eqs. 51, 52, 55 and 57 to 64).

1. Interpolate the density to the faces, $\rho_{i-1/2}$ ([topic 6](06-reconstruction-and-limiting.md)).
2. Form the mass flux relative to the grid, $\dot M_{i-1/2} = \rho_{i-1/2}\,(v_{x,i-1/2} - v_{\mathrm{g},i-1/2})$.
3. Update the mass $\rho V$ of each zone with the fluxes $\dot M A$, with the factors of the face areas $A_{i\mp1/2}$ that depend on $x$ centred in time and that of the volume $V$ at the new time, while the factors along $y$ wait for the sweep along $y$.
4. Transport every other quantity with the flux of its interpolated specific value times $\dot M A$, such as $e_{i-1/2}\,\dot M_{i-1/2}\,A_{i-1/2}$ for the internal energy.
5. Move the faces and centres by the grid velocities once the step is complete.

The momenta along $x$ and $y$ live on faces, so that their control volumes are shifted by half a zone in their own direction and their mass fluxes are averages of neighbouring ones, while the third component sits at the centre, as the density does, with its control volume and mass flux.

Detail: [ZEUS 2.2.1](../references/zeus-synthesis.md#221-the-staggered-mesh), [ZEUS 2.2.2](../references/zeus-synthesis.md#222-domains-and-grid-motion), [ZEUS 2.4.3](../references/zeus-synthesis.md#243-fluxes-on-a-moving-grid-and-consistent-transport), [Zingale 2.3.5](../references/computational-hydrodynamics-synthesis.md#235-eulerian-and-lagrangian-frames), [Zingale 2.2.6](../references/computational-hydrodynamics-synthesis.md#226-beyond-the-uniform-grid), [Athena 2.1.3](../references/athena-synthesis.md#213-the-finite-volume-discretisation), [Athena 2.8.1](../references/athena-synthesis.md#281-grids-and-geometry).

## 3. Assessment

Stone et al. (2008) keep Athena at second order because higher orders improve the accuracy mainly in smooth flow and combine poorly with mesh refinement, and because [Greenough and Rider](#greenough-rider-2003) (2003) found a Godunov scheme of second order more accurate for its cost than a WENO scheme of fifth order on tests in one dimension. Stone and Norman judge the advantages of the staggered mesh to outweigh its averages, although these can limit the accuracy and the rate of convergence ([Stone and Norman](#stone-norman-1992b) 1992b), and they call their orthogonal moving grid less general than truly two-dimensional adaptive meshes. **[GK]** Cell averages on a structured grid are the natural choice for Godunov schemes: conservation to round-off is built in, the data map onto arrays that vectorise well, and the distinction between average and central value matters only above second order. A staggered mesh suits the magnetic field, whose constrained transport is most compact with its components on the faces ([topic 11, §2.1](11-constrained-transport.md#21-the-staggered-field)), but in hydrodynamics it costs the averages that the cell-centred layout avoids. Nonuniform spacing along each axis costs little and puts resolution where it is needed, whereas a moving grid adds work to every flux and pays off only for flows that a grid can follow, such as a collapse. Open are whether the grid supports nonuniform spacing from the start, which coordinates the cell average is centred on in curvilinear geometry, and whether any variable besides the magnetic field is staggered.

## 4. Sources

- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="greenough-rider-2003"></a>Greenough, J. A. and Rider, W. J., A quantitative comparison of numerical methods for the compressible Euler equations: fifth-order WENO and piecewise-linear Godunov, Journal of Computational Physics 196, 259–281 (2003), [doi:10.1016/j.jcp.2003.11.002](https://doi.org/10.1016/j.jcp.2003.11.002). **[GK]** Crossref dates the volume to 2004.
- <a id="norman-et-al-1980"></a>Norman, M. L., Wilson, J. R. and Barton, R. T., A new calculation on rotating protostar collapse, ApJ 239, 968–981 (1980), [doi:10.1086/158185](https://doi.org/10.1086/158185).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

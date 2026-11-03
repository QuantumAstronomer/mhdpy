# Multidimensional and astrophysical MHD

## 1. Overview

The tests of MHD beyond one dimension fall into two kinds. ZEUS-2D draws on astrophysical solutions that are analytic or semi-analytic: a magnetised stellar wind through its critical points, an expanding coronal transient, and the magnetic braking of a rotating disc, which test curvilinear geometry, rotation and boundaries as well as the MHD. Athena runs the standard problems of multidimensional MHD, the vortex of Orszag and Tang, the rotor, blast waves in strong fields, current sheets and a magnetised Rayleigh–Taylor instability, which test robustness, symmetry and dissipation without exact solutions. CT and the advected field loop follow in topic 10, linear and Alfvén waves in topic 26 and the MHD shock tubes in topic 27.

## 2. Problems

### 2.1 The Weber–Davis wind

The wind of [Weber and Davis](#weber-davis-1967) (1967), a magnetised stellar wind in the equatorial plane, follows from four conservation laws and flux freezing as a contour of a Bernoulli function that passes smoothly through the slow, Alfvén and fast critical points ([Stone and Norman](#stone-norman-1992b) 1992b, §4.3). The contour has no analytic form, and root finding must trace it from radius to radius without diverging onto inadmissible roots, after [Sakurai](#sakurai-1985) (1985). ZEUS-2D runs two solutions on 100 radial zones in a strip about the equator, filling the grid at the start or growing the wind from the inner boundary into vacuum. The wind tests the rotational terms of the equations and the passage through critical points, and also served the convergence studies of topic 26.

Detail: [ZEUS 2.9.3](../references/zeus-synthesis.md#293-the-weberdavis-wind).

### 2.2 The coronal transients of Low

The analytic, time-dependent models of [Low](#low-1984) (1984) describe a hot, magnetised bubble driven into an unmagnetised ambient corona, with a strong shock ahead of a contact surface and a self-similar coasting flow behind (Stone and Norman 1992b, §4.4). They serve as a fully two-dimensional test, since multidimensional winds have no usable solutions. ZEUS-2D initialises one of Low's solutions on $128 \times 80$ zones in spherical polar coordinates over the full range of polar angle, to check that the equatorial symmetry is kept, with the inner boundary following the analytic solution, and compares at the time of Low's last plot. Gravity is ignored beyond the shock, as the pressure of the ambient medium is not given.

Detail: [ZEUS 2.9.5](../references/zeus-synthesis.md#295-the-coronal-transients-of-low).

### 2.3 Magnetic braking of an aligned rotator

A disc threaded by an axial field and set rotating launches torsional Alfvén waves that spin up the ambient medium and brake the disc, with the exact time-dependent solution of [Mouschovias and Paleologou](#mouschovias-paleologou-1980) (1980) for any ratio of densities (Stone and Norman 1992b, §4.5). ZEUS-2D runs it with a density ratio of 10 on 300 zones, 20 of them in the disc, with continuous and discontinuous initial conditions and small amplitudes, and repeats it over many braking times and in spherical polar coordinates, where the waves cross the grid lines. It tests the propagation of torsional Alfvén waves and the transparency of the boundaries to them. Athena reproduces these nonlinear Alfvén waves accurately and converges at second order on the continuous version ([Stone et al.](#stone-et-al-2008) 2008, §8.4).

Detail: [ZEUS 2.9.6](../references/zeus-synthesis.md#296-magnetic-braking-of-an-aligned-rotator), [Athena 2.16.6](../references/athena-synthesis.md#2166-mhd-in-two-and-three-dimensions).

### 2.4 The vortex of Orszag and Tang

The vortex of [Orszag and Tang](#orszag-tang-1979) (1979) sets a periodic square with uniform density and pressure, a vortical velocity and a field from a vector potential of two cosines, by now a standard test, although the times of comparison vary in the literature. Athena runs it on $192 \times 192$ cells and compares slices of the pressure with a solution on $512^2$ cells, which gives the most demanding comparison between methods in it (Stone et al. 2008, §8.4). The problem generator of Athena++ centres the domain on the origin, so that its symmetry can be exact.

Detail: [Athena 2.16.6](../references/athena-synthesis.md#2166-mhd-in-two-and-three-dimensions).

### 2.5 The rotor

The rotor of [Balsara and Spicer](#balsara-spicer-1999) (1999) spins a dense disc in the plane of a field perpendicular to its axis, so that the shear at its edge launches strong rotational discontinuities and its expansion under unbalanced centrifugal forces drives shocks and rarefactions. Athena runs the harder first rotor of [Tóth](#toth-2000) (2000), without smoothing at the edge of the disc, on $400 \times 400$ cells with reconstruction of third order and Roe's solver. Concentric contours of the Mach number in the central rarefaction and a constant field inside it test the symmetry and the absence of oscillations.

Detail: [Athena 2.16.6](../references/athena-synthesis.md#2166-mhd-in-two-and-three-dimensions).

### 2.6 Blast waves in strong fields

A blast wave after [Londrillo and Del Zanna](#londrillo-del-zanna-2000) (2000) expands from an overpressured circle into gas threaded by a field along the diagonal of the grid. Athena compares the hydrodynamic version with one in a field and lets the outgoing wave re-enter through periodic boundaries, runs isothermal versions with a plasma beta of 2 and 0.02, and repeats the adiabatic blast in three dimensions on $200 \times 300 \times 200$ cells. [Gardiner and Stone](#gardiner-stone-2005) (2005, §5.6) run the case of a pressure ratio of 100 and a beta of 0.02 outside, which tests strong slow shocks at low beta.

Detail: [Athena 2.16.6](../references/athena-synthesis.md#2166-mhd-in-two-and-three-dimensions).

### 2.7 Current sheets

Two current sheets in a periodic square, with a field reversing across them, a plasma beta of 0.2 and a small transverse velocity, start as nearly linear Alfvén waves until reconnection and nonlinear effects take over (Gardiner and Stone 2005, §5.5). Reconnection measures the numerical resistivity directly, the released energy drives waves that seed further reconnection, and magnetic islands form and merge, so that strong compressions occur while the topology of the field changes. Larger velocities or lower pressures make the problem harder, and the relativistic variant tests robustness in topic 22.

Detail: [Athena 2.16.6](../references/athena-synthesis.md#2166-mhd-in-two-and-three-dimensions).

### 2.8 The magnetised Rayleigh–Taylor instability and the magnetised Noh problem

A single mode of the Rayleigh–Taylor instability with a horizontal field of 0.05 times the field that suppresses it shows how the field changes the nonlinear evolution, and demonstrates adaptive refinement in Athena with five levels and a passive contaminant (Stone et al. 2008, §8.4). Athena++ also sets the magnetised Noh problem of a Z pinch, whose self-similar solutions [Velikovich et al.](#velikovich-et-al-2012) (2012) derived, in Cartesian or cylindrical coordinates, but no regression test runs it.

Detail: [Athena 2.16.6](../references/athena-synthesis.md#2166-mhd-in-two-and-three-dimensions).

## 3. Assessment

The Weber–Davis wind follows the semi-analytic solution very closely in all variables but the rotational velocity, whose error stays below 1 per cent and comes from wrong slopes at the inner boundary; the results are identical whether the wind starts on the grid or grows from the boundary, and the code carries it through the critical points from submagnetosonic inflow to supermagnetosonic outflow (Stone and Norman 1992b). Low's transient agrees well, with final errors of at most 6.2 per cent in the density, 6.9 in the radial velocity and 3.1 and 9.5 in the radial and toroidal field, dominated by a wave of error from the initial discontinuities and by the outflow boundary, which handles submagnetosonic outflow poorly. The braking agrees excellently with the analytic solution, with discontinuities about 14 zones wide with van Leer interpolation and six with PPA, and only the method of characteristics among the schemes tried gives suitable results; outflow boundaries are perfectly transparent to the torsional waves. The vortex of Orszag and Tang keeps its symmetry but seems not to discriminate strongly between algorithms, which the authors measure better by linear waves, Alfvén waves and the field loop (Stone et al. 2008). The rotor comes out nearly perfectly symmetric and free of oscillations, and the blast waves keep their symmetry exactly under CTU, the field suppressing the Richtmyer–Meshkov fingers that the hydrodynamic version raises, and stay robust at a beta of 0.02. In the current sheets, the field reconnects mostly where it lies oblique to the grid, and the islands merge until two remain on each sheet, a problem that discriminates usefully between algorithms (Gardiner and Stone 2005). The field suppresses the secondary Kelvin–Helmholtz instabilities of the Rayleigh–Taylor instability, and refinement concentrates where it is needed, near the interface. **[GK]** The tests of ZEUS-2D probe what tests of planar MHD do not, rotation, curvilinear grids, critical points and boundaries, and their analytic solutions make them quantitative, while the standard two-dimensional problems of Athena test robustness and symmetry qualitatively. The current sheets measure numerical resistivity, which sets reconnection wherever explicit resistivity is absent. MHD lies outside the production runs but inside the scope from the start, so that these problems define the suite against which the MHD layer of mhdpy is later verified.

## 4. Sources

- <a id="balsara-spicer-1999"></a>Balsara, D. S. and Spicer, D. S., A staggered mesh algorithm using high order Godunov fluxes to ensure solenoidal magnetic fields in magnetohydrodynamic simulations, Journal of Computational Physics 149, 270–292 (1999), [doi:10.1006/jcph.1998.6153](https://doi.org/10.1006/jcph.1998.6153).
- <a id="gardiner-stone-2005"></a>Gardiner, T. A. and Stone, J. M., An unsplit Godunov method for ideal MHD via constrained transport, Journal of Computational Physics 205, 509–539 (2005), [arXiv:astro-ph/0501557](https://arxiv.org/abs/astro-ph/0501557), [doi:10.1016/j.jcp.2004.11.016](https://doi.org/10.1016/j.jcp.2004.11.016).
- <a id="londrillo-del-zanna-2000"></a>Londrillo, P. and Del Zanna, L., High-order upwind schemes for multidimensional magnetohydrodynamics, ApJ 530, 508–524 (2000), [doi:10.1086/308344](https://doi.org/10.1086/308344).
- <a id="low-1984"></a>Low, B. C., Self-similar magnetohydrodynamics. IV. The physics of coronal transients, ApJ 281, 392–412 (1984), [doi:10.1086/162110](https://doi.org/10.1086/162110).
- <a id="mouschovias-paleologou-1980"></a>Mouschovias, T. Ch. and Paleologou, E. V., Magnetic braking of an aligned rotator during star formation: an exact, time-dependent solution, ApJ 237, 877–899 (1980), [doi:10.1086/157936](https://doi.org/10.1086/157936).
- <a id="orszag-tang-1979"></a>Orszag, S. A. and Tang, C.-M., Small-scale structure of two-dimensional magnetohydrodynamic turbulence, Journal of Fluid Mechanics 90, 129–143 (1979), [doi:10.1017/S002211207900210X](https://doi.org/10.1017/S002211207900210X).
- <a id="sakurai-1985"></a>Sakurai, T., Magnetic stellar winds: a 2-D generalization of the Weber–Davis model, A&A 152, 121–129 (1985), [1985A&A...152..121S](https://ui.adsabs.harvard.edu/abs/1985A%26A...152..121S/abstract).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="toth-2000"></a>Tóth, G., The $\nabla \cdot \mathbf{B} = 0$ constraint in shock-capturing magnetohydrodynamics codes, Journal of Computational Physics 161, 605–652 (2000), [doi:10.1006/jcph.2000.6519](https://doi.org/10.1006/jcph.2000.6519).
- <a id="velikovich-et-al-2012"></a>Velikovich, A. L., Giuliani, J. L., Zalesak, S. T., Thornhill, J. W. and Gardiner, T. A., Exact self-similar solutions for the magnetized Noh Z pinch problem, Physics of Plasmas 19, 012707 (2012), [doi:10.1063/1.3678213](https://doi.org/10.1063/1.3678213).
- <a id="weber-davis-1967"></a>Weber, E. J. and Davis, L., Jr., The angular momentum of the solar wind, ApJ 148, 217–227 (1967), [doi:10.1086/149138](https://doi.org/10.1086/149138).

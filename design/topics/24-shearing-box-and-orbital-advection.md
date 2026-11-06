# The shearing box and orbital advection

## 1. Overview

The shearing box follows a small patch of a differentially rotating disc in a Cartesian frame that corotates with the disc at a radius $r_0$, with $x$ radial, $y$ azimuthal and $z$ vertical. Tidal and Coriolis forces replace the curvature of the orbits, and radial boundaries that are periodic but shifted by the shear replace the rest of the disc. The model cannot give global properties such as the rate of accretion, but serves as a laboratory for local dynamics such as the magnetorotational instability (MRI), to which [Hawley, Gammie and Balbus](#hawley-et-al-1995) (1995) introduced it. Athena integrates its source terms so that epicycles and energy are conserved, corrects its boundaries so that the net vertical flux is conserved, and removes the orbital motion from the time step by orbital advection built on CT ([Stone and Gardiner](#stone-gardiner-2010) 2010). Athena++ implements the same algorithms, with source terms of its own in each stage and orbital advection for global discs as well. No other reference treats the shearing box. The rotating frame in curvilinear coordinates follows in topic 13, CT in topic 11 and the particles in the box in topic 22.

## 2. Methods

### 2.1 The equations of the shearing box

In the frame that corotates at $\Omega_0 = \Omega(r_0)$, the momentum and energy equations of ideal MHD gain the tidal and vertical gravity and the Coriolis force (Stone and Gardiner 2010, eqs. 1 to 6):

$$\frac{\partial(\rho\mathbf{v})}{\partial t} + \nabla\cdot\mathsf{M} = \rho\Omega_0^2(2qx\,\hat{\mathbf{x}} - z\,\hat{\mathbf{z}}) - 2\Omega_0\hat{\mathbf{z}}\times\rho\mathbf{v}, \qquad \frac{\partial E}{\partial t} + \nabla\cdot\mathbf{F}_E = \rho\Omega_0^2\,\mathbf{v}\cdot(2qx\,\hat{\mathbf{x}} - z\,\hat{\mathbf{z}}),$$

with the momentum tensor $\mathsf{M}$ of topic 12 and the energy flux $\mathbf{F}_E$ of MHD. The shear parameter $q = -\tfrac{1}{2}\,d\ln\Omega^2/d\ln r$ is 3/2 for Keplerian flow. The equations admit the uniform orbital motion $\mathbf{v}_\mathrm{K} = -q\Omega_0x\,\hat{\mathbf{y}}$, steady and varying with $x$ alone, on which orbital advection rests. Most difficulties come from the tidal and Coriolis terms in the orbital plane, so that these and the vertical gravity are treated apart.

Detail: [Athena 2.9.2](../references/athena-synthesis.md#292-the-shearing-box).

### 2.2 Source terms that conserve epicycles and energy

When hydrodynamic turbulence was left to decay in a shearing box, its kinetic energy grew at late times, and the growth was traced to a truncation error of the source terms that amplified epicyclic motions (Stone and Gardiner 2010, §3). In the fluctuations $\rho v'_x = \rho v_x$ and $\rho v'_y = \rho(v_y + q\Omega_0x)$, a medium without stresses obeys $\partial(\rho v'_x)/\partial t = 2\Omega_0\rho v'_y$ and $\partial(\rho v'_y)/\partial t = (q - 2)\Omega_0\rho v'_x$, which conserve an epicyclic energy. Forward Euler makes these oscillations grow and backward Euler makes them decay, while the time differences of Crank and Nicolson, with the source terms at the mean of the old and new states, conserve the energy exactly in the discrete sense. Athena solves these differences in closed form together with the flux divergence, which leaves the update of $\rho v_y$ with a term from the radial mass fluxes. The CTU integrator adds the source terms for half a step by forward Euler where it needs them besides: in the interface states, in the transverse corrections and in the velocities that give the electric field of CT.

The energy source is the work of the effective potential $\Phi_\mathrm{SB} = -q\Omega_0^2x^2 + \tfrac{1}{2}\Omega_0^2z^2$, differenced as the work at the faces of each cell, the mass flux through each face times the drop of $\Phi_\mathrm{SB}$ over the adjacent half of the cell. Summed over the domain, this leaves only the work at the boundaries, so that the total energy $E + \rho\Phi_\mathrm{SB}$ cannot change by truncation error. The vertical gravity enters through its potential at four points of the integrator, with the density averaged over the step in the final update. The copy of Athena++ adds instead explicit source terms in each stage, from the primitive variables of the stage, with the energy source in the same form of work at the faces, and its stratified problems add the vertical gravity as a source term of their own.

Detail: [Athena 2.9.1](../references/athena-synthesis.md#291-physical-source-terms), [Athena 2.9.2](../references/athena-synthesis.md#292-the-shearing-box).

### 2.3 Shearing-periodic boundaries

Solutions that are not axisymmetric need radial boundaries that shift the solution by the distance that the shear has displaced the two radial edges against each other (Stone and Gardiner 2010, §4). Values at $(x, y, z)$ are carried to $(x \pm L_x, y \mp \Delta v_y t, z)$, where $\Delta v_y = q\Omega_0L_x$ is the jump of the orbital velocity across the box, with $\rho v_y$ changed by $\mp\rho\Delta v_y$ and the energy with it. The boundaries are filled as follows.

1. Apply periodic boundaries along $x$, with these changes of momentum and energy.
2. Remap the ghost cells conservatively along $y$ by the sheared distance, whole cells by a shift and the fraction of a cell by the reconstruction of the integrator.
3. Remap the components of the field in the ghost cells directly, in Athena, or remap $B_y$ and $B_z$ and set $B_x$ from the divergence constraint, in Athena++.
4. Remap the azimuthal electric field $\mathcal{E}_y$ on each radial face and update the field next to the boundary with the mean of its own value and the remapped one of the opposite face.

After a remap, the fluxes integrated over one radial face need not equal those over the other, as [Gressel and Ziegler](#gressel-ziegler-2007) (2007) noted, and step 4 conserves the net vertical flux, to which the MRI is sensitive, to machine precision. The same correction could restore conservation for every flux, but with orbital advection mass, momentum and energy stay accurate without it. A third-order integrator needs ghost cells reconstructed at third order as well, and Athena++ exchanges the shifted cells with up to four blocks along $y$.

Detail: [Athena 2.9.3](../references/athena-synthesis.md#293-shearing-periodic-boundaries).

### 2.4 Orbital advection

Orbital advection, introduced by [Masset](#masset-2000) (2000) and extended to MHD by [Johnson, Guan and Gammie](#johnson-et-al-2008) (2008) among others, splits the velocity as $\mathbf{v} = \mathbf{v}_\mathrm{K} + \mathbf{v}'$ (Stone and Gardiner 2010, §5). The equations of $\rho$, $\rho\mathbf{v}'$ and the energy $E'$ of the fluctuations each gain a linear advection $v_\mathrm{K}\,\partial/\partial y$, the induction equation gains $\nabla\times(\mathbf{v}_\mathrm{K}\times\mathbf{B})$, and $E'$ gains the work $(B_xB_y - \rho v'_xv'_y)\,\partial v_\mathrm{K}/\partial x$ of the stresses on the shear. The equations split into two systems. The second is ordinary MHD in the fluctuations, whose step depends on the fluctuations alone:

$$\Delta t = \mathcal{C}\min\left[\frac{\Delta x}{|v'_x| + c_{\mathrm{f},x}}, \frac{\Delta y}{|v'_y| + c_{\mathrm{f},y}}, \frac{\Delta z}{|v'_z| + c_{\mathrm{f},z}}\right],$$

with the fast speeds $c_\mathrm{f}$ along each direction. The first is linear advection along $y$, solved by a conservative remap.

1. Split the displacement $v_\mathrm{K}\Delta t$ of each cell into whole cells and a fraction.
2. Shift the conserved variables by the whole cells, and add the upwind fluxes of the fraction from the reconstruction of the integrator.
3. Remap the field by CT with the effective electric field $\boldsymbol{\mathcal{E}} = -\mathbf{v}_\mathrm{K}\times\mathbf{B} = (-v_\mathrm{K}B_z, 0, v_\mathrm{K}B_x)$, integrated over the swept distance upwind of each edge, which keeps the field free of divergence.
4. Add the work of the stresses on the shear, averaged over the step, before the remap carries the energy.

The remap may extend over any number of cells and needs no limit of stability. As the orbital flow is supersonic where $|x| > H/q$, with the scale height $H = c_\mathrm{s}/\Omega_0$, wide domains gain much larger steps. Athena++ follows Stone and Gardiner (2010) and applies orbital advection to global discs on cylindrical and spherical-polar grids as well, with Keplerian profiles about a point mass by default ([Stone et al.](#stone-et-al-2020) 2020, §3.2.6). Its remap follows the main stages, or comes by half steps before and after them for second order, and its fluxes integrate the linear profile of van Leer or the parabola of PPM. Unlike that of Athena, it limits the step: a displacement may not exceed a block length less the ghost cells of the remap, and those of neighbouring cells must differ by less than a cell. The work of the stresses enters explicitly in each stage.

Detail: [Athena 2.9.4](../references/athena-synthesis.md#294-orbital-advection).

## 3. Tests

The tests of Stone and Gardiner (2010) run with $\Omega_0 = 10^{-3}$, $q = 3/2$ and an isothermal gas with $c_\mathrm{s} = 10^{-3}$, third-order reconstruction and CTU with CT. An initial radial velocity of $0.1c_\mathrm{s}$ in square domains of sides 1, 10 and 50 on $64^2$ cells starts epicycles that are followed over thousands of orbits, the largest domain with only 14 steps per orbit. The nonlinear axisymmetric density waves of [Fromang and Papaloizou](#fromang-papaloizou-2007) (2007) start from a numerical solution on 40 cells and run for 100 periods.

The hydrodynamic shearing wave of [Johnson and Gammie](#johnson-gammie-2005) (2005), whose wavevector the shear swings from leading to trailing, should grow at most 17-fold, and runs with and without orbital advection on 4 to 16 cells per initial wavelength. A weak field loop given a radial velocity $c_\mathrm{s}$ oscillates in epicycles while the shear distorts it, and a quarter of it passes through the radial boundary where the displacement is largest. The test shows whether the electric fields of CT and the boundaries leave stripes in the field lines.

The MRI tests the whole scheme. In two dimensions, axisymmetric modes without net flux after [Hawley and Balbus](#hawley-balbus-1992) (1992) grow, saturate and decay as two-dimensional turbulence. In three dimensions, the MRI without net vertical flux runs in boxes up to $32H \times 32H \times H$ at 32 cells per $H$, with and without orbital advection, and longer runs at 32 to 256 cells per $H$ follow the conservation of mass and the convergence of the stress.

Athena++ runs the two-dimensional MRI and compares time averages of the Maxwell stress and the magnetic energy with reference data, within 50 per cent. A compressive magnetic shearing wave must follow the linear growth of its $\delta B_y$ within mean absolute errors of 0.01, and the hydrodynamic shearing wave its analytic solution in confluent hypergeometric functions. Both run with and without orbital advection, the second checking its thresholds only without it.

Detail: [Athena 2.9.2](../references/athena-synthesis.md#292-the-shearing-box), [Athena 2.9.3](../references/athena-synthesis.md#293-shearing-periodic-boundaries), [Athena 2.9.4](../references/athena-synthesis.md#294-orbital-advection).

## 4. Assessment

The epicycles keep a constant amplitude over thousands of orbits, with an error of dispersion of up to about 2 per cent at 14 steps per orbit that converges at second order (Stone and Gardiner 2010). The density waves err by at most 1.5 per cent after 100 periods and lose only 3 per cent of their amplitude, as good as runs at much higher resolution. The shearing wave is followed closely from 8 cells per wavelength on, its energy falling by five orders of magnitude without spurious growth, and the field loop shows no stripes. In the MRI, orbital advection gives magnetic energies of the same character at steps 4.3 times longer, far smoother radial profiles of density and stress, and a loss of mass of 0.03 per cent in 100 orbits at every resolution, against 1.5 to 8 per cent without it; the Maxwell stress without net flux does not converge with resolution. The net toroidal flux stays near $10^{-9}$ of the thermal pressure, ten times more with ghost cells of second order under a third-order integrator. **[GK]** The explicit source terms of the copy of Athena++ do not conserve the epicyclic energy exactly: for an oscillation of frequency $\omega$, a Runge–Kutta step of second order amplifies its amplitude by a factor $1 + (\omega\Delta t)^4/8$ to leading order, slight at the usual steps but systematic over many orbits. Orbital advection pays chiefly through the step in wide boxes and through a truncation error even in radius, at the cost of a remap, of conditions on the decomposition into blocks and, in Athena++, of a limit on the step. The production runs need no shearing box, which lies in the eventual scope through discs. Open are whether its source terms take the form of Crank and Nicolson or join the stages, and how the shifted boundaries fit the exchange of ghost cells of topic 4.

## 5. Sources

- <a id="fromang-papaloizou-2007"></a>Fromang, S. and Papaloizou, J., Properties and stability of freely propagating nonlinear density waves in accretion disks, A&A 468, 1–18 (2007), [doi:10.1051/0004-6361:20067044](https://doi.org/10.1051/0004-6361:20067044).
- <a id="gressel-ziegler-2007"></a>Gressel, O. and Ziegler, U., Shearingbox-implementation for the central-upwind, constraint-transport MHD-code NIRVANA, Computer Physics Communications 176, 652–659 (2007), [doi:10.1016/j.cpc.2007.01.010](https://doi.org/10.1016/j.cpc.2007.01.010).
- <a id="hawley-balbus-1992"></a>Hawley, J. F. and Balbus, S. A., A powerful local shear instability in weakly magnetized disks. III. Long-term evolution in a shearing sheet, ApJ 400, 595 (1992), [doi:10.1086/172021](https://doi.org/10.1086/172021).
- <a id="hawley-et-al-1995"></a>Hawley, J. F., Gammie, C. F. and Balbus, S. A., Local three-dimensional magnetohydrodynamic simulations of accretion disks, ApJ 440, 742 (1995), [doi:10.1086/175311](https://doi.org/10.1086/175311).
- <a id="johnson-et-al-2008"></a>Johnson, B. M., Guan, X. and Gammie, C. F., Orbital advection by interpolation: a fast and accurate numerical scheme for super-fast MHD flows, ApJS 177, 373–387 (2008), [doi:10.1086/586707](https://doi.org/10.1086/586707).
- <a id="johnson-gammie-2005"></a>Johnson, B. M. and Gammie, C. F., Linear theory of thin, radially stratified disks, ApJ 626, 978–990 (2005), [doi:10.1086/430081](https://doi.org/10.1086/430081).
- <a id="masset-2000"></a>Masset, F., FARGO: a fast eulerian transport algorithm for differentially rotating disks, A&AS 141, 165–173 (2000), [doi:10.1051/aas:2000116](https://doi.org/10.1051/aas:2000116).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-gardiner-2010"></a>Stone, J. M. and Gardiner, T. A., Implementation of the shearing box approximation in Athena, ApJS 189, 142–155 (2010), [arXiv:1006.0139](https://arxiv.org/abs/1006.0139), [doi:10.1088/0067-0049/189/1/142](https://doi.org/10.1088/0067-0049/189/1/142).

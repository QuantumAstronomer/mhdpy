# Cosmic rays

## 1. Overview

Cosmic rays stream along the magnetic field, diffuse along and across it, and exchange momentum and energy with the gas. Athena++ alone among the references treats them, with two modules: a transport of their energy density and flux by two moments, of the form of the moment equations of radiation, and an implicit solver for their diffusion by multigrid. The synthesis describes both from the code, without a paper. Radiation follows in [topic 23](23-radiation-transport.md), diffusion in [topic 16](16-diffusion.md) and multigrid in [topic 14, §2.3](14-elliptic-solvers.md#23-multigrid). **[GK]** Cosmic rays are relativistic charged particles.

## 2. Methods

### 2.1 Transport by two moments

The energy density $E_\mathrm{cr}$ of the cosmic rays and its flux $\mathbf{F}_\mathrm{cr}$ evolve by equations of the form of those of radiation, in which a chosen maximum speed takes the place of the speed of light, as the reduced speed of light does in [topic 23, §2.4](23-radiation-transport.md#24-discrete-ordinates-in-athena). A function of the problem sets the opacities, capped at a maximum, and their inverse sets the coefficients of diffusion along and across the field. Unless switched off, the cosmic rays also stream at the Alfvén speed down the gradient of their pressure along the field. A step runs within the main integrator.

1. Rotate the diffusion into the direction of the field and compute the fluxes from a reconstruction of selectable order, corrected in optically thick cells.
2. Correct the fluxes between levels of refinement and update the moments.
3. Add the source terms implicitly in each cell, which exchange momentum and energy with the gas through the gradient of the pressure of the cosmic rays and the work of streaming.
4. Exchange the boundaries and, after the physical boundaries, update the opacities.

Detail: [Athena 2.15.2](../references/athena-synthesis.md#2152-cosmic-rays).

### 2.2 Implicit diffusion

The second module solves for $E_\mathrm{cr}$ a diffusion equation with the tensor $\mathcal{D}_\perp\mathsf{I} + (\mathcal{D}_\parallel - \mathcal{D}_\perp)\mathbf{b}\mathbf{b}$, with the coefficients $\mathcal{D}_\parallel$ along and $\mathcal{D}_\perp$ across the unit vector $\mathbf{b}$ of the field, and a loss proportional to the density, optionally in a steady state. Its solver derives from the generic multigrid driver, on which the solver of self-gravity also builds ([topic 14, §2.3](14-elliptic-solvers.md#23-multigrid)), with Jacobi smoothing in red and black order and trilinear prolongation by default, the full approximation scheme as an option, and boundary conditions and a task list of its own for exchanging variables and coefficients. Functions of the problem can set the boundaries, the coefficients and masks of the source. Without a field the code sets every component of the tensor, the off-diagonal ones included, to $\mathcal{D}_\parallel$.

Detail: [Athena 2.10.3](../references/athena-synthesis.md#2103-multigrid-the-driver-its-boundaries-and-its-parallelisation), [Athena 2.15.2](../references/athena-synthesis.md#2152-cosmic-rays).

## 3. Tests

A Gaussian profile of cosmic rays diffuses along one of the three axes with the opacity $10^3$, so that the coefficient is the maximum speed over three times the opacity, at rest or advected by a uniform flow. The problem writes its error against the analytic solution. The regression runs both cases along each axis on 256 cells in blocks of 32 and requires errors below $8 \times 10^{-5}$ at rest and $9 \times 10^{-5}$ when advected. A further problem exercises the multigrid solver without a regression of its own.

Detail: [Athena 2.15.2](../references/athena-synthesis.md#2152-cosmic-rays).

## 4. Assessment

The references report only these thresholds. **[GK]** A tensor with all components equal to $\mathcal{D}_\parallel$ is not isotropic: it diffuses only along the diagonal direction of the grid, whereas isotropic diffusion would need vanishing off-diagonal components, so that the case without a field deserves checking before any reuse. The two-moment transport shares its structure, and its limit of the step by the maximum speed, with the explicit radiation of [topic 23, §2.4](23-radiation-transport.md#24-discrete-ordinates-in-athena). The second module solves implicitly a diffusion with the tensor of anisotropic thermal conduction, for which the references give only explicit schemes ([topic 17, §2.3](17-thermal-conduction.md#23-anisotropic-conduction)), although nothing records whether its operator keeps temperatures positive at sharp gradients, as the limited schemes do. Four files of the two-moment transport and the two problems of cosmic rays carry headers of version 3 of the GNU General Public License, as part of the radiation files do. The production runs need no cosmic rays, which lie in the eventual scope for galactic flows. Open is whether cosmic rays, radiation and anisotropic conduction share one implementation of moments and of anisotropic diffusion.

## 5. Sources

The synthesis cites no paper for these modules, whose description rests on the code of Athena++.

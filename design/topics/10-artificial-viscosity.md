# Artificial viscosity

## 1. Overview

A scheme of centred differences, such as ZEUS, cannot capture a shock by itself: its difference equations break down at the discontinuity. An artificial viscosity, a dissipation that in its nonlinear forms acts only where the flow converges, spreads the shock over a few zones, where the difference equations hold, and still gives the correct jump conditions and shock speed. ZEUS rests on it, with a scalar viscous pressure and a tensor form for curvilinear coordinates. Godunov schemes capture shocks through their Riemann solvers, but some add a small viscosity against the oscillations that remain behind slowly moving shocks, as [Colella and Woodward](#colella-woodward-1984) (1984) do: pyro in its compressible solvers and in its solver of fourth order ([topic 9, §2.2](09-methods-of-higher-order.md#22-finite-volumes-of-fourth-order)). The syntheses of Ulula and Athena describe none. Flattening, the other remedy at shocks, follows in [topic 6, §2.6](06-reconstruction-and-limiting.md#26-flattening-and-contact-steepening), and the physical viscosity in [topic 16, §2.4](16-diffusion.md#24-physical-diffusion-in-mhd). Artificial heat fluxes and resistivities are only named.

## 2. Methods

### 2.1 The viscous pressure of von Neumann and Richtmyer

[Von Neumann and Richtmyer](#von-neumann-richtmyer-1950) (1950) add to the pressure a nonlinear viscous pressure that acts only in compression ([Stone and Norman](#stone-norman-1992a) 1992a, eqs. 32 to 37):

$$q = \begin{cases} l^2\rho\,(\partial v_x/\partial x)^2, & \partial v_x/\partial x < 0, \\ 0, & \text{otherwise}, \end{cases}$$

with a length $l$ of a few zones that sets its strength. Being quadratic in the velocity gradient, it is large in shocks and negligible in smooth flow, and with it the difference equations give the correct jump in entropy and the correct shock speed. A shock is then several zones wide, so that its internal structure cannot be studied, unless an adaptive mesh resolves it with very small zones. In several dimensions ZEUS defines a scalar viscous pressure for each direction at the zone centres. Its source step adds the viscosity in a substep of its own, after the forces of pressure and gravity ([topic 18, §2.1](18-operator-splitting-and-coupling-of-processes.md#21-strang-splitting)).

1. Form $q_{x,i} = C_2\,\rho_i\,(v_{x,i+1/2} - v_{x,i-1/2})^2$ where the velocity difference across the zone is negative, and zero elsewhere, with $C_2 \approx 3$ roughly the number of zones over which a shock spreads, and alike $q_y$.
2. Accelerate the flow by the viscous force, $-(q_{x,i} - q_{x,i-1})/[\Delta x\,\tfrac{1}{2}(\rho_{i-1} + \rho_i)]$ for the velocity on the face $i - 1/2$.
3. Heat the gas by $-q_{x,i}(v_{x,i+1/2} - v_{x,i-1/2})/\Delta x$ per unit volume, and alike in $y$.

Strong shocks can also need a linear viscosity against oscillations where the flow stagnates, $q^\mathrm{lin} = C_1\rho\,c_\mathrm{s}\,\Delta v$ with the velocity difference $\Delta v$ across a zone and $C_1$ of order unity, which acts in expansion as well (Stone and Norman 1992a, eq. 38; [Lapidus](#lapidus-1967) 1967). Viscosity makes the equation of motion diffusive. **[GK]** The time step then obeys $\Delta t \le \Delta x^2/(4\nu)$, with $\nu = l^2|\nabla\cdot\mathbf{v}|$, the limit $\delta t_4$ of [topic 8, §2.6](08-time-integration.md#26-the-time-step), whose divergence needs its absolute value. The heating of step 3 is never negative, as $q_{x,i}$ vanishes unless the velocity difference is negative. With $\partial v_x/\partial x \approx \Delta v_x/\Delta x$, step 1 calls for $C_2^2$ rather than $C_2$ if $C_2 = l/\Delta x$, and later copies of the code multiply $\rho(\Delta v)^2$ by a constant of 2 by default, which stands for $(l/\Delta x)^2$. The linear viscosity heats only if $\Delta v$ is taken positive in compression, which the code confirms, although it uses the square root of the specific internal energy, $\sqrt{e}$, for the sound speed, which for an ideal gas differs from $c_\mathrm{s}$ by the factor $[\gamma(\gamma - 1)]^{1/2}$.

Detail: [ZEUS 2.1.2](../references/zeus-synthesis.md#212-operator-splitting), [ZEUS 2.3.1](../references/zeus-synthesis.md#231-substeps-and-forces), [ZEUS 2.3.2](../references/zeus-synthesis.md#232-artificial-viscosity), [ZEUS 2.5.2](../references/zeus-synthesis.md#252-stability-and-the-time-step).

### 2.2 The tensor artificial viscosity

The scalar form is ad hoc in several dimensions and can cause serious trouble in curvilinear coordinates: gas falling radially along converging grid lines is compressed even where $\partial v_r/\partial r = 0$, yet receives no viscosity ([Tscharnuter and Winkler](#tscharnuter-winkler-1979) 1979). The tensor form of Tscharnuter and Winkler (1979) builds on the viscous stress of a Newtonian fluid with zero bulk viscosity, but takes its coefficient from the divergence, an invariant (Stone and Norman 1992a, app. B, eqs. 133 to 144):

$$\mathsf{Q} = \begin{cases} l^2\rho\,(\nabla\cdot\mathbf{v})\left[\nabla\mathbf{v} - \tfrac{1}{3}(\nabla\cdot\mathbf{v})\,\mathsf{I}\right], & \nabla\cdot\mathbf{v} < 0, \\ 0, & \text{otherwise}, \end{cases}$$

with the symmetrised velocity gradient $\nabla\mathbf{v}$ and the unit tensor $\mathsf{I}$. The tensor is traceless and vanishes in an isotropic expansion. It enters the equation of motion as $-\nabla\cdot\mathsf{Q}$ and the equation of the internal energy as $-\mathsf{Q}:\nabla\mathbf{v}$, in covariant form. ZEUS takes one length for all directions, $l = C_2\max(\Delta x, \Delta y)$, as separate lengths would break the isotropy and the zero trace, and drops the off-diagonal components, so that the viscosity smooths compressive fronts but does not broaden shear layers. The heating is written as a sum of squares,

$$-\mathsf{Q}:\nabla\mathbf{v} = -\tfrac{1}{3}\,l^2\rho\,(\nabla\cdot\mathbf{v})\left[(\nabla v_{(11)} - \nabla v_{(22)})^2 + (\nabla v_{(11)} - \nabla v_{(33)})^2 + (\nabla v_{(33)} - \nabla v_{(22)})^2\right],$$

with the diagonal components $\nabla v_{(kk)}$ of the gradient. Tscharnuter and Winkler stress that the sum of squares is essential, as in their experience every other form eventually turns unstable. ZEUS offers both viscosities, and keeps the tensor for the problems that demand it, as the scalar one proves adequate in many, even in curvilinear coordinates. **[GK]** As the viscosity acts only where $\nabla\cdot\mathbf{v} < 0$, the sum of squares makes the heating non-negative. In planar flow the tensor reduces to $\tfrac{2}{3}l^2\rho(\partial v_x/\partial x)^2$, the scalar pressure with $l^2$ scaled by 2/3, which the later code compensates with a factor 1.5. Several printed formulae of the appendix need correcting, and the zone width in the polar direction, an angle, needs its scale factor before it sets $l$, which the code applies.

Detail: [ZEUS 2.3.2](../references/zeus-synthesis.md#232-artificial-viscosity), [ZEUS 2.3.4](../references/zeus-synthesis.md#234-the-tensor-artificial-viscosity).

### 2.3 Viscosity in Godunov schemes

Colella and Woodward (1984) report oscillations behind slowly moving shocks that flattening alone does not remove, and add a dissipation at converging flows, a multidimensional analogue of their eq. 4.5 that modifies the fluxes ([Zingale's text](#zingale-2025), §8.4.1). pyro adds to the flux through each face a diffusive term, which runs as follows.

1. Compute the divergence of the velocity at the corners of the zones from the averaged velocities, and average it to the faces.
2. Form the coefficient $\alpha = c_\mathrm{visc}\max(-\Delta x\,\nabla\cdot\mathbf{v},\ 0)$, with $c_\mathrm{visc} = 0.1$ by default, so that only converging flow is damped.
3. Add $\alpha\,(\mathbf{U}_{i-1} - \mathbf{U}_i)$ to the flux through the face $i - 1/2$, and alike in $y$, before the conservative update.

pyro's method of lines adds the same term, and its solver of fourth order the viscosity of [McCorquodale and Colella](#mccorquodale-colella-2011) (2011, eqs. 35 and 36), whose coefficient $\Delta x\,|\nabla\cdot\mathbf{v}|$ is reduced by the factor $\min[(\Delta x\,\nabla\cdot\mathbf{v})^2/(\beta c_\mathrm{s}^2), 1]$ ([topic 9, §2.2](09-methods-of-higher-order.md#22-finite-volumes-of-fourth-order)). Athena's Godunov methods capture shocks without such terms, apart from the H-correction against the carbuncle ([topic 7, §2.7](07-riemann-solvers.md#27-the-carbuncle-and-solvers-of-low-dissipation)), and [Felker and Stone](#felker-stone-2018) (2018) name artificial viscosity, beside the flattening of slopes and stronger limiting, as an alternative to characteristic projection where relativity or complex physics may make the latter impractical.

Detail: [Zingale 2.5.14](../references/computational-hydrodynamics-synthesis.md#2514-riemann-solvers-and-the-conservative-update), [pyro 2.4.4](../references/pyro-synthesis.md#244-artificial-viscosity-and-the-update), [pyro 2.4.8](../references/pyro-synthesis.md#248-the-method-of-lines-solver), [pyro 2.4.9](../references/pyro-synthesis.md#249-the-fourth-order-solver), [Athena 2.7.1](../references/athena-synthesis.md#271-finite-volumes-of-fourth-order).

## 3. Assessment

In ZEUS's shock tube, the shock and the contact spread over about four zones, as expected from the artificial viscosity and the advection of second order (Stone and Norman 1992a, §5.4; [topic 30, §2.2](30-shock-tubes-and-interacting-blast-waves.md#22-sods-shock-tube)). **[GK]** An artificial viscosity is simple, cheap and independent of the eigensystem, which makes it easy to extend to new physics, as ZEUS's long use shows. It needs tuned constants, however, whose best values depend on the problem, smears shocks over more zones than a Riemann solver, and in its scalar form misbehaves in converging curvilinear flow. In a scheme that conserves the total energy, the heating it adds is correct in total but placed within the smeared shock, which matters where cooling acts on the shocked gas, as behind the shocks around clouds. In a Godunov scheme a small viscosity is cheap insurance against oscillations at slowly moving shocks and in multidimensional flow, at some loss of sharpness. Open are whether a Godunov code for MHD needs any artificial viscosity beside flattening and characteristic limiting, and what form it should take on curvilinear grids.

## 4. Sources

- <a id="colella-woodward-1984"></a>Colella, P. and Woodward, P. R., The piecewise parabolic method (PPM) for gas-dynamical simulations, Journal of Computational Physics 54, 174–201 (1984), [doi:10.1016/0021-9991(84)90143-8](https://doi.org/10.1016/0021-9991%2884%2990143-8).
- <a id="felker-stone-2018"></a>Felker, K. G. and Stone, J. M., A fourth-order accurate finite volume method for ideal MHD via upwind constrained transport, Journal of Computational Physics 375, 1365–1400 (2018), [arXiv:1711.07439](https://arxiv.org/abs/1711.07439), [doi:10.1016/j.jcp.2018.08.025](https://doi.org/10.1016/j.jcp.2018.08.025).
- <a id="lapidus-1967"></a>Lapidus, A., A detached shock calculation by second-order finite differences, Journal of Computational Physics 2, 154–177 (1967), [doi:10.1016/0021-9991(67)90032-0](https://doi.org/10.1016/0021-9991%2867%2990032-0).
- <a id="mccorquodale-colella-2011"></a>McCorquodale, P. and Colella, P., A high-order finite-volume method for conservation laws on locally refined grids, Communications in Applied Mathematics and Computational Science 6, 1–25 (2011), [doi:10.2140/camcos.2011.6.1](https://doi.org/10.2140/camcos.2011.6.1).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="tscharnuter-winkler-1979"></a>Tscharnuter, W.-M. and Winkler, K.-H. A., A method for computing selfgravitating gas flows with radiation, Computer Physics Communications 18, 171–199 (1979), [doi:10.1016/0010-4655(79)90111-5](https://doi.org/10.1016/0010-4655%2879%2990111-5).
- <a id="von-neumann-richtmyer-1950"></a>von Neumann, J. and Richtmyer, R. D., A method for the numerical calculation of hydrodynamic shocks, Journal of Applied Physics 21, 232–237 (1950), [doi:10.1063/1.1699639](https://doi.org/10.1063/1.1699639).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

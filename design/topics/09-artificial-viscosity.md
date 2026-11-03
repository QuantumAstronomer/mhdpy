# Artificial viscosity

## 1. Overview

A difference scheme without a Riemann solver cannot capture a shock by itself: its equations break down at the discontinuity. An artificial viscosity, a dissipation that acts only where the flow converges, spreads the shock over a few zones, where the difference equations hold, and still gives the correct jump conditions and shock speed. ZEUS rests on it, with a scalar viscous pressure and a tensor form for curvilinear coordinates. Godunov schemes capture shocks through their Riemann solvers, but some add a small viscosity against the oscillations that remain behind slow shocks, as [Colella and Woodward](#colella-woodward-1984) (1984) do: pyro in its compressible solvers and in its solver of fourth order (topic 8). The syntheses of Ulula and Athena describe none. Flattening, the other remedy at shocks, follows in topic 5, and the physical viscosity in topic 15. Artificial heat fluxes and resistivities are only named.

## 2. Methods

### 2.1 The viscous pressure of von Neumann and Richtmyer

[Von Neumann and Richtmyer](#von-neumann-richtmyer-1950) (1950) add to the pressure a nonlinear viscous pressure that acts only in compression ([Stone and Norman](#stone-norman-1992a) 1992a, eqs. 32 to 37):

$$q = \begin{cases} l^2\rho\,(\partial v_x/\partial x)^2, & \partial v_x/\partial x < 0, \\ 0, & \text{otherwise}, \end{cases}$$

with a length $l$ of a few zones that sets its strength. Being quadratic in the velocity gradient, it is large in shocks and negligible in smooth flow, and with it the difference equations give the correct jump in entropy and the correct shock speed. A shock is then several zones wide, so that its internal structure cannot be studied. In several dimensions ZEUS defines a scalar viscous pressure for each direction at the zone centres. Its source step adds the viscosity in a substep of its own, after the forces of pressure and gravity (topic 16).

1. Form $q_{x,i} = C_2\,\rho_i\,(v_{x,i+1/2} - v_{x,i-1/2})^2$ where the velocity difference across the zone is negative, and zero elsewhere, with $C_2 \approx 3$ roughly the number of zones over which a shock spreads, and alike $q_y$.
2. Accelerate the flow by the viscous force, $-(q_{x,i} - q_{x,i-1})/[\Delta x\,\tfrac{1}{2}(\rho_{i-1} + \rho_i)]$ for the velocity on the face $i - 1/2$.
3. Heat the gas by $-q_{x,i}(v_{x,i+1/2} - v_{x,i-1/2})/\Delta x$ per unit volume, alike in $y$, which is never negative.

Strong shocks can also need a linear viscosity against oscillations where the flow stagnates, $q^\mathrm{lin} = C_1\rho\,c_\mathrm{s}\,\Delta v$ with $C_1$ of order unity, which acts in expansion as well ([Lapidus](#lapidus-1967) 1967). Viscosity makes the equation of motion diffusive, so that the time step obeys $\Delta t \le \Delta x^2/(4\nu)$ with $\nu = l^2|\nabla\cdot\mathbf{v}|$, the limit $\delta t_4$ of topic 7. **[GK]** With $\partial v_x/\partial x \approx \Delta v_x/\Delta x$, step 1 calls for $C_2^2$ rather than $C_2$ if $C_2 = l/\Delta x$, and later copies of the code multiply $\rho(\Delta v)^2$ by a constant of 2 by default, which stands for $(l/\Delta x)^2$. The linear viscosity heats only if $\Delta v$ is taken positive in compression, which the code confirms, although it uses $\sqrt{e/\rho}$ for the sound speed.

Detail: [ZEUS 2.1.2](../references/zeus-synthesis.md#212-operator-splitting), [ZEUS 2.3.2](../references/zeus-synthesis.md#232-artificial-viscosity), [ZEUS 2.5.2](../references/zeus-synthesis.md#252-stability-and-the-time-step).

### 2.2 The tensor artificial viscosity

The scalar form is ad hoc in several dimensions and fails in curvilinear coordinates: gas falling radially along converging grid lines is compressed even where $\partial v_r/\partial r = 0$, yet receives no viscosity ([Tscharnuter and Winkler](#tscharnuter-winkler-1979) 1979). The tensor form builds on the viscous stress of a Newtonian fluid with zero bulk viscosity, but takes its coefficient from the divergence, an invariant (Stone and Norman 1992a, app. B, eqs. 133 to 144):

$$\mathsf{Q} = \begin{cases} l^2\rho\,(\nabla\cdot\mathbf{v})\left[\nabla\mathbf{v} - \tfrac{1}{3}(\nabla\cdot\mathbf{v})\,\mathsf{I}\right], & \nabla\cdot\mathbf{v} < 0, \\ 0, & \text{otherwise}, \end{cases}$$

with the symmetrised velocity gradient $\nabla\mathbf{v}$ and the unit tensor $\mathsf{I}$. The tensor is traceless and vanishes in an isotropic expansion. It enters the momentum equation as $-\nabla\cdot\mathsf{Q}$ and the energy equation as $-\mathsf{Q}:\nabla\mathbf{v}$, in covariant form. ZEUS takes one length for all directions, $l = C_2\max(\Delta x, \Delta y)$, as separate lengths would break the isotropy and the zero trace, and drops the off-diagonal components, so that the viscosity smooths compressive fronts but does not broaden shear layers. The heating is written as a sum of squares,

$$-\mathsf{Q}:\nabla\mathbf{v} = -\tfrac{1}{3}\,l^2\rho\,(\nabla\cdot\mathbf{v})\left[(\nabla v_{(11)} - \nabla v_{(22)})^2 + (\nabla v_{(11)} - \nabla v_{(33)})^2 + (\nabla v_{(33)} - \nabla v_{(22)})^2\right],$$

with the diagonal components $\nabla v_{(kk)}$ of the gradient. Tscharnuter and Winkler stress that every other form eventually turns unstable. ZEUS offers both viscosities, and keeps the tensor for the problems that demand it, as the scalar one proves adequate in many, even in curvilinear coordinates. **[GK]** As the viscosity acts only where $\nabla\cdot\mathbf{v} < 0$, the sum of squares makes the heating non-negative. In planar flow the tensor reduces to $\tfrac{2}{3}l^2\rho(\partial v_x/\partial x)^2$, the scalar pressure with $l^2$ scaled by 2/3, which the later code compensates with a factor 1.5. Several printed formulae of the appendix need correcting, and the length $l$ in the polar direction needs its scale factor, which the code applies.

Detail: [ZEUS 2.3.4](../references/zeus-synthesis.md#234-the-tensor-artificial-viscosity).

### 2.3 Viscosity in Godunov schemes

Colella and Woodward (1984) report oscillations behind slow shocks that flattening alone does not remove, and add a dissipation at converging flows that modifies the fluxes ([Zingale's text](#zingale-2025), §8.4.1). pyro adds to the flux through each face a diffusive term, which runs as follows.

1. Compute the divergence of the velocity at the corners of the zones from the averaged velocities, and average it to the faces.
2. Form the coefficient $\alpha = c_\mathrm{visc}\max(-\Delta x\,\nabla\cdot\mathbf{v},\ 0)$, with $c_\mathrm{visc} = 0.1$ by default, so that only converging flow is damped.
3. Add $\alpha\,(\mathbf{U}_{i-1} - \mathbf{U}_i)$ to the flux through the face $i - 1/2$, and alike in $y$, before the conservative update.

pyro's method of lines adds the same term, and its solver of fourth order the viscosity of [McCorquodale and Colella](#mccorquodale-colella-2011) (2011), which scales with the square of the compression over the sound speed (topic 8). Athena's Godunov methods capture shocks without such terms, and [Felker and Stone](#felker-stone-2018) (2018) name artificial viscosity only as an alternative to characteristic projection where complex physics makes the latter impractical.

Detail: [Zingale 2.5.14](../references/computational-hydrodynamics-synthesis.md#2514-riemann-solvers-and-the-conservative-update), [pyro 2.4.4](../references/pyro-synthesis.md#244-artificial-viscosity-and-the-update), [pyro 2.4.9](../references/pyro-synthesis.md#249-the-fourth-order-solver), [Athena 2.7.1](../references/athena-synthesis.md#271-finite-volumes-of-fourth-order).

## 3. Assessment

In ZEUS's shock tube, the shock and the contact spread over about four zones, as expected from the artificial viscosity and the advection of second order (Stone and Norman 1992a, §5.4; topic 27). **[GK]** An artificial viscosity is simple, cheap and independent of the eigensystem, which makes it easy to extend to new physics, as ZEUS's long use shows. It needs tuned constants, however, whose best values depend on the problem, smears shocks over more zones than a Riemann solver, and in its scalar form misbehaves in converging curvilinear flow. The heating it adds is correct in total but placed within the smeared shock, which matters where cooling acts on the shocked gas, as behind the shocks around clouds. In a Godunov scheme a small viscosity is cheap insurance against oscillations at slow shocks and in multidimensional flow, at some loss of sharpness. Open are whether a Godunov code for MHD needs any artificial viscosity beside flattening and characteristic limiting, and what form it should take on curvilinear grids.

## 4. Sources

- <a id="colella-woodward-1984"></a>Colella, P. and Woodward, P. R., The piecewise parabolic method (PPM) for gas-dynamical simulations, Journal of Computational Physics 54, 174–201 (1984), [doi:10.1016/0021-9991(84)90143-8](https://doi.org/10.1016/0021-9991%2884%2990143-8).
- <a id="felker-stone-2018"></a>Felker, K. G. and Stone, J. M., A fourth-order accurate finite volume method for ideal MHD via upwind constrained transport, Journal of Computational Physics 375, 1365–1400 (2018), [arXiv:1711.07439](https://arxiv.org/abs/1711.07439), [doi:10.1016/j.jcp.2018.08.025](https://doi.org/10.1016/j.jcp.2018.08.025).
- <a id="lapidus-1967"></a>Lapidus, A., A detached shock calculation by second-order finite differences, Journal of Computational Physics 2, 154–177 (1967), [doi:10.1016/0021-9991(67)90032-0](https://doi.org/10.1016/0021-9991%2867%2990032-0).
- <a id="mccorquodale-colella-2011"></a>McCorquodale, P. and Colella, P., A high-order finite-volume method for conservation laws on locally refined grids, Communications in Applied Mathematics and Computational Science 6, 1–25 (2011), [doi:10.2140/camcos.2011.6.1](https://doi.org/10.2140/camcos.2011.6.1).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="tscharnuter-winkler-1979"></a>Tscharnuter, W.-M. and Winkler, K.-H. A., A method for computing selfgravitating gas flows with radiation, Computer Physics Communications 18, 171–199 (1979), [doi:10.1016/0010-4655(79)90111-5](https://doi.org/10.1016/0010-4655%2879%2990111-5).
- <a id="von-neumann-richtmyer-1950"></a>von Neumann, J. and Richtmyer, R. D., A method for the numerical calculation of hydrodynamic shocks, Journal of Applied Physics 21, 232–237 (1950), [doi:10.1063/1.1699639](https://doi.org/10.1063/1.1699639).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

# Reconstruction and limiting

## 1. Overview

Reconstruction is the first step of the conservative update of [topic 3, §2.3](03-grids-and-finite-volume-discretisation.md#23-the-conservative-update). From the cell averages it builds a profile within each cell, whose values at the faces are the states between which the Riemann solver of [topic 7](07-riemann-solvers.md) computes the flux. A constant profile gives a scheme of first order, which smears every feature. A profile of higher order sharpens smooth data but oscillates at discontinuities, and by Godunov's theorem a monotone scheme of higher order must be nonlinear, as a limiter makes it. The methods compared are linear profiles with slope limiters, in every reference, parabolic ones in Athena and Athena++ (PPM) and in the transport of ZEUS, weighted essentially non-oscillatory (WENO) reconstruction in pyro and Athena++, limiting in characteristic variables, and flattening at shocks. The prediction of the face states at the half step follows in [topic 8, §2.2](08-time-integration.md#22-predictorcorrector-schemes-in-one-dimension), methods of fourth order in [topic 9](09-methods-of-higher-order.md) and curvilinear weights in [topic 12, §2.4](12-curvilinear-coordinates.md#24-reconstruction-on-curvilinear-grids). Limiters that act in several dimensions at once are only named, by Zingale's text.

## 2. Methods

### 2.1 Reconstruction and monotonicity

Here $f_i$ stands for the cell average $\langle f\rangle_i$ of any variable, and the states of cell $i$ are $f_{\mathrm{R},i-1/2}$ at its left face and $f_{\mathrm{L},i+1/2}$ at its right one. A constant profile, $f_{\mathrm{R},i-1/2} = f_{\mathrm{L},i+1/2} = f_i$, gives the donor cell of first order, too diffusive for applications ([Stone et al.](#stone-et-al-2008) 2008, eq. 35; [Diemer](#diemer-2025) 2025, eq. 16). A linear profile with the limited difference $\delta f_i$ across the cell gives second order:

$$f_i(x) = f_i + \frac{\delta f_i}{\Delta x}\,(x - x_i), \qquad f_{\mathrm{R},i-1/2} = f_i - \tfrac{1}{2}\,\delta f_i, \qquad f_{\mathrm{L},i+1/2} = f_i + \tfrac{1}{2}\,\delta f_i.$$

For advection of $u$ at a velocity $v > 0$, the update with the upwind face values $u_i + \tfrac{1}{2}(1 - \mathcal{C})\,\delta u_i$, where $\mathcal{C} = v\,\Delta t/\Delta x$, equals shifting this profile by $\mathcal{C}\,\Delta x$ and averaging it over the cells ([Zingale's text](#zingale-2025), eqs. 5.16 to 5.28): reconstruct, evolve and average.

Godunov's theorem states that a linear method for advection that is monotone, creating no new extrema, is at most of first order, so that a monotone method of second order must be nonlinear (Zingale's text). A limiter makes it so: it reduces the slope where the profile would create an extremum, and sets it to zero at an extremum of the data. The limiters are built to make the scheme total variation diminishing (TVD). **[GK]** Its total variation $\sum_i |f_{i+1} - f_i|$ then never grows, and at smooth extrema, where the limiter clips the slope, the scheme falls to first order.

Detail: [Zingale 2.3.9](../references/computational-hydrodynamics-synthesis.md#239-limiting), [Zingale 2.3.10](../references/computational-hydrodynamics-synthesis.md#2310-reconstruct-evolve-average), [Ulula 2.5.1](../references/ulula-synthesis.md#251-constant-and-linear-states), [ZEUS 2.4.2](../references/zeus-synthesis.md#242-interpolation-to-the-faces), [Athena 2.4.2](../references/athena-synthesis.md#242-first-order).

### 2.2 Slope limiters

The limited difference comes from the differences to the neighbours (Stone et al. 2008, eq. 36; Diemer 2025, eqs. 18 and 19, there divided by $\Delta x$):

$$\delta f_{\mathrm{L},i} = f_i - f_{i-1}, \qquad \delta f_{\mathrm{R},i} = f_{i+1} - f_i, \qquad \delta f_{\mathrm{C},i} = \tfrac{1}{2}\,(f_{i+1} - f_{i-1}).$$

With $\mathrm{minmod}$ returning the argument of smallest magnitude where all share a sign and zero otherwise, the three common limiters are (Zingale's text, eqs. 5.11 to 5.14; Diemer 2025, eqs. 20 to 22)

$$\delta f_i = \begin{cases} \mathrm{minmod}(\delta f_{\mathrm{L},i},\ \delta f_{\mathrm{R},i}) & \text{minmod,}\\[2pt] 2\,\delta f_{\mathrm{L},i}\,\delta f_{\mathrm{R},i}/(\delta f_{\mathrm{L},i} + \delta f_{\mathrm{R},i}) \ \text{where}\ \delta f_{\mathrm{L},i}\,\delta f_{\mathrm{R},i} > 0,\ 0\ \text{otherwise} & \text{van Leer,}\\[2pt] \mathrm{minmod}(2\,\delta f_{\mathrm{L},i},\ \delta f_{\mathrm{C},i},\ 2\,\delta f_{\mathrm{R},i}) & \text{monotonised central (MC).} \end{cases}$$

Minmod ([Roe](#roe-1986) 1986) is the most cautious, MC ([van Leer](#van-leer-1977) 1977) the most aggressive in common use, and the harmonic mean of [van Leer](#van-leer-1974) (1974) lies between. Ulula offers all three, and ZEUS and Athena++ use the harmonic mean, Athena++ minmod on request. pyro uses MC or a variant of fourth order after [Colella](#colella-1985) (1985), which limits $\tfrac{4}{3}\,\delta f_{\mathrm{C},i} - \tfrac{1}{6}(\delta f_{i+1} + \delta f_{i-1})$, built from the MC differences of the neighbours, by the same bounds.

On nonuniform and curvilinear meshes, Athena++ scales the differences to the cell, $\delta q_\mathrm{B} = \delta f_{\mathrm{L},i}\,\Delta x_i/(x^\mathrm{v}_i - x^\mathrm{v}_{i-1})$ and $\delta q_\mathrm{F} = \delta f_{\mathrm{R},i}\,\Delta x_i/(x^\mathrm{v}_{i+1} - x^\mathrm{v}_i)$, with the volume centres $x^\mathrm{v}_i$, and limits them by the generalised harmonic mean of [Mignone](#mignone-2014) (2014, eqs. 33 and 37):

$$\delta f_i = \frac{\delta q_\mathrm{F}\,\delta q_\mathrm{B}\,(c_\mathrm{f}\,\delta q_\mathrm{B} + c_\mathrm{b}\,\delta q_\mathrm{F})}{\delta q_\mathrm{B}^2 + \delta q_\mathrm{F}^2 + (c_\mathrm{f} + c_\mathrm{b} - 2)\,\delta q_\mathrm{F}\,\delta q_\mathrm{B}}, \qquad c_\mathrm{f} = \frac{x^\mathrm{v}_{i+1} - x^\mathrm{v}_i}{x_{i+1/2} - x^\mathrm{v}_i}, \qquad c_\mathrm{b} = \frac{x^\mathrm{v}_i - x^\mathrm{v}_{i-1}}{x^\mathrm{v}_i - x_{i-1/2}},$$

zero where the signs differ. On a uniform grid $c_\mathrm{f} = c_\mathrm{b} = 2$, and the harmonic mean returns. For a gravitating atmosphere, pyro limits the pressure in $y$ as a deviation from hydrostatic balance, $p'_j = 0$ and $p'_{j\pm1} = p_{j\pm1} - [p_j \pm \tfrac{1}{2}\Delta y\,(\rho_j + \rho_{j\pm1})\,g]$, so that a discretely hydrostatic profile receives no slope.

Detail: [Zingale 2.3.9](../references/computational-hydrodynamics-synthesis.md#239-limiting), [pyro 2.1.5](../references/pyro-synthesis.md#215-slopes-and-limiters), [Ulula 2.5.1](../references/ulula-synthesis.md#251-constant-and-linear-states), [Ulula 2.5.2](../references/ulula-synthesis.md#252-slope-limiters), [ZEUS 2.4.2](../references/zeus-synthesis.md#242-interpolation-to-the-faces), [Athena 2.4.3](../references/athena-synthesis.md#243-second-order).

### 2.3 Piecewise parabolic reconstruction

PPM reconstructs a parabola in each cell ([Colella and Woodward](#colella-woodward-1984) 1984). Its edge values $f_{-,i}$ and $f_{+,i}$ start from the face values

$$f_{i+1/2} = \tfrac{1}{2}\,(f_i + f_{i+1}) - \tfrac{1}{6}\,(\delta f_{i+1} - \delta f_i),$$

which with the centred differences $\delta f_{\mathrm{C},i}$ become the stencil of fourth order, $f_{i+1/2} = \tfrac{7}{12}(f_i + f_{i+1}) - \tfrac{1}{12}(f_{i-1} + f_{i+2})$ ([Stone et al.](#stone-et-al-2020) 2020, eq. 10). With $\xi = (x - x_{i-1/2})/\Delta x$ and $f_{6,i} = 6\,[f_i - \tfrac{1}{2}(f_{-,i} + f_{+,i})]$, the parabola

$$f_i(\xi) = f_{-,i} + \xi\,(f_{+,i} - f_{-,i}) + \xi\,(1 - \xi)\,f_{6,i}$$

has the average $f_i$ over the cell (Zingale's text, eqs. 8.36 to 8.40). Athena takes the face values from limited differences (2.2, 2.5) and constrains the parabola as Colella and Woodward (1984, eq. 1.10) do (Stone et al. 2008, §4.2.3). Where $f_i$ is an extremum, $(f_{+,i} - f_i)(f_i - f_{-,i}) \le 0$, both edge values become $f_i$. Where the parabola would overshoot within the cell, one edge value is reset, $f_{-,i} = 3f_i - 2f_{+,i}$ or $f_{+,i} = 3f_i - 2f_{-,i}$. These constraints clip smooth extrema, which the limiters of [Colella and Sekora](#colella-sekora-2008) (2008), also offered by Athena, avoid.

Athena++ interpolates the face values from unlimited differences and limits them afterwards, with the limiter of [McCorquodale et al.](#mccorquodale-et-al-2015) (2015) that preserves smooth extrema, an extension of Colella and Sekora (2008) (Stone et al. 2020, §3.2.1). Along a uniform Cartesian direction it runs as follows.

1. Interpolate the face values with the stencil of fourth order.
2. Replace a face value outside the range of its two neighbouring averages by $\tfrac{1}{2}(f_{i-1} + f_i) - \tilde{d}/6$, with a second derivative $\tilde{d}$ limited against those of the two cells.
3. At an extremum of the parabola or of the averages, scale the parabola about $f_i$ by the ratio of its second derivative, limited against those of the cells $i - 1$, $i$ and $i + 1$, to its own. The ratio vanishes unless all share a sign, so that only a smooth extremum survives.
4. Elsewhere, reset an edge value where the parabola would overshoot, as above.

Along nonuniform directions the general weights of Colella and Woodward (1984, eq. 1.6) take the place of the stencil of step 1, along the radial and polar directions of curvilinear coordinates those of Mignone (2014) ([topic 12, §2.4](12-curvilinear-coordinates.md#24-reconstruction-on-curvilinear-grids)), and along all these directions the limiter of Mignone (2014) replaces steps 2 to 4. The scheme stays formally of second order, although its face values are of fourth. ZEUS's piecewise parabolic advection uses the same parabola for transport ([Stone and Norman](#stone-norman-1992a) 1992a, eq. 50). **[GK]** Eq. 50 is the average of that parabola over the part of the upwind zone that crosses the face in a step.

Detail: [Zingale 2.5.12](../references/computational-hydrodynamics-synthesis.md#2512-piecewise-parabolic-reconstruction), [ZEUS 2.4.2](../references/zeus-synthesis.md#242-interpolation-to-the-faces), [Athena 2.4.5](../references/athena-synthesis.md#245-the-piecewise-parabolic-method).

### 2.4 WENO reconstruction

WENO combines the candidates of several stencils instead of limiting one (Zingale's text, eqs. 5.71 to 5.79). For fifth order, three stencils of three cells give third-order face values,

$$f^{(0)}_{i+1/2} = \tfrac{1}{6}(2f_{i-2} - 7f_{i-1} + 11f_i), \qquad f^{(1)}_{i+1/2} = \tfrac{1}{6}(-f_{i-1} + 5f_i + 2f_{i+1}), \qquad f^{(2)}_{i+1/2} = \tfrac{1}{6}(2f_i + 5f_{i+1} - f_{i+2}),$$

which the linear weights $C_\ell = (1/10,\ 3/5,\ 3/10)$ of the stencils $\ell = 0$, 1 and 2 combine into the fifth-order value $\tfrac{1}{60}(2f_{i-2} - 13f_{i-1} + 47f_i + 27f_{i+1} - 3f_{i+2})$. Indicators of smoothness shift the weights away from a stencil that crosses a discontinuity:

$$f_{i+1/2} = \sum_\ell \omega_\ell\,f^{(\ell)}_{i+1/2}, \qquad \omega_\ell = \frac{\alpha_\ell}{\alpha_0 + \alpha_1 + \alpha_2}, \qquad \alpha_\ell = \frac{C_\ell}{\epsilon_\mathrm{w} + \beta_\ell^2},$$

with the indicators that Athena++ writes out, $\beta_0 = \tfrac{13}{12}(f_{i-2} - 2f_{i-1} + f_i)^2 + \tfrac{1}{4}(f_{i-2} - 4f_{i-1} + 3f_i)^2$, $\beta_1 = \tfrac{13}{12}(f_{i-1} - 2f_i + f_{i+1})^2 + \tfrac{1}{4}(f_{i-1} - f_{i+1})^2$, $\beta_2$ the mirror image of $\beta_0$, and a small $\epsilon_\mathrm{w}$. The value at the left face follows by reflection. pyro implements this form, with two or three stencils, in a finite-difference scheme for advection that reconstructs split fluxes from point values ([topic 9, §2.3](09-methods-of-higher-order.md#23-finite-differences-with-weno-and-flux-splitting)). Athena++ offers instead WENO-Z of [Borges et al.](#borges-et-al-2008) (2008), with $\alpha_\ell = C_\ell\,[1 + (\tau_5/(\beta_\ell + \epsilon_\mathrm{w}))^2]$ and $\tau_5 = |\beta_0 - \beta_2|$, and a modification of it, both in primitive variables on uniform Cartesian grids. **[GK]** These are the indicators of [Jiang and Shu](#jiang-shu-1996) (1996) for three stencils, who set $\alpha_\ell = C_\ell/(\epsilon_\mathrm{w} + \beta_\ell)^2$, where Zingale's text and pyro square $\beta_\ell$ alone.

Detail: [Zingale 2.3.19](../references/computational-hydrodynamics-synthesis.md#2319-weno-reconstruction), [pyro 2.1.7](../references/pyro-synthesis.md#217-weno-reconstruction), [Athena 2.4.6](../references/athena-synthesis.md#246-weno).

### 2.5 Primitive and characteristic variables

The references reconstruct primitive variables rather than conserved ones, which guards density and pressure directly against negative values (Diemer 2025). ZEUS interpolates the density and the specific quantities that it transports. In MHD only the transverse field is reconstructed, as the normal component lives on the face (Stone et al. 2008; [topic 11, §2.1](11-constrained-transport.md#21-the-staggered-field)). Athena limits in characteristic variables instead, with the decomposition of [topic 1, §2.3](01-equations-and-their-variables.md#23-the-quasi-linear-primitive-and-characteristic-forms) (Stone et al. 2008, eqs. 37 to 39):

$$\delta\mathbf{a}_{\mathrm{X},i} = \mathsf{L}(\mathbf{W}_i)\,\delta\mathbf{W}_{\mathrm{X},i}\ \ \text{for X = L, R, C}, \qquad \delta a^{(m)}_i = \mathrm{minmod}\big(2\,\delta a^{(m)}_{\mathrm{L},i},\ \delta a^{(m)}_{\mathrm{C},i},\ 2\,\delta a^{(m)}_{\mathrm{R},i}\big), \qquad \delta\mathbf{W}_i = \mathsf{R}(\mathbf{W}_i)\,\delta\mathbf{a}_i.$$

Athena++ projects on request as well, but differently: its PLM limits the projected one-sided differences by the harmonic mean of 2.2, and its PPM projects all averages of the stencil with the eigenvectors of the cell before interpolating and limiting them as in 2.3 ([Felker and Stone](#felker-stone-2018) 2018, §2.2.2). Limiting each wave on its own follows the theory of advection more closely and reduces oscillations, in MHD in particular. The recovered primitive variables can leave their physical range, however, for example with a negative density, so that Athena++ applies the floors of [topic 2, §2.2](02-equations-of-state.md#22-the-internal-energy-and-floors) again (Zingale's text, eqs. 8.52 and 8.53). Athena++ applies the eigensystem without forming its matrices, and refuses the projection with a general equation of state. **[GK]** Stone et al. (2008) print eq. 38 without the zero where the one-sided differences differ in sign, and eq. 39 with $\mathsf{R}$ on the wrong side; the display gives the forms that the method needs.

Detail: [Zingale 2.5.11](../references/computational-hydrodynamics-synthesis.md#2511-piecewise-linear-reconstruction-and-characteristic-tracing), [Zingale 2.5.13](../references/computational-hydrodynamics-synthesis.md#2513-flattening-contact-steepening-and-characteristic-limiting), [Ulula 2.5.1](../references/ulula-synthesis.md#251-constant-and-linear-states), [ZEUS 2.4.3](../references/zeus-synthesis.md#243-fluxes-on-a-moving-grid-and-consistent-transport), [Athena 2.4.1](../references/athena-synthesis.md#241-interface-states), [Athena 2.4.3](../references/athena-synthesis.md#243-second-order), [Athena 2.4.4](../references/athena-synthesis.md#244-characteristic-variables), [Athena 2.7.1](../references/athena-synthesis.md#271-finite-volumes-of-fourth-order).

### 2.6 Flattening and contact steepening

Shocks steepen themselves, and the reconstructions above can make them too steep. Flattening blends the face states towards the cell average at strong shocks, so that a shock spreads over about two zones (Zingale's text, eq. 8.51; [Saltzman](#saltzman-1994) 1994):

$$\mathbf{W}_{\mathrm{L},i+1/2} \leftarrow (1 - \chi_i)\,\mathbf{W}_i + \chi_i\,\mathbf{W}_{\mathrm{L},i+1/2},$$

and alike for $\mathbf{W}_{\mathrm{R},i-1/2}$, with $\chi_i = 1$ for no flattening and $\chi_i = 0$ for first order. pyro, which flattens by default, computes the coefficient in four steps.

1. Measure the steepness of the pressure jump over three cells against five, $z_i = |p_{i+1} - p_{i-1}|/|p_{i+2} - p_{i-2}|$.
2. Set $\chi_i = \min\{1, \max[0, 1 - (z_i - z_0)/(z_1 - z_0)]\}$, with two constants $z_0 < z_1$.
3. Keep $\chi_i$ only where the flow converges, $v_{x,i-1} > v_{x,i+1}$, and the relative jump of the pressure exceeds a threshold, and set $\chi_i = 1$ elsewhere.
4. Take the smallest coefficient over both directions, each at the cell and at its neighbour towards lower pressure.

Flattening widens the stencil to four ghost cells. Contacts do not steepen, as their characteristics run parallel, and the original PPM steepens them artificially, which can cause problems in several dimensions. **[GK]** Eq. 8.51 of Zingale's text blends the right state at $x_{i+1/2}$, which cell $i + 1$ supplies, with $\mathbf{W}_i$; the form above blends each state with the cell that supplies it, as pyro does.

Detail: [Zingale 2.5.13](../references/computational-hydrodynamics-synthesis.md#2513-flattening-contact-steepening-and-characteristic-limiting), [pyro 2.1.6](../references/pyro-synthesis.md#216-flattening), [pyro 2.4.2](../references/pyro-synthesis.md#242-interface-states).

## 3. Tests

Linear advection tests the reconstruction apart from the rest of the scheme, as its exact solution is the initial profile shifted. A smooth profile measures the order of convergence, which should match the formal order of each method. Zingale's text advects a Gaussian for five periods at $\mathcal{C} = 0.8$ with centred, MC and minmod slopes. ZEUS advects a Gaussian over ten times its width with donor cell, the van Leer method and PPA, and takes the $L_1$ error on a sequence of grids (Stone and Norman 1992a, §5.1, eq. 88).

A discontinuous profile tests monotonicity and sharpness. Zingale's text advects a top hat with constant, centred, minmod, MC and superbee slopes, ZEUS a square pulse 50 zones wide over five times its width, and Ulula a blob with constant states, minmod and MC under two integrators. The width of the smeared edges and any new extrema measure the methods, and the area under the pulse checks conservation.

Detail: [Zingale 2.3.11](../references/computational-hydrodynamics-synthesis.md#2311-convergence-and-the-choice-of-limiter), [ZEUS 2.7.1](../references/zeus-synthesis.md#271-approach-and-advection-tests), [Ulula 2.5.2](../references/ulula-synthesis.md#252-slope-limiters).

## 4. Assessment

On the Gaussian of Zingale's text, unlimited centred slopes converge at second order, MC comes close with errors a few times larger, and minmod gives errors about ten times larger at a lower rate. ZEUS measures the rates 3.0 for PPA, 2.1 for the van Leer method and 0.6 for donor cell, whose error on the finest grid exceeds that of PPA more than a thousandfold. On the square pulse the van Leer method spreads each edge over about 14 zones, PPA over 6 and PPA with steepening over 2, while donor cell loses the shape, and every scheme keeps the area to one part in $10^7$ to $10^8$. Ulula's blob turns unstable with MC under the Euler integrator, but is sharpest with MC under the Hancock step, and MC can cause effects at the edges of a shock tube. Stone et al. (2008) find that the limiters of Colella and Sekora (2008) improve some tests markedly, and that faster convergence of the reconstruction is not always the best route to accuracy. Stone and Norman (1992a) are unsure that PPA beats the van Leer method at a higher resolution in several dimensions. **[GK]** The limiter matters as much as the order of the profile: on smooth data minmod loses an order of magnitude in error against unlimited slopes and MC only a few times, while every TVD limiter clips smooth extrema. The harmonic mean and MC are the usual compromise, MC the sharper and the closer to instability. PPM with a limiter that preserves extrema keeps contacts and smooth extrema sharper, at the cost of a wider stencil, three ghost cells and more work per face, and WENO of fifth order shares the stencil of PPM, at a cost per face that no reference measures. Characteristic limiting suppresses oscillations better, especially in MHD, but needs the eigensystem, which Athena++ provides only for an ideal gas, although Zingale\'s text gives one for a general equation of state, and can leave states that need floors. Open are which limiter suits contacts and mixing layers in production runs, whether characteristic variables repay their cost where general equations of state are also wanted, and whether limiting in several dimensions at once, which no reference implements, is needed.

## 5. Sources

- <a id="borges-et-al-2008"></a>Borges, R., Carmona, M., Costa, B. and Don, W. S., An improved weighted essentially non-oscillatory scheme for hyperbolic conservation laws, Journal of Computational Physics 227, 3191–3211 (2008), [doi:10.1016/j.jcp.2007.11.038](https://doi.org/10.1016/j.jcp.2007.11.038).
- <a id="colella-1985"></a>Colella, P., A direct Eulerian MUSCL scheme for gas dynamics, SIAM Journal on Scientific and Statistical Computing 6, 104–117 (1985), [doi:10.1137/0906009](https://doi.org/10.1137/0906009).
- <a id="colella-sekora-2008"></a>Colella, P. and Sekora, M. D., A limiter for PPM that preserves accuracy at smooth extrema, Journal of Computational Physics 227, 7069–7076 (2008), [doi:10.1016/j.jcp.2008.03.034](https://doi.org/10.1016/j.jcp.2008.03.034).
- <a id="colella-woodward-1984"></a>Colella, P. and Woodward, P. R., The piecewise parabolic method (PPM) for gas-dynamical simulations, Journal of Computational Physics 54, 174–201 (1984), [doi:10.1016/0021-9991(84)90143-8](https://doi.org/10.1016/0021-9991%2884%2990143-8).
- <a id="diemer-2025"></a>Diemer, B., Ulula: an ultra-lightweight 2D hydrodynamics code for teaching and experimentation, preprint (2025), [arXiv:2505.20399](https://arxiv.org/abs/2505.20399), [2025arXiv250520399D](https://ui.adsabs.harvard.edu/abs/2025arXiv250520399D/abstract).
- <a id="felker-stone-2018"></a>Felker, K. G. and Stone, J. M., A fourth-order accurate finite volume method for ideal MHD via upwind constrained transport, Journal of Computational Physics 375, 1365–1400 (2018), [arXiv:1711.07439](https://arxiv.org/abs/1711.07439), [doi:10.1016/j.jcp.2018.08.025](https://doi.org/10.1016/j.jcp.2018.08.025).
- <a id="jiang-shu-1996"></a>Jiang, G.-S. and Shu, C.-W., Efficient implementation of weighted ENO schemes, Journal of Computational Physics 126, 202–228 (1996), [doi:10.1006/jcph.1996.0130](https://doi.org/10.1006/jcph.1996.0130).
- <a id="mccorquodale-et-al-2015"></a>McCorquodale, P., Dorr, M. R., Hittinger, J. A. F. and Colella, P., High-order finite-volume methods for hyperbolic conservation laws on mapped multiblock grids, Journal of Computational Physics 288, 181–195 (2015), [doi:10.1016/j.jcp.2015.01.006](https://doi.org/10.1016/j.jcp.2015.01.006).
- <a id="mignone-2014"></a>Mignone, A., High-order conservative reconstruction schemes for finite volume methods in cylindrical and spherical coordinates, Journal of Computational Physics 270, 784–814 (2014), [doi:10.1016/j.jcp.2014.04.001](https://doi.org/10.1016/j.jcp.2014.04.001).
- <a id="roe-1986"></a>Roe, P. L., Characteristic-based schemes for the Euler equations, Annual Review of Fluid Mechanics 18, 337–365 (1986), [doi:10.1146/annurev.fl.18.010186.002005](https://doi.org/10.1146/annurev.fl.18.010186.002005).
- <a id="saltzman-1994"></a>Saltzman, J., An unsplit 3D upwind method for hyperbolic conservation laws, Journal of Computational Physics 115, 153–168 (1994), [doi:10.1006/jcph.1994.1184](https://doi.org/10.1006/jcph.1994.1184).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="van-leer-1974"></a>van Leer, B., Towards the ultimate conservative difference scheme. II. Monotonicity and conservation combined in a second-order scheme, Journal of Computational Physics 14, 361–370 (1974), [doi:10.1016/0021-9991(74)90019-9](https://doi.org/10.1016/0021-9991%2874%2990019-9).
- <a id="van-leer-1977"></a>van Leer, B., Towards the ultimate conservative difference scheme. III. Upstream-centered finite-difference schemes for ideal compressible flow, Journal of Computational Physics 23, 263–275 (1977), [doi:10.1016/0021-9991(77)90094-8](https://doi.org/10.1016/0021-9991%2877%2990094-8).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

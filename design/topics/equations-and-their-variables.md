# The equations and their variables

## 1. Overview

Every scheme of the later topics solves a system of hyperbolic conservation laws, the Euler equations of gas dynamics or the equations of ideal MHD, written in one of three sets of variables ([`notation.md`](notation.md)). The conserved variables $\mathbf{U}$ carry the update and its conservation, the primitive variables $\mathbf{W}$ give the simplest matrix of the waves, and the characteristic variables $\mathbf{a}$ separate the waves from one another. Zingale's text derives the Euler equations, their primitive and characteristic forms and the other forms of the energy equation. pyro and Ulula solve the Euler equations in conservative form, Ulula with gravity. ZEUS writes hydrodynamics and MHD in Lagrangian form and evolves the internal energy instead of the total energy, while Athena++ solves ideal MHD in conservative form. None of the references derives the equations from kinetic theory, for which Zingale's text and ZEUS refer to textbooks. The equations of state beyond the ideal gas follow in topic 2, the numerical treatment of $\nabla\cdot\mathbf{B} = 0$ in topic 10, gravity and other sources in topic 12, diffusion in topic 15 and relativistic MHD in topic 22.

## 2. Methods

### 2.1 Hyperbolic equations and their characteristics

Partial differential equations fall into three classes, each with a prototype ([Zingale's text](#zingale-2025), eqs. 2.1 to 2.6). The wave equation is hyperbolic and carries information at finite speeds, the Poisson equation is elliptic and responds at once throughout the domain to its source and boundaries, and the heat equation is parabolic and smooths features on a diffusive timescale. The schemes for each class are developed apart and combined later, the elliptic ones in topic 13 and the parabolic ones in topic 15.

The model of a hyperbolic equation is the advection of a scalar $u$ at a constant velocity $v$ (eq. 2.3), which moves any profile unchanged:

$$\frac{\partial u}{\partial t} + v\,\frac{\partial u}{\partial x} = 0.$$

A linear system $\partial\mathbf{U}/\partial t + \mathsf{A}\,\partial\mathbf{U}/\partial x = 0$ is hyperbolic if the eigenvalues of $\mathsf{A}$ are real (eq. 2.4). Its characteristics, the curves $dx/dt = \lambda^{(m)}$ in the space-time plane, are the paths along which information travels, and for a linear problem they determine the solution completely. **[GK]** The standard definition also requires $\mathsf{A}$ to be diagonalisable, so that its eigenvectors can split any data into waves ([LeVeque](#leveque-2002) 2002, §2.9).

The model of a nonlinear hyperbolic equation is Burgers' equation (eq. 6.1), in which the scalar is its own speed:

$$\frac{\partial u}{\partial t} + u\,\frac{\partial u}{\partial x} = 0.$$

Its value is constant along the characteristics $dx/dt = u$ (eqs. 6.2 and 6.3), which are no longer parallel. Where they converge they meet in a shock, and where they diverge they leave a rarefaction to be filled with intermediate states (figs. 6.1 and 6.2). Neither wave exists in a linear problem. **[GK]** Each characteristic is the straight line $x = x_0 + u_0(x_0)\,t$ for as long as the solution is smooth, and neighbouring ones first meet at the breaking time $t_\mathrm{b} = -1/\min_x u_0'(x)$ ([LeVeque](#leveque-2002) 2002, §11.2).

Detail: [Zingale 2.1.9](../references/computational-hydrodynamics-synthesis.md#219-classes-of-partial-differential-equations), [Zingale 2.4.1](../references/computational-hydrodynamics-synthesis.md#241-characteristics-shocks-and-rarefactions).

### 2.2 The Euler equations in conservative form

The Euler equations state the conservation of mass, momentum and energy of an inviscid fluid ([Zingale's text](#zingale-2025), eqs. 7.1 to 7.4):

$$\frac{\partial\rho}{\partial t} + \nabla\cdot(\rho\mathbf{v}) = 0, \qquad \frac{\partial(\rho\mathbf{v})}{\partial t} + \nabla\cdot(\rho\mathbf{v}\mathbf{v}) + \nabla p = 0, \qquad \frac{\partial E}{\partial t} + \nabla\cdot\left[(E + p)\,\mathbf{v}\right] = 0,$$

with the total energy density $E = \rho e + \rho v^2/2$. In one dimension they take the conservative form $\partial\mathbf{U}/\partial t + \partial\mathbf{F}/\partial x = 0$ with (eqs. 7.7 to 7.11)

$$\mathbf{U} = \begin{pmatrix} \rho \\ \rho v_x \\ E \end{pmatrix}, \qquad \mathbf{F} = \begin{pmatrix} \rho v_x \\ \rho v_x^2 + p \\ (E + p)\, v_x \end{pmatrix}.$$

An equation of state closes the system, most simply the ideal gas $p = (\gamma - 1)\rho e$, with $\gamma = 5/3$ for a monatomic gas, although any $p(\rho, e)$ serves (eqs. 7.5 and 7.6; topic 2). The temperature does not enter the equations, only the sources that need it. Viscous and other dissipative terms act on scales far below those of astrophysical systems, whose Reynolds numbers are very large, and are left to topic 15.

pyro, Ulula and Athena++ evolve these conserved variables and convert them to primitive ones wherever a flux or a reconstruction needs them. pyro carries passive scalars as further components (topic 18), and Ulula counts the potential energy $\rho\Phi$ in its total energy (topic 12). Ulula computes the flux of one direction from a primitive state, with the velocities along and across that direction, so that one function serves both sweeps. The conversion from conserved to primitive variables runs as follows.

1. Divide the momentum by the density, $\mathbf{v} = (\rho\mathbf{v})/\rho$.
2. Subtract the kinetic energy, and in MHD the magnetic energy, $\rho e = E - \rho v^2/2 - B^2/2$.
3. Obtain the pressure from the equation of state, $p = (\gamma - 1)\rho e$ for an ideal gas.
4. Check that $\rho$ and $p$ are positive, or apply a floor (topic 2).

The inverse sets the momentum $\rho\mathbf{v}$ and the energy $E = p/(\gamma - 1) + \rho v^2/2 + B^2/2$. pyro sets the velocity to zero where the density vanishes.

Detail: [Zingale 2.5.1](../references/computational-hydrodynamics-synthesis.md#251-conservation-laws-and-the-equation-of-state), [pyro 2.4.1](../references/pyro-synthesis.md#241-variables-and-equation-of-state), [Ulula 2.1.1](../references/ulula-synthesis.md#211-the-euler-equations-with-gravity), [Ulula 2.1.3](../references/ulula-synthesis.md#213-primitive-and-conserved-variables), [Ulula 2.1.4](../references/ulula-synthesis.md#214-the-flux-vector).

### 2.3 The quasi-linear, primitive and characteristic forms

By the chain rule, the conservative form becomes the quasi-linear form $\partial\mathbf{U}/\partial t + \mathsf{A}(\mathbf{U})\,\partial\mathbf{U}/\partial x = 0$ with the Jacobian $\mathsf{A} = \partial\mathbf{F}/\partial\mathbf{U}$ ([Zingale's text](#zingale-2025), eqs. 7.14 and 7.15), a complicated matrix. The primitive variables $\mathbf{W} = (\rho, v_x, p)^\mathsf{T}$ give a simpler one (eqs. 7.16 to 7.20):

$$\frac{\partial\mathbf{W}}{\partial t} + \mathsf{A}(\mathbf{W})\,\frac{\partial\mathbf{W}}{\partial x} = 0, \qquad \mathsf{A}(\mathbf{W}) = \begin{pmatrix} v_x & \rho & 0 \\ 0 & v_x & 1/\rho \\ 0 & \gamma p & v_x \end{pmatrix}.$$

Its eigenvalues, from $\det(\mathsf{A} - \lambda\mathsf{I}) = 0$, are $\lambda^{(1)} = v_x - c_\mathrm{s}$, $\lambda^{(2)} = v_x$ and $\lambda^{(3)} = v_x + c_\mathrm{s}$, with $c_\mathrm{s}^2 = \gamma p/\rho$. They are the speeds of the two sound waves and of the fluid itself, the same for both matrices. As they are real the system is hyperbolic, and as $\mathsf{A}$ depends on $\mathbf{W}$ it is quasi-linear. A general equation of state replaces $\gamma$ in the pressure equation by the first adiabatic index $\Gamma_1 = \partial \ln p/\partial \ln \rho|_s$, so that $c_\mathrm{s}^2 = \Gamma_1 p/\rho$ (eqs. 7.21 and 7.22). **[GK]** The two matrices share their eigenvalues because they are similar: with $\mathsf{M} = \partial\mathbf{U}/\partial\mathbf{W}$, substituting $\mathbf{U}(\mathbf{W})$ into the quasi-linear form gives $\mathsf{A}(\mathbf{W}) = \mathsf{M}^{-1}\mathsf{A}(\mathbf{U})\,\mathsf{M}$.

The right and left eigenvectors, normalised so that $\mathbf{l}^{(m)}\cdot\mathbf{r}^{(n)} = \delta_{mn}$, are (eqs. 7.23 to 7.27)

$$\mathbf{r}^{(1,3)} = \begin{pmatrix} 1 \\ \mp c_\mathrm{s}/\rho \\ c_\mathrm{s}^2 \end{pmatrix}, \quad \mathbf{r}^{(2)} = \begin{pmatrix} 1 \\ 0 \\ 0 \end{pmatrix}, \quad \mathbf{l}^{(1,3)} = \left(0,\ \mp\frac{\rho}{2c_\mathrm{s}},\ \frac{1}{2c_\mathrm{s}^2}\right), \quad \mathbf{l}^{(2)} = \left(1,\ 0,\ -\frac{1}{c_\mathrm{s}^2}\right),$$

with the upper sign for $m = 1$ and the lower for $m = 3$. Multiplying the primitive system by $\mathsf{L}$ and inserting $\mathsf{R}\mathsf{L} = \mathsf{I}$ between $\mathsf{A}$ and the derivative gives, with $\mathsf{L}\mathsf{A}\mathsf{R} = \mathsf{\Lambda}$ and $d\mathbf{a} = \mathsf{L}\,d\mathbf{W}$, the characteristic form (eqs. 7.28 to 7.36):

$$\mathsf{L}\,\frac{\partial\mathbf{W}}{\partial t} + (\mathsf{L}\mathsf{A}\mathsf{R})\,\mathsf{L}\,\frac{\partial\mathbf{W}}{\partial x} = 0 \quad\Longrightarrow\quad \frac{\partial\mathbf{a}}{\partial t} + \mathsf{\Lambda}\,\frac{\partial\mathbf{a}}{\partial x} = 0.$$

These are three decoupled advection equations, $\partial a^{(m)}/\partial t + \lambda^{(m)}\,\partial a^{(m)}/\partial x = 0$. In a linear system each $a^{(m)}$ is advected at its own speed, but in general $d\mathbf{a} = \mathsf{L}\,d\mathbf{W}$ cannot be integrated, and the decomposition holds only locally. A jump in the data splits into the jumps of the waves, approximately because $\mathsf{L}$ depends on $\mathbf{W}$, and the jump across wave $m$ is proportional to $\mathbf{r}^{(m)}$. Across the middle wave, the contact, only the density jumps. Sod's shock tube (topic 27) shows all three: a rarefaction, a contact and a shock. Reconstruction and the Riemann solvers decompose a jump in this way (topics 5 and 6).

1. Evaluate $\mathsf{L}$ and $\mathsf{R}$ at a reference state, such as the state of the cell.
2. Project the jump onto the waves, $\delta\mathbf{a} = \mathsf{L}\,\delta\mathbf{W}$.
3. Treat each component $\delta a^{(m)}$ on its own, by its speed $\lambda^{(m)}$ or by a limiter.
4. Recombine the waves, $\delta\mathbf{W} = \mathsf{R}\,\delta\mathbf{a} = \sum_m \delta a^{(m)}\,\mathbf{r}^{(m)}$.

Detail: [Zingale 2.5.2](../references/computational-hydrodynamics-synthesis.md#252-quasi-linear-and-primitive-forms), [Zingale 2.5.3](../references/computational-hydrodynamics-synthesis.md#253-eigenvectors-and-the-characteristic-form).

### 2.4 The forms of the energy equation

Without heat sources, the first law, $de + p\,d(1/\rho) = 0$ for a fluid element, together with the continuity equation gives the equation of the internal energy ([Zingale's text](#zingale-2025), eqs. 7.95 to 7.99):

$$\rho\,\frac{De}{Dt} + p\,\nabla\cdot\mathbf{v} = 0 \quad\Longleftrightarrow\quad \frac{\partial(\rho e)}{\partial t} + \nabla\cdot(\rho e\,\mathbf{v}) + p\,\nabla\cdot\mathbf{v} = 0,$$

with $D/Dt = \partial/\partial t + \mathbf{v}\cdot\nabla$. The term $p\,\nabla\cdot\mathbf{v}$ is not in conservative form, so that the internal energy is not conserved. The specific enthalpy $h = e + p/\rho$ obeys $\rho\,Dh/Dt = Dp/Dt$ and is conserved where the pressure is constant along the flow, and equations for the temperature follow with the specific heats $c_v$ and $c_p$ (eqs. 7.100 to 7.108). They serve flows of very low Mach number and reactive flow (topic 17).

ZEUS evolves $\rho$, $\mathbf{v}$ and the internal energy density $\rho e$ in Lagrangian form ([Stone and Norman](#stone-norman-1992a) 1992a, eqs. 1 to 5):

$$\frac{D\rho}{Dt} + \rho\,\nabla\cdot\mathbf{v} = 0, \qquad \rho\,\frac{D\mathbf{v}}{Dt} = -\nabla p - \rho\nabla\Phi, \qquad \rho\,\frac{De}{Dt} = -p\,\nabla\cdot\mathbf{v},$$

closed by an equation of state and the Poisson equation for the potential $\Phi$. The internal energy, and with it the temperature, then stays accurate in highly supersonic flows. **[GK]** There the kinetic energy dominates, and an internal energy found by subtracting it from the total energy inherits its truncation errors and can turn negative. The price is that the total energy is no longer conserved to round-off.

ZEUS adds the compressional heating $-p\,\nabla\cdot\mathbf{v}$ as a substep of its operator-split update (topic 16), implicitly with the time-centred pressure (Stone and Norman 1992a, eqs. 39 to 42). With $n+b$ and $n+c$ marking the states before and after the substep, the update $(\rho e)^{n+c} - (\rho e)^{n+b} = -\Delta t\,p^{n+1/2}\,\nabla\cdot\mathbf{v}$ with $p^{n+1/2} = \tfrac{1}{2}(p^{n+b} + p^{n+c})$ and $p = (\gamma - 1)\rho e$ is linear in $(\rho e)^{n+c}$, and its solution for an ideal gas is

$$(\rho e)^{n+c} = (\rho e)^{n+b}\, \frac{1 - \tfrac{1}{2}\Delta t\,(\gamma - 1)\,\nabla\cdot\mathbf{v}}{1 + \tfrac{1}{2}\Delta t\,(\gamma - 1)\,\nabla\cdot\mathbf{v}},$$

with the divergence centred in the cell. For other equations of state a predictor and a corrector take its place.

1. Predict $(\rho e)^\mathrm{pred} = (\rho e)^{n+b} - \Delta t\,p^{n}\,\nabla\cdot\mathbf{v}$ with the old pressure.
2. Obtain $p^\mathrm{pred}$ from $(\rho e)^\mathrm{pred}$ by the equation of state.
3. Correct with the mean pressure, $(\rho e)^{n+c} = (\rho e)^{n+b} - \tfrac{1}{2}\Delta t\,(p^{n} + p^\mathrm{pred})\,\nabla\cdot\mathbf{v}$.

Detail: [Zingale 2.5.9](../references/computational-hydrodynamics-synthesis.md#259-other-thermodynamic-equations), [ZEUS 2.1.1](../references/zeus-synthesis.md#211-the-equations-of-hydrodynamics), [ZEUS 2.3.3](../references/zeus-synthesis.md#233-compressional-heating).

### 2.5 The equations of ideal MHD

Athena++ solves the equations of ideal MHD in conservative form, in units in which the magnetic permeability is one ([Stone et al.](#stone-et-al-2008) 2008, eqs. 1 to 5):

$$\begin{aligned}
&\frac{\partial\rho}{\partial t} + \nabla\cdot(\rho\mathbf{v}) = 0, \\
&\frac{\partial(\rho\mathbf{v})}{\partial t} + \nabla\cdot\left(\rho\mathbf{v}\mathbf{v} - \mathbf{B}\mathbf{B} + p_\mathrm{T}\,\mathsf{I}\right) = 0, \\
&\frac{\partial E}{\partial t} + \nabla\cdot\left[(E + p_\mathrm{T})\,\mathbf{v} - \mathbf{B}\,(\mathbf{B}\cdot\mathbf{v})\right] = 0, \\
&\frac{\partial\mathbf{B}}{\partial t} - \nabla\times(\mathbf{v}\times\mathbf{B}) = 0,
\end{aligned}$$

with the total pressure $p_\mathrm{T} = p + B^2/2$ and the total energy density $E = p/(\gamma - 1) + \rho v^2/2 + B^2/2$. With $\mathbf{U} = (\rho, \rho\mathbf{v}, E, \mathbf{B})$ and $\mathbf{W} = (\rho, \mathbf{v}, p, \mathbf{B})$, the system is $\partial\mathbf{U}/\partial t + \partial\mathbf{F}/\partial x + \partial\mathbf{G}/\partial y + \partial\mathbf{H}/\partial z = 0$, with the flux along $x$ (eqs. 6 to 8)

$$\mathbf{F} = \begin{pmatrix} \rho v_x \\ \rho v_x^2 + p_\mathrm{T} - B_x^2 \\ \rho v_x v_y - B_x B_y \\ \rho v_x v_z - B_x B_z \\ (E + p_\mathrm{T})\,v_x - (\mathbf{B}\cdot\mathbf{v})\,B_x \\ 0 \\ B_y v_x - B_x v_y \\ B_z v_x - B_x v_z \end{pmatrix},$$

and $\mathbf{G}$ and $\mathbf{H}$ by permuting the directions, each with a zero for the field along its own direction. In one dimension $B_x$ is therefore constant, and a state of a Riemann problem of MHD carries seven variables, or six for an isothermal gas. The same equations without the field are those of hydrodynamics, and a barotropic gas, such as an isothermal one with $p = c_\mathrm{s}^2\rho$, drops the energy equation and with it the conservation of energy. Athena++ thus solves four systems with the same methods. It keeps the field on the faces of the cells and evolves it by constrained transport, apart from the other variables (topic 10).

ZEUS writes MHD in Lagrangian form, with the continuity and internal energy equations of 2.4 ([Stone and Norman](#stone-norman-1992b) 1992b, eqs. 1 to 4). In the units used here, the equation of motion gains the Lorentz force, and the induction equation evolves the field:

$$\rho\,\frac{D\mathbf{v}}{Dt} = -\nabla p - \rho\nabla\Phi + (\nabla\times\mathbf{B})\times\mathbf{B}, \qquad \frac{\partial\mathbf{B}}{\partial t} = \nabla\times(\mathbf{v}\times\mathbf{B}).$$

The equations assume quasi-neutrality and close the current by Ohm's law, of which only the advective term is kept, so that the field is frozen into the fluid. They also omit the displacement current, which holds for phenomena of low frequency. ZEUS-2D has neither resistivity nor ambipolar diffusion (topic 15). **[GK]** The printed eq. 2 has $p\nabla\Phi$ in place of $\rho\nabla\Phi$, a misprint.

MHD brings two difficulties that hydrodynamics lacks (Stone and Norman 1992b, §3). The field must stay free of divergence, $\nabla\cdot\mathbf{B} = 0$, at all times, and unless a scheme builds the constraint in, its errors grow until the calculation must stop. MHD also has new families of waves, among them the incompressible, transverse Alfvén waves, which upwind schemes for hydrodynamics propagate with a large dispersion error. Both shape the schemes for the field in topic 10.

Detail: [ZEUS 2.8.1](../references/zeus-synthesis.md#281-the-equations-of-magnetohydrodynamics), [ZEUS 2.8.2](../references/zeus-synthesis.md#282-the-divergence-constraint-and-the-wave-families), [Athena 2.1.1](../references/athena-synthesis.md#211-the-equations-of-ideal-mhd), [Athena 2.1.4](../references/athena-synthesis.md#214-the-variables-in-the-code).

## 3. Assessment

**[GK]** The conservative form with the total energy suits Godunov schemes best. It conserves mass, momentum and energy to round-off, and by the theorem of Lax and Wendroff a conservative scheme that converges gives shocks the right speeds and jumps ([LeVeque](#leveque-2002) 2002, ch. 12), while Zingale's text shows a nonconservative difference of Burgers' equation moving a shock at the wrong speed (eq. 6.20). Its weak point is the internal energy, found by subtraction, which loses accuracy and can turn negative where the kinetic or magnetic energy dominates. Evolving the internal energy, as ZEUS does, keeps the temperature accurate in such flows, but gives up the conservation of energy, so that the heating at shocks rests on the artificial viscosity (topic 9). The primitive and characteristic forms cost conversions and eigenvectors and never carry the update, but they give the waves that reconstruction and the Riemann solvers need. The questions left open are which energy equation suits the supersonic clouds of the production runs, perhaps both together (topic 2), whether the adiabatic and isothermal systems share one path through the code, as in Athena++, and whether the field is kept with the cell-centred variables or on the faces (topic 10).

## 4. Sources

- <a id="leveque-2002"></a>LeVeque, R. J., Finite Volume Methods for Hyperbolic Problems, Cambridge University Press (2002), [doi:10.1017/CBO9780511791253](https://doi.org/10.1017/CBO9780511791253).
- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-norman-1992a"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. I. The hydrodynamic algorithms and tests, ApJS 80, 753–790 (1992), [doi:10.1086/191680](https://doi.org/10.1086/191680).
- <a id="stone-norman-1992b"></a>Stone, J. M. and Norman, M. L., ZEUS-2D: a radiation magnetohydrodynamics code for astrophysical flows in two space dimensions. II. The magnetohydrodynamic algorithms and tests, ApJS 80, 791–818 (1992), [doi:10.1086/191681](https://doi.org/10.1086/191681).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

# Notation of the topic summaries

All topic summaries share the notation set out here, as `plan.md` requires. It fixes the symbols for the variables, the indices of cells, faces and time levels, the states on either side of a face and the fluxes. A symbol that it does not fix is defined in the summary where it first appears, and later summaries keep it. The syntheses keep the notation of their references, which the last table relates to the one used here.

## Conventions

Vectors are bold, as $\mathbf{U}$ and $\mathbf{v}$, matrices and tensors are sans-serif, as $\mathsf{A}$, and scalars are italic. Subscripts that label rather than count are upright, as in $c_\mathrm{s}$ and $\mathbf{W}_\mathrm{L}$. In a subscript, a label or a component comes first and the indices of a position follow, as in $B_{x,i-1/2,j,k}$, and indices that do not change are dropped. The time level is a superscript, as in $\mathbf{U}^n_i$.

The magnetic field is measured in units in which the magnetic permeability is one, as in Athena, so that the magnetic pressure is $B^2/2$. **[GK]** A field in Gaussian units, as in ZEUS, is $\sqrt{4\pi}$ times larger.

## Variables

The equations take the form $\partial\mathbf{U}/\partial t + \partial\mathbf{F}/\partial x + \partial\mathbf{G}/\partial y + \partial\mathbf{H}/\partial z = \mathbf{S}$. In hydrodynamics, the field drops out of $\mathbf{U}$ and $\mathbf{W}$.

| Symbol | Meaning |
|---|---|
| $\rho$ | mass density |
| $\mathbf{v} = (v_x, v_y, v_z)$ | velocity |
| $p$ | gas pressure |
| $e$ | specific internal energy, per unit mass |
| $E$ | total energy density, $\rho e + \rho v^2/2 + B^2/2$ |
| $\mathbf{B} = (B_x, B_y, B_z)$ | magnetic field |
| $p_\mathrm{T}$ | total pressure, $p + B^2/2$ |
| $\gamma$ | adiabatic index, with $p = (\gamma - 1)\rho e$ for an ideal gas |
| $\mathbf{U}$ | conserved variables, $(\rho, \rho\mathbf{v}, E, \mathbf{B})$ |
| $\mathbf{W}$ | primitive variables, $(\rho, \mathbf{v}, p, \mathbf{B})$ |
| $\mathbf{F}$, $\mathbf{G}$, $\mathbf{H}$ | fluxes of $\mathbf{U}$ along $x$, $y$ and $z$ |
| $\mathbf{S}$ | source terms |
| $c_\mathrm{s}$ | sound speed, adiabatic or isothermal as the equation of state gives it |
| $c_\mathrm{A}$, $c_\mathrm{fast}$, $c_\mathrm{slow}$ | Alfvén, fast and slow magnetosonic speeds along the direction considered |
| $c$ | speed of light |

## Discretisation

| Symbol | Meaning |
|---|---|
| $i$, $j$, $k$ | indices of the cells along $x$, $y$ and $z$ |
| $x_i$, $x_{i \pm 1/2}$ | centre and faces of cell $i$ |
| $\Delta x_i$ | width $x_{i+1/2} - x_{i-1/2}$ of cell $i$, written $\Delta x$ on a uniform grid |
| $t^n$, $\Delta t$ | time level $n$ and time step $t^{n+1} - t^n$, with $n + 1/2$ for the midpoint |
| $\mathbf{U}_i$ | state of cell $i$, which at second order stands for both its average and its value at the centre |
| $\langle\mathbf{U}\rangle_i$ | cell average, where it must be told apart from the value $\mathbf{U}_i$ at the centre |
| $\delta\mathbf{W}_i$ | difference or slope of the primitive variables across cell $i$ |
| $\mathbf{W}_{\mathrm{L},i+1/2}$, $\mathbf{W}_{\mathrm{R},i+1/2}$ | states to the left and right of the face $x_{i+1/2}$ |
| $\mathbf{U}^*$ | a state between the waves of a Riemann problem |
| $\mathbf{F}_{i+1/2}$ | numerical flux through the face $x_{i+1/2}$, and likewise $\mathbf{G}_{j+1/2}$ and $\mathbf{H}_{k+1/2}$ |
| $\mathcal{C}$ | Courant number |

## Characteristic structure

| Symbol | Meaning |
|---|---|
| $\mathsf{A}$ | matrix of the quasi-linear form $\partial\mathbf{W}/\partial t + \mathsf{A}\,\partial\mathbf{W}/\partial x = 0$, or the Jacobian $\partial\mathbf{F}/\partial\mathbf{U}$ where a summary says so |
| $\lambda^{(m)}$ | eigenvalue of the wave family $m$, in ascending order |
| $\mathbf{r}^{(m)}$, $\mathbf{l}^{(m)}$ | right and left eigenvectors of the family $m$ |
| $\mathsf{R}$, $\mathsf{L}$, $\mathsf{\Lambda}$ | matrices with the right eigenvectors as columns, the left ones as rows and the eigenvalues on the diagonal, with $\mathsf{L} = \mathsf{R}^{-1}$ |
| $\mathbf{a}$ | characteristic variables, with $\delta\mathbf{a} = \mathsf{L}\,\delta\mathbf{W}$ and the components $a^{(m)}$ |

## The references

The syntheses keep the symbols of their references. A dash marks a quantity for which a synthesis gives no symbol.

| Quantity | Here | Zingale | pyro | Ulula | ZEUS | Athena |
|---|---|---|---|---|---|---|
| Conserved variables | $\mathbf{U}$ | $\boldsymbol{\mathcal{U}}$ | $\mathbf{U}$ | $\boldsymbol{U}$ | — | $\mathbf{U}$ |
| Primitive variables | $\mathbf{W}$ | $\mathbf{q}$ | $\mathbf{q}$ | $\boldsymbol{V}$ | — | $\mathbf{W}$, and $\mathbf{q}$ or $\mathbf{w}$ in reconstruction |
| Characteristic variables | $\mathbf{a}$ | $\mathbf{w}$ | — | — | — | $\mathbf{a}$ |
| Velocity | $\mathbf{v}$ | $\mathbf{U}$, with $u$ and $v$ | $\mathbf{U}$, with $u$ and $v$ | $v_x$, $v_y$ | $\mathbf{v}$ | $\mathbf{v}$ |
| Gas pressure | $p$ | $p$ | $p$ | $P$ | $p$ | $P$, at times $p$ |
| Internal energy | $e$, per mass | $e$, per mass | — | $\varepsilon$, per mass | $e$, per volume | $e$, per volume, or $\epsilon$, per mass |
| Total energy | $E$, per volume | $\rho E$ | $\rho E$ | $E$ | — | $E$ |
| Sound speed | $c_\mathrm{s}$ | $c$ | $c$ | $c_\mathrm{s}$ | $C_a$ | $a$, or $C$ if isothermal |
| Units of the field | permeability one | — | — | — | $1/4\pi$ in the Lorentz force | permeability one |
| Courant number | $\mathcal{C}$ | $\mathcal{C}$ | — | $\alpha_\mathrm{cfl}$ | $C_0$ | $C_\circ$ or $C_0$ |
| Cell width and time step | $\Delta x$, $\Delta t$ | $\Delta x$, $\Delta t$ | $\Delta x$, $\Delta t$ | $\Delta x$, $\Delta t$ | $\Delta x$, $\Delta t$ | $\delta x$, $\delta t$, or $h$ and $\Delta t$ at fourth order |
| Eigenvectors and eigenvalues | $\mathsf{R}$, $\lambda^{(m)}$ | $\mathbf{R}$, $\lambda^{(\nu)}$ | — | — | — | $\mathsf{R}$, $\lambda^\alpha$ |

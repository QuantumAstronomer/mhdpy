"""JAX kernel of experiment E04.1: the NumPy code of ``E04.1a-hydro2d-numpy.py`` in ``jax.numpy``, compiled by XLA.

Idiomatic JAX compiles the whole step (both RK stages and the periodic ghost fill) into one function, which lets XLA
fuse operations across it; this is done here. Double precision is enabled explicitly (JAX defaults to float32).
"""

import jax

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp  # noqa: E402

GAMMA = 1.4
G = 2


def cons_to_prim(u):
    rho = u[0]
    vx = u[1] / rho
    vy = u[2] / rho
    return jnp.stack([rho, vx, vy, (GAMMA - 1.0) * (u[3] - 0.5 * rho * (vx * vx + vy * vy))])


def mc_slope(left, right):
    limited = jnp.minimum(jnp.minimum(2.0 * jnp.abs(left), 2.0 * jnp.abs(right)), 0.5 * jnp.abs(left + right))
    return jnp.where(left * right > 0.0, jnp.where(left > 0.0, limited, -limited), 0.0)


def hll(wl, wr):
    rl, ul, vl, pl = wl
    rr, ur, vr, pr = wr
    cl = jnp.sqrt(GAMMA * pl / rl)
    cr = jnp.sqrt(GAMMA * pr / rr)
    sl = jnp.minimum(ul - cl, ur - cr)
    sr = jnp.maximum(ul + cl, ur + cr)
    el = pl / (GAMMA - 1.0) + 0.5 * rl * (ul * ul + vl * vl)
    er = pr / (GAMMA - 1.0) + 0.5 * rr * (ur * ur + vr * vr)
    fl = jnp.stack([rl * ul, rl * ul * ul + pl, rl * ul * vl, (el + pl) * ul])
    fr = jnp.stack([rr * ur, rr * ur * ur + pr, rr * ur * vr, (er + pr) * ur])
    ql = jnp.stack([rl, rl * ul, rl * vl, el])
    qr = jnp.stack([rr, rr * ur, rr * vr, er])
    star = (sr * fl - sl * fr + sl * sr * (qr - ql)) / (sr - sl)
    return jnp.where(sl >= 0.0, fl, jnp.where(sr <= 0.0, fr, star))


def fill_ghosts(u):
    inner = u[:, G:-G, G:-G]
    return jnp.pad(inner, ((0, 0), (G, G), (G, G)), mode="wrap")


def rhs(u, dx):
    n = u.shape[1] - 2 * G
    w = cons_to_prim(u)
    sx = mc_slope(w[:, 1:-1, G:-G] - w[:, :-2, G:-G], w[:, 2:, G:-G] - w[:, 1:-1, G:-G])
    wl = w[:, G - 1 : G + n, G:-G] + 0.5 * sx[:, G - 2 : G + n - 1]
    wr = w[:, G : G + n + 1, G:-G] - 0.5 * sx[:, G - 1 : G + n]
    fx = hll(wl, wr)
    sy = mc_slope(w[:, G:-G, 1:-1] - w[:, G:-G, :-2], w[:, G:-G, 2:] - w[:, G:-G, 1:-1])
    wl = w[:, G:-G, G - 1 : G + n] + 0.5 * sy[:, :, G - 2 : G + n - 1]
    wr = w[:, G:-G, G : G + n + 1] - 0.5 * sy[:, :, G - 1 : G + n]
    perm = jnp.array([0, 2, 1, 3])
    fy = hll(wl[perm], wr[perm])[perm]
    return -(fx[:, 1:, :] - fx[:, :-1, :]) / dx - (fy[:, :, 1:] - fy[:, :, :-1]) / dx


@jax.jit
def step(u, dt, dx):
    stage = fill_ghosts(u.at[:, G:-G, G:-G].add(dt * rhs(u, dx)))
    new_inner = 0.5 * u[:, G:-G, G:-G] + 0.5 * (stage[:, G:-G, G:-G] + dt * rhs(stage, dx))
    return fill_ghosts(u.at[:, G:-G, G:-G].set(new_inner))

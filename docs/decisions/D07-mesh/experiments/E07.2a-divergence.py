"""Kernels of experiment E07.2: the flux divergence with three ways of supplying the geometry.

The finite-volume update of a cell is the sum of the fluxes through its faces, weighted with the face areas and divided
by the cell volume. In uniform Cartesian coordinates the weights reduce to one cell width; in curvilinear or nonuniform
coordinates they vary from cell to cell. The three kernels compute the same divergence of given fluxes, in the layout
of D06 (``[var, k, j, i]``, extent 1 and no flux in inactive directions):

- ``div_cartesian``: uniform Cartesian, one cell width, as in the E07.1a kernel;
- ``div_separable``: orthogonal coordinates (Cartesian, cylindrical, spherical polar, possibly nonuniform), where every
  face area and volume is a product of three one-dimensional factors, one per direction, stored as 1D arrays;
- ``div_full``: face areas and volumes stored as full arrays for every face and cell of the block.

With Cartesian values (areas 1, volume factors dx, 1, 1) all three give bit-for-bit the same result.
"""

import cython


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def div_cartesian(
    fx: cython.double[:, :, :, ::1], fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1],
    du: cython.double[:, :, :, ::1], nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t,
    dx: cython.double,
) -> None:
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    with cython.nogil:
        for v in range(du.shape[0]):
            for k in range(nz):
                for j in range(ny):
                    for i in range(nx):
                        du[v, k, j, i] = -(fx[v, k, j, i + 1] - fx[v, k, j, i]) / dx
        if ny > 1:
            for v in range(du.shape[0]):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (fy[v, k, j + 1, i] - fy[v, k, j, i]) / dx
        if nz > 1:
            for v in range(du.shape[0]):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (fz[v, k + 1, j, i] - fz[v, k, j, i]) / dx


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def div_separable(
    fx: cython.double[:, :, :, ::1], fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1],
    du: cython.double[:, :, :, ::1], nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t,
    a1i: cython.double[::1], a1j: cython.double[::1], a1k: cython.double[::1],
    a2i: cython.double[::1], a2j: cython.double[::1], a2k: cython.double[::1],
    a3i: cython.double[::1], a3j: cython.double[::1], a3k: cython.double[::1],
    vi: cython.double[::1], vj: cython.double[::1], vk: cython.double[::1],
) -> None:
    """Face areas A1 = a1i[i] a1j[j] a1k[k] (a1i at faces, a1j and a1k at cell centres), likewise A2, A3; V = vi vj vk."""
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    with cython.nogil:
        for v in range(du.shape[0]):
            for k in range(nz):
                for j in range(ny):
                    for i in range(nx):
                        du[v, k, j, i] = -(a1i[i + 1] * a1j[j] * a1k[k] * fx[v, k, j, i + 1]
                                           - a1i[i] * a1j[j] * a1k[k] * fx[v, k, j, i]) / (vi[i] * vj[j] * vk[k])
        if ny > 1:
            for v in range(du.shape[0]):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (a2i[i] * a2j[j + 1] * a2k[k] * fy[v, k, j + 1, i]
                                                               - a2i[i] * a2j[j] * a2k[k] * fy[v, k, j, i]) / (
                                vi[i] * vj[j] * vk[k])
        if nz > 1:
            for v in range(du.shape[0]):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (a3i[i] * a3j[j] * a3k[k + 1] * fz[v, k + 1, j, i]
                                                               - a3i[i] * a3j[j] * a3k[k] * fz[v, k, j, i]) / (
                                vi[i] * vj[j] * vk[k])


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
def div_full(
    fx: cython.double[:, :, :, ::1], fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1],
    du: cython.double[:, :, :, ::1], nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t,
    ax: cython.double[:, :, ::1], ay: cython.double[:, :, ::1], az: cython.double[:, :, ::1],
    vol: cython.double[:, :, ::1],
) -> None:
    """Face areas ax[k, j, i] (i at faces), ay, az and volumes vol[k, j, i] as full arrays."""
    v: cython.Py_ssize_t
    k: cython.Py_ssize_t
    j: cython.Py_ssize_t
    i: cython.Py_ssize_t
    with cython.nogil:
        for v in range(du.shape[0]):
            for k in range(nz):
                for j in range(ny):
                    for i in range(nx):
                        du[v, k, j, i] = -(ax[k, j, i + 1] * fx[v, k, j, i + 1] - ax[k, j, i] * fx[v, k, j, i]) / vol[
                            k, j, i]
        if ny > 1:
            for v in range(du.shape[0]):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (ay[k, j + 1, i] * fy[v, k, j + 1, i]
                                                               - ay[k, j, i] * fy[v, k, j, i]) / vol[k, j, i]
        if nz > 1:
            for v in range(du.shape[0]):
                for k in range(nz):
                    for j in range(ny):
                        for i in range(nx):
                            du[v, k, j, i] = du[v, k, j, i] - (az[k + 1, j, i] * fz[v, k + 1, j, i]
                                                               - az[k, j, i] * fz[v, k, j, i]) / vol[k, j, i]

# pyright: strict
"""B3E1: the step on slabs shared by processes, the ghost rows exchanged with the neighbours through MPI."""

import numpy as np
from mpi4py import MPI

from slabs import Array, Slab


def exchange(a: Array, comm: MPI.Intracomm) -> None:
    """Fill the two ghost rows on each side of the slab of this process from its neighbours, periodically."""
    up = (comm.Get_rank() + 1) % comm.Get_size()
    down = (comm.Get_rank() - 1) % comm.Get_size()
    received = np.empty((a.shape[0], 2, a.shape[2]))
    comm.Sendrecv(np.ascontiguousarray(a[:, -4:-2, :]), dest=up, recvbuf=received, source=down)
    a[:, :2, :] = received
    comm.Sendrecv(np.ascontiguousarray(a[:, 2:4, :]), dest=down, recvbuf=received, source=up)
    a[:, -2:, :] = received


def step(slab: Slab, comm: MPI.Intracomm) -> None:
    """Advance the slab of this process by one step of Heun's method."""
    exchange(slab.u, comm)
    slab.first()
    exchange(slab.u1, comm)
    slab.second()

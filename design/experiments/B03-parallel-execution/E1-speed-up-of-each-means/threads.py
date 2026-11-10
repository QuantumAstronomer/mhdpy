# pyright: strict
"""B3E1: the step on slabs shared by the threads of one process, the ghost rows copied between the slabs."""

from concurrent.futures import ThreadPoolExecutor

from slabs import Array, Slab


def exchange(arrays: list[Array]) -> None:
    """Fill the two ghost rows on each side of every slab from the interiors of its neighbours, periodically."""
    for k, a in enumerate(arrays):
        a[:, :2, :] = arrays[k - 1][:, -4:-2, :]
        a[:, -2:, :] = arrays[(k + 1) % len(arrays)][:, 2:4, :]


def step(slabs: list[Slab], pool: ThreadPoolExecutor) -> None:
    """Advance every slab by one step of Heun's method, the slabs of each stage shared among the threads."""
    exchange([slab.u for slab in slabs])
    list(pool.map(Slab.first, slabs))
    exchange([slab.u1 for slab in slabs])
    list(pool.map(Slab.second, slabs))

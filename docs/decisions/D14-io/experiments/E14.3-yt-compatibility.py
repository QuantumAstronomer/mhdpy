# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "h5py", "yt"]
# ///
"""Experiment E14.3: can existing analysis tools read mhdpy's block data, if it is written in Athena++'s layout?

Athena++ writes its block data to HDF5 files (``.athdf``) with a documented set of attributes and datasets: the root grid,
the block size, each block's logical location and refinement level, the coordinates of each block's faces and centres,
and the variables as arrays [var, block, k, j, i]. yt, the most widely used analysis package for astrophysical
simulations, reads such files, as do Athena++'s own Python reader and, through an XDMF description, VisIt and ParaView.

This experiment writes a 2D state held as mhdpy holds it (blocks of 50^2 cells with ghost cells, in Morton order, as one
array [block, var, k, j, i], D06/D07) to a file in that layout, together with a group of mhdpy's own metadata that
Athena++ does not have. It then checks:

- that yt 4 opens the file and recognises the fields (density, velocity, pressure, a passive scalar);
- that yt's uniform-grid view of the data equals the original global arrays bit for bit, including the placement of the
  blocks from their logical locations;
- that a reader of a few lines, assembling the blocks from their logical locations, gives the same result.

Run from this directory with:

    uv run --locked --script E14.3-yt-compatibility.py

Results are written to results/.
"""

import json
import platform
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np
import yt

HERE = Path(__file__).parent
RESULTS = HERE / "results"
NX, NY, B, G = 400, 100, 50, 2
NAMES = ["rho", "vel1", "vel2", "vel3", "press", "r0"]


def morton(cx: int, cy: int) -> int:
    code = 0
    for bit in range(16):
        code |= ((cx >> bit) & 1) << (2 * bit) | ((cy >> bit) & 1) << (2 * bit + 1)
    return code


LOCATIONS = sorted(((ci, cj) for cj in range(NY // B) for ci in range(NX // B)), key=lambda c: morton(*c))


def global_state() -> np.ndarray:
    """Primitive variables [var, y, x] on a domain [0, 4] x [0, 1]; every value distinct, to catch misplaced blocks."""
    rng = np.random.default_rng(143)
    x = (np.arange(NX) + 0.5) / NY
    y = (np.arange(NY) + 0.5) / NY
    yy, xx = np.meshgrid(y, x, indexing="ij")
    noise = rng.random((len(NAMES), NY, NX)) * 1e-3
    return np.array([1.0 + np.exp(-((xx - 1) ** 2 + (yy - 0.5) ** 2) / 0.02), -np.ones_like(xx), 0.1 * np.sin(xx),
                     np.zeros_like(xx), np.ones_like(xx), 0.1 + 0.9 * (xx < 1)]) + noise


def to_blocks(state: np.ndarray) -> np.ndarray:
    pack = np.zeros((len(LOCATIONS), len(NAMES), 1, B + 2 * G, B + 2 * G))
    for b, (ci, cj) in enumerate(LOCATIONS):
        pack[b, :, 0, G:-G, G:-G] = state[:, cj * B : (cj + 1) * B, ci * B : (ci + 1) * B]
    return pack


def write_athdf(path: Path, pack: np.ndarray, time: float, cycle: int) -> None:
    """Write the blocks in Athena++'s layout, plus a group of mhdpy's own metadata."""
    nb = len(LOCATIONS)
    dx = 1.0 / NY
    with h5py.File(path, "w") as f:
        f.attrs["NumCycles"] = np.int32(cycle)
        f.attrs["Time"] = time
        f.attrs["Coordinates"] = np.bytes_("cartesian")
        f.attrs["RootGridX1"] = np.array([0.0, NX * dx, 1.0])
        f.attrs["RootGridX2"] = np.array([0.0, NY * dx, 1.0])
        f.attrs["RootGridX3"] = np.array([-0.5 * dx, 0.5 * dx, 1.0])
        f.attrs["RootGridSize"] = np.array([NX, NY, 1], dtype=np.int32)
        f.attrs["NumMeshBlocks"] = np.int32(nb)
        f.attrs["MeshBlockSize"] = np.array([B, B, 1], dtype=np.int32)
        f.attrs["MaxLevel"] = np.int32(0)
        f.attrs["NumVariables"] = np.array([len(NAMES)], dtype=np.int32)
        f.attrs["DatasetNames"] = np.array([b"prim"])
        f.attrs["VariableNames"] = np.array([n.encode() for n in NAMES])
        f.create_dataset("Levels", data=np.zeros(nb, dtype=np.int32))
        f.create_dataset("LogicalLocations", data=np.array([(i, j, 0) for i, j in LOCATIONS], dtype=np.int64))
        f.create_dataset("x1f", data=np.array([(i * B + np.arange(B + 1)) * dx for i, _ in LOCATIONS]))
        f.create_dataset("x2f", data=np.array([(j * B + np.arange(B + 1)) * dx for _, j in LOCATIONS]))
        f.create_dataset("x3f", data=np.tile([-0.5 * dx, 0.5 * dx], (nb, 1)))
        f.create_dataset("x1v", data=np.array([(i * B + np.arange(B) + 0.5) * dx for i, _ in LOCATIONS]))
        f.create_dataset("x2v", data=np.array([(j * B + np.arange(B) + 0.5) * dx for _, j in LOCATIONS]))
        f.create_dataset("x3v", data=np.zeros((nb, 1)))
        ## [block, var, k, j, i] in memory -> [var, block, k, j, i] in the file, interior cells only.
        f.create_dataset("prim", data=np.ascontiguousarray(pack[:, :, :, G:-G, G:-G].transpose(1, 0, 2, 3, 4)))
        ## What Athena++ does not record: mhdpy's own description of the simulation (illustrative content).
        meta = f.create_group("mhdpy")
        meta.attrs["format_version"] = 1
        meta.attrs["registry"] = json.dumps({n: {"centring": "cell", "role": "primitive"} for n in NAMES})
        meta.attrs["units"] = json.dumps({"length_cm": 3.0857e21, "mass_g": 1.989e38, "time_s": 3.156e13})
        meta.create_dataset("morton_order", data=np.arange(nb))


def read_blocks(path: Path) -> np.ndarray:
    """The few lines a reader needs: assemble [var, y, x] from the blocks' logical locations."""
    with h5py.File(path, "r") as f:
        data, locations = f["prim"][...], f["LogicalLocations"][...]
        bx, by, _ = f.attrs["MeshBlockSize"]
        nx, ny, _ = f.attrs["RootGridSize"]
    out = np.empty((data.shape[0], ny, nx))
    for b, (i, j, _) in enumerate(locations):
        out[:, j * by : (j + 1) * by, i * bx : (i + 1) * bx] = data[:, b, 0]
    return out


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    yt.set_log_level(40)
    state = global_state()
    results = {"python": sys.version, "numpy": np.__version__, "h5py": h5py.__version__, "yt": yt.__version__,
               "platform": platform.platform()}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cloud.out1.00010.athdf"
        write_athdf(path, to_blocks(state), time=0.25, cycle=10)
        ds = yt.load(str(path))
        results["yt_fields"] = sorted(f"{a}/{b}" for a, b in ds.field_list)
        results["yt_derived_examples"] = sorted(f"{a}/{b}" for a, b in ds.derived_field_list
                                                if b in ("density", "pressure", "velocity_x", "velocity_magnitude"))
        results["yt_time"] = float(ds.current_time.d)
        grid = ds.covering_grid(level=0, left_edge=ds.domain_left_edge, dims=ds.domain_dimensions)
        checks = {}
        for v, name in enumerate(NAMES):
            from_yt = np.asarray(grid["athena_pp", name].d)[:, :, 0].T
            checks[f"yt: {name}"] = bool(np.array_equal(from_yt, state[v]))
        checks["yt: gas/density = rho"] = bool(np.array_equal(np.asarray(grid["gas", "density"].d)[:, :, 0].T, state[0]))
        checks["minimal reader: all variables"] = bool(np.array_equal(read_blocks(path), state))
        results["checks"] = checks
    print(json.dumps(results, indent=1))
    md = ["# E14.3: reading mhdpy's blocks with yt through Athena++'s layout", "",
          f"400 x 100 cells in 16 blocks of 50², Morton order, 6 primitive variables plus a group of mhdpy metadata; "
          f"Python {platform.python_version()}, NumPy {np.__version__}, h5py {h5py.__version__}, yt {yt.__version__}.", "",
          f"Fields recognised by yt: {', '.join(results['yt_fields'])}.", "",
          f"Examples of derived fields yt provides from them: {', '.join(results['yt_derived_examples'])}.", "",
          "| Check | Bit-for-bit identical to the original |", "|---|---|"]
    md += [f"| {name} | {'yes' if ok else 'no'} |" for name, ok in results["checks"].items()]
    (RESULTS / "E14.3-yt-compatibility.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E14.3-yt-compatibility.md").write_text("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

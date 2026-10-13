# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "h5py", "hdf5plugin", "zarr"]
# ///
"""Experiment E14.1: how long does writing a snapshot of the thesis grid take, and how large is it?

A snapshot of the thesis grid (4000 x 1000 cells, D07) holds the primitive variables of a 2D hydrodynamic run with a
passive scalar for the metallicity: density, three velocity components (the third is zero in 2D but stored, D06.3),
pressure and metallicity. In memory they are blocks of 50^2 cells with two ghost cells, in Morton order, as one array
[block, var, k, j, i] (D06, D07). A snapshot writes the interior cells only.

The experiment writes that state in several forms and measures, for each:

- the time to write it (including the copy that drops the ghost cells and any reordering), until the file is closed,
  and until it is also flushed to the disk (``fsync``, ``F_FULLFSYNC`` on macOS);
- the time to read it back (with the file in the operating system's cache);
- the file size, and whether the data read back are bit-for-bit identical.

The forms are NumPy's own format; HDF5 (h5py) contiguous in the block layout of memory ([block, var, ...]) and in
Athena++'s layout ([var, block, ...]); HDF5 chunked, without compression and with the gzip, lzf and zstd (Blosc,
hdf5plugin) filters; zarr with its default zstd compression; and single precision, uncompressed and with zstd.

Compression depends on the data, so two synthetic states are used:

- **cloud in a halo:** a dense, turbulent cloud with a tail in a uniform hot medium, the situation of the thesis run;
  the medium far from the cloud is exactly uniform, as the inflowing halo is in the run;
- **turbulent everywhere:** every cell perturbed, as a worst case.

Perturbations are random fields with a power-law spectrum (fixed seed). Repetitions are interleaved; the best of three
is kept. Run from this directory with:

    uv run --locked --script E14.1-snapshot-formats.py

The files are written to a temporary directory on the internal SSD. Results are written to results/.
"""

import fcntl
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

import h5py
import hdf5plugin
import numpy as np
import zarr

HERE = Path(__file__).parent
RESULTS = HERE / "results"
NX, NY, B, G = 4000, 1000, 50, 2
NAMES = ["rho", "vel1", "vel2", "vel3", "press", "metallicity"]
REPEATS = 3
CHUNK_BLOCKS = 16
STEP_SECONDS = 0.12  # a step of the thesis grid on 6-12 workers (E09.1)


def morton(cx: int, cy: int) -> int:
    code = 0
    for bit in range(16):
        code |= ((cx >> bit) & 1) << (2 * bit) | ((cy >> bit) & 1) << (2 * bit + 1)
    return code


LOCATIONS = sorted(((ci, cj) for cj in range(NY // B) for ci in range(NX // B)), key=lambda c: morton(*c))


def random_field(rng: np.random.Generator, slope: float = -11 / 3) -> np.ndarray:
    """A random field on the grid with power spectrum k^slope (in 2D), zero mean and unit standard deviation."""
    kx, ky = np.fft.rfftfreq(NX), np.fft.fftfreq(NY)
    k = np.hypot(*np.meshgrid(kx, ky, indexing="xy"))
    k[0, 0] = np.inf
    amplitude = k ** ((slope - 1) / 2)
    phases = np.exp(2j * np.pi * rng.random(amplitude.shape))
    field = np.fft.irfft2(amplitude * phases, s=(NY, NX))
    return (field - field.mean()) / field.std()


def state(case: str) -> np.ndarray:
    """The primitive variables [var, y, x] of the synthetic state."""
    rng = np.random.default_rng(14)
    x = (np.arange(NX) + 0.5) / NY
    y = (np.arange(NY) + 0.5) / NY
    yy, xx = np.meshgrid(y, x, indexing="ij")
    noise = [random_field(rng) for _ in NAMES]
    if case == "turbulent everywhere":
        mask = np.ones((NY, NX))
    else:
        ## A cloud at x = 0.6 with a tail behind it (towards larger x), cut off where it is negligible.
        width = 0.05 + 0.04 * np.clip(xx - 0.6, 0, None)
        mask = np.exp(-((yy - 0.5) / width) ** 2 - (np.clip(0.6 - xx, 0, None) / 0.08) ** 2)
        mask *= np.exp(-np.clip(xx - 0.6, 0, None) / 1.2)
        mask[mask < 1e-2] = 0.0
    rho = 1.0 + mask * 99.0 * np.exp(0.5 * noise[0])
    vel1 = -1.0 + mask * (1.0 + 0.3 * noise[1])
    vel2 = mask * 0.3 * noise[2]
    vel3 = np.zeros((NY, NX))
    press = 1.0 + mask * 0.1 * noise[4]
    metallicity = 0.1 + mask * (0.9 + 0.05 * noise[5])
    return np.array([rho, vel1, vel2, vel3, press, metallicity])


def pack(prim: np.ndarray) -> np.ndarray:
    """The state as blocks with ghost cells, [block, var, k, j, i], in Morton order (ghost cells left zero)."""
    out = np.zeros((len(LOCATIONS), len(NAMES), 1, B + 2 * G, B + 2 * G))
    for b, (ci, cj) in enumerate(LOCATIONS):
        out[b, :, 0, G:-G, G:-G] = prim[:, cj * B : (cj + 1) * B, ci * B : (ci + 1) * B]
    return out


def interior(p: np.ndarray, dtype=np.float64) -> np.ndarray:
    return np.ascontiguousarray(p[:, :, :, G:-G, G:-G], dtype=dtype)


def fsync(path: Path) -> None:
    """Flush the file(s) to the disk; on macOS fsync only reaches the drive's cache, F_FULLFSYNC the disk itself."""
    paths = [path] if path.is_file() else [q for q in path.rglob("*") if q.is_file()]
    for q in paths:
        fd = os.open(q, os.O_RDONLY)
        try:
            if sys.platform == "darwin":
                fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
            else:
                os.fsync(fd)
        finally:
            os.close(fd)


def write_npy(p, path):
    np.save(path, interior(p))


def read_npy(path):
    return np.load(path)


def hdf5_writer(layout: str = "block", dtype=np.float64, **dataset_options):
    def write(p, path):
        data = interior(p, dtype)
        if layout == "athena":
            data = np.ascontiguousarray(data.transpose(1, 0, 2, 3, 4))
        with h5py.File(path, "w") as f:
            f.attrs["Time"] = 1.0
            f.create_dataset("LogicalLocations", data=np.array([(i, j, 0) for i, j in LOCATIONS], dtype=np.int64))
            if "chunks" in dataset_options:
                dataset_options["chunks"] = (CHUNK_BLOCKS, *data.shape[1:])
            f.create_dataset("prim", data=data, **dataset_options)

    return write


def read_hdf5(path):
    with h5py.File(path, "r") as f:
        return f["prim"][...]


def write_zarr(p, path):
    data = interior(p)
    array = zarr.create_array(store=str(path), shape=data.shape, dtype=data.dtype,
                              chunks=(CHUNK_BLOCKS, *data.shape[1:]))
    array[...] = data


def read_zarr(path):
    return zarr.open_array(str(path), mode="r")[...]


FORMS = {
    "NumPy .npy": (write_npy, read_npy, ".npy"),
    "HDF5, contiguous, block layout": (hdf5_writer(), read_hdf5, ".h5"),
    "HDF5, contiguous, Athena++ layout": (hdf5_writer("athena"), read_hdf5, ".h5"),
    "HDF5, chunked": (hdf5_writer(chunks=True), read_hdf5, ".h5"),
    "HDF5, chunked, gzip 1 + shuffle": (hdf5_writer(chunks=True, compression="gzip", compression_opts=1, shuffle=True),
                                        read_hdf5, ".h5"),
    "HDF5, chunked, lzf + shuffle": (hdf5_writer(chunks=True, compression="lzf", shuffle=True), read_hdf5, ".h5"),
    "HDF5, chunked, zstd 1 + shuffle (Blosc)": (
        hdf5_writer(chunks=True, **hdf5plugin.Blosc(cname="zstd", clevel=1, shuffle=hdf5plugin.Blosc.SHUFFLE)),
        read_hdf5, ".h5"),
    "zarr, default (zstd)": (write_zarr, read_zarr, ".zarr"),
    "HDF5, contiguous, single precision": (hdf5_writer(dtype=np.float32), read_hdf5, ".h5"),
    "HDF5, chunked, single precision, zstd 1 + shuffle (Blosc)": (
        hdf5_writer(dtype=np.float32, chunks=True,
                    **hdf5plugin.Blosc(cname="zstd", clevel=1, shuffle=hdf5plugin.Blosc.SHUFFLE)),
        read_hdf5, ".h5"),
}


def size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else sum(q.stat().st_size for q in path.rglob("*") if q.is_file())


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    results = {"python": sys.version, "numpy": np.__version__, "h5py": h5py.__version__,
               "hdf5": h5py.version.hdf5_version, "zarr": zarr.__version__, "hdf5plugin": hdf5plugin.version,
               "platform": platform.platform(), "cases": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for case in ["cloud in a halo", "turbulent everywhere"]:
            prim = state(case)
            perturbed = float(np.mean(np.any(prim != prim[:, :1, :1], axis=0)))
            p = pack(prim)
            reference = interior(p)
            raw = reference.nbytes
            best = {form: {"write": np.inf, "write_and_fsync": np.inf, "read": np.inf} for form in FORMS}
            rows = {}
            for repeat in range(REPEATS):
                for form, (write, read, suffix) in FORMS.items():
                    path = Path(tmp) / f"snapshot{suffix}"
                    remove(path)
                    start = time.perf_counter()
                    write(p, path)
                    written = time.perf_counter()
                    fsync(path)
                    synced = time.perf_counter()
                    data = read(path)
                    done = time.perf_counter()
                    best[form]["write"] = min(best[form]["write"], written - start)
                    best[form]["write_and_fsync"] = min(best[form]["write_and_fsync"], synced - start)
                    best[form]["read"] = min(best[form]["read"], done - synced)
                    if repeat == 0:
                        if "Athena" in form:
                            data = data.transpose(1, 0, 2, 3, 4)
                        error = float(np.max(np.abs(data.astype(np.float64) - reference) / np.abs(reference).clip(1e-300)
                                             * (reference != 0)))
                        rows[form] = {"bytes": size(path), "bitwise_identical": bool(np.array_equal(data, reference)),
                                      "max_relative_error": error}
                    remove(path)
            for form in FORMS:
                rows[form].update(best[form])
                rows[form]["raw_bytes"] = raw
                print(case, form, rows[form], flush=True)
            results["cases"][case] = {"perturbed_fraction": perturbed, "forms": rows}

    md = [
        "# E14.1: writing a snapshot of the thesis grid",
        "",
        f"4000 x 1000 cells in blocks of 50², {len(NAMES)} primitive variables, interior cells only "
        f"({results['cases']['cloud in a halo']['forms']['NumPy .npy']['raw_bytes'] / 1e6:.0f} MB in double precision). "
        f"Python {platform.python_version()}, NumPy {np.__version__}, h5py {h5py.__version__} (HDF5 "
        f"{h5py.version.hdf5_version}), zarr {zarr.__version__}, hdf5plugin {hdf5plugin.version}; {platform.platform()}, "
        "internal SSD. Best of three; reading with the file in the operating system's cache. Steps: the write with fsync "
        f"in units of a thesis step ({1e3 * STEP_SECONDS:.0f} ms).",
        "",
    ]
    for case, entry in results["cases"].items():
        rows = entry["forms"]
        md += [f"## {case} ({100 * entry['perturbed_fraction']:.0f} % of the cells perturbed)", "",
               "| Form | Write | Write + fsync | Steps | Read | Size | Ratio | Exact |",
               "|---|---|---|---|---|---|---|---|"]
        for form, row in rows.items():
            exact = "yes" if row["bitwise_identical"] else f"no ({row['max_relative_error']:.1e})"
            md.append(f"| {form} | {row['write']:.2f} s | {row['write_and_fsync']:.2f} s | "
                      f"{row['write_and_fsync'] / STEP_SECONDS:.1f} | {row['read']:.2f} s | {row['bytes'] / 1e6:.0f} MB | "
                      f"{row['raw_bytes'] / row['bytes']:.2f} | {exact} |")
        md.append("")
    (RESULTS / "E14.1-snapshot-formats.json").write_text(json.dumps(results, indent=1) + "\n")
    (RESULTS / "E14.1-snapshot-formats.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()

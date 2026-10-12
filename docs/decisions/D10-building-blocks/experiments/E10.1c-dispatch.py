# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "cython"]
# ///
"""Experiment E10.1: what does it cost to select the Riemann solver and the limiter at run time?

A simulation chooses its components (Riemann solver, limiter, later the equation of state) when it is set up, not when
mhdpy is compiled, unlike Athena++, which links exactly one of each. The kernel then has to reach the chosen component
somehow. This experiment times the time-derivative kernel of D09 (``rhs_block`` in ``E10.1a-kernels.py``) in three
forms, generated from its source:

- **direct:** the kernel calls ``hll`` and ``mc_slope`` directly; the C compiler can inline them (a fixed choice, as a
  kernel specialised for one combination would be);
- **switch:** every call goes through a small inline function that branches on an integer chosen at run time between
  ``hll`` and ``hll_alt`` (and ``mc_slope`` and ``mc_alt``); the branch goes the same way for the whole call, so the
  processor predicts it;
- **function pointer:** the kernel picks the two functions once, at its start, and calls them through C function
  pointers (types from ``E10.1b-kernels.pxd``); calls through a pointer cannot be inlined;
- **switch, fixed per wrapper:** the switch form declared inline and called from a thin wrapper with the selection as
  literal constants, one wrapper per combination. If the compiler inlines it and folds the constants, the branches
  disappear and the wrapper is as fast as the direct form, without a second copy of the kernel's source;
- **fused types:** Cython's compile-time specialisation (its counterpart of C++ templates). The selection is an argument
  whose *type* is a fused type with one member per choice; Cython compiles one copy of the kernel per combination, in
  which ``if T is <member>`` is resolved at compile time. Uncompiled, a fused type cannot be told apart this way, so the
  test is written ``(T is cython.char) if cython.compiled else (tag == 0)``, and the tags carry distinct values as well:
  the uncompiled module then takes the same branch, as D04.3 requires.

The alternatives are exact copies, so all forms must give the same result bit for bit (checked). For the fused form,
the uncompiled module is also run on a small block with the alternatives replaced by recording stubs, to check that it
takes the branch the tags select (D04.3). Each form is
timed natively (Clang) and in a Linux container (GCC, ``E10.1d-Dockerfile``), on one thread, for 2D blocks of 64^2 and
512^2 and 3D blocks of 32^3. Run from this directory with (Docker running, the machine otherwise idle):

    uv run --no-project --python 3.14 E10.1c-dispatch.py

Results are written to results/.
"""

import importlib.util
import json
import platform
import subprocess
import sys
import sysconfig
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent.resolve()
RESULTS = HERE / "results"
IMAGE = "mhdpy-e10"
G = 2
GAMMA = 1.4
NVAR = 5
MIN_TIME = 0.3
REPEATS = 9  ## interleaved: every repetition times every form once, so drift affects all forms alike
SIZES = {"2D, 64²": (64, 64, 1), "2D, 512²": (512, 512, 1), "3D, 32³": (32, 32, 32)}
FORMS = ["direct", "switch", "function pointer", "switch, fixed per wrapper", "fused types"]

HELPERS = '''


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
def limit_switch(sel: cython.int, left: cython.double, right: cython.double) -> cython.double:
    if sel == 0:
        return mc_slope(left, right)
    return mc_alt(left, right)


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
def riemann_switch(
    sel: cython.int,
    rl: cython.double, nl: cython.double, al: cython.double, bl: cython.double, pl: cython.double,
    rr: cython.double, nr: cython.double, ar: cython.double, br: cython.double, pr: cython.double,
    out: cython.double[:, :, :, ::1], k: cython.Py_ssize_t, j: cython.Py_ssize_t, i: cython.Py_ssize_t,
    n: cython.Py_ssize_t, a: cython.Py_ssize_t, b: cython.Py_ssize_t,
) -> cython.void:
    if sel == 0:
        hll(rl, nl, al, bl, pl, rr, nr, ar, br, pr, out, k, j, i, n, a, b)
    else:
        hll_alt(rl, nl, al, bl, pl, rr, nr, ar, br, pr, out, k, j, i, n, a, b)
'''

WRAPPER = '''


@cython.boundscheck(False)
@cython.wraparound(False)
def {name}_call(
    u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t, g: cython.Py_ssize_t, dx: cython.double,
    riemann: cython.int, limiter: cython.int,
) -> None:
    with cython.nogil:
        {name}(u, w, fx, fy, fz, du, nx, ny, nz, g, dx, riemann, limiter)
'''


FIXED = '''


@cython.boundscheck(False)
@cython.wraparound(False)
def rhs_fixed_call(
    u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t, g: cython.Py_ssize_t, dx: cython.double,
) -> None:
    with cython.nogil:
        rhs_switch(u, w, fx, fy, fz, du, nx, ny, nz, g, dx, 0, 0)
'''


FUSED = '''


RSel = cython.fused_type(cython.char, cython.short)
LSel = cython.fused_type(cython.char, cython.short)


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
def limit_fused(tag: LSel, left: cython.double, right: cython.double) -> cython.double:
    if (LSel is cython.char) if cython.compiled else (tag == 0):
        return mc_slope(left, right)
    return mc_alt(left, right)


@cython.cfunc
@cython.inline
@cython.nogil
@cython.exceptval(check=False)
def riemann_fused(
    tag: RSel,
    rl: cython.double, nl: cython.double, al: cython.double, bl: cython.double, pl: cython.double,
    rr: cython.double, nr: cython.double, ar: cython.double, br: cython.double, pr: cython.double,
    out: cython.double[:, :, :, ::1], k: cython.Py_ssize_t, j: cython.Py_ssize_t, i: cython.Py_ssize_t,
    n: cython.Py_ssize_t, a: cython.Py_ssize_t, b: cython.Py_ssize_t,
) -> cython.void:
    if (RSel is cython.char) if cython.compiled else (tag == 0):
        hll(rl, nl, al, bl, pl, rr, nr, ar, br, pr, out, k, j, i, n, a, b)
    else:
        hll_alt(rl, nl, al, bl, pl, rr, nr, ar, br, pr, out, k, j, i, n, a, b)
'''

FUSED_CALL = '''


@cython.boundscheck(False)
@cython.wraparound(False)
def rhs_fused_call(
    u: cython.double[:, :, :, ::1], w: cython.double[:, :, :, ::1], fx: cython.double[:, :, :, ::1],
    fy: cython.double[:, :, :, ::1], fz: cython.double[:, :, :, ::1], du: cython.double[:, :, :, ::1],
    nx: cython.Py_ssize_t, ny: cython.Py_ssize_t, nz: cython.Py_ssize_t, g: cython.Py_ssize_t, dx: cython.double,
) -> None:
    with cython.nogil:
        rhs_fused(u, w, fx, fy, fz, du, nx, ny, nz, g, dx, cython.cast(cython.char, 0), cython.cast(cython.char, 0))
'''


def variants_source() -> str:
    """The kernel module plus the switch and function-pointer forms of rhs_block, generated from its source."""
    source = (HERE / "E10.1a-kernels.py").read_text()
    start = source.index("def rhs_block(")
    start = source.rfind("\n\n\n", 0, start) + 3
    end = source.index("\n\n\n", source.index("def rhs_block("))
    original = source[start:end]
    signature = "    dx: cython.double,\n) -> cython.void:"
    assert signature in original
    extended = original.replace(signature, "    dx: cython.double,\n    riemann: cython.int,\n    limiter: cython.int,\n"
                                           ") -> cython.void:")
    switch = (extended.replace("def rhs_block(", "def rhs_switch(")
              .replace("mc_slope(", "limit_switch(limiter, ").replace("hll(", "riemann_switch(riemann, "))
    docstring_end = extended.index('"""', extended.index('"""') + 3) + 3
    pointer = (extended[:docstring_end]
               + "\n    lim: limiter_t = mc_slope if limiter == 0 else mc_alt"
               + "\n    rs: riemann_t = hll if riemann == 0 else hll_alt"
               + extended[docstring_end:])
    pointer = pointer.replace("def rhs_block(", "def rhs_pointer(").replace("mc_slope(", "lim(").replace("hll(", "rs(")
    switch = switch.replace("@cython.cfunc\n", "@cython.cfunc\n@cython.inline\n", 1)
    fused = (original.replace(signature, "    dx: cython.double,\n    rtag: RSel,\n    ltag: LSel,\n) -> cython.void:")
             .replace("def rhs_block(", "def rhs_fused(")
             .replace("mc_slope(", "limit_fused(ltag, ").replace("hll(", "riemann_fused(rtag, "))
    wrappers = WRAPPER.format(name="rhs_switch") + WRAPPER.format(name="rhs_pointer") + FIXED + FUSED_CALL
    return source.rstrip() + HELPERS + FUSED + "\n\n" + switch + "\n\n\n" + pointer + "\n\n\n" + fused + wrappers


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(workdir: Path):
    (workdir / "dispatch.py").write_text(variants_source())
    (workdir / "dispatch.pxd").write_text((HERE / "E10.1b-kernels.pxd").read_text())
    subprocess.run([sys.executable, "-m", "cython", "-3", "dispatch.py", "-o", "dispatch.c"], cwd=workdir, check=True)
    shared = ["-shared", "-fPIC"] + (["-undefined", "dynamic_lookup"] if sys.platform == "darwin" else [])
    ext = workdir / f"dispatch{sysconfig.get_config_var('EXT_SUFFIX')}"
    subprocess.run(["cc", "-O3", *shared, f"-I{sysconfig.get_paths()['include']}", "dispatch.c", "-o", str(ext)],
                   cwd=workdir, check=True)
    compiler = subprocess.run(["cc", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    return load("dispatch", ext), compiler


def state(nx: int, ny: int, nz: int):
    import numpy as np

    axes = [(np.arange(n) + 0.5) / n for n in (nz, ny, nx)]
    zz, yy, xx = np.meshgrid(*axes, indexing="ij")
    s = 2 * np.pi
    rho = 1.0 + 0.2 * np.sin(s * xx) * np.cos(s * yy) * np.cos(s * zz)
    vx, vy, vz = 0.5 + 0.1 * np.sin(s * yy), 0.3 * np.cos(s * xx), 0.2 * np.sin(s * (xx + yy))
    pres = 1.0 + 0.1 * np.cos(s * (xx + yy + zz))
    u = np.array([rho, rho * vx, rho * vy, rho * vz, pres / (GAMMA - 1.0) + 0.5 * rho * (vx * vx + vy * vy + vz * vz)])
    pad = [(0, 0)] + [(G, G) if n > 1 else (0, 0) for n in (nz, ny, nx)]
    return np.ascontiguousarray(np.pad(u, pad, mode="wrap"))


def mean_time(function) -> float:
    """Mean duration of ``function()`` over calls lasting at least MIN_TIME in total."""
    calls, start = 0, time.perf_counter()
    while True:
        function()
        calls += 1
        elapsed = time.perf_counter() - start
        if elapsed >= MIN_TIME:
            return elapsed / calls


def uncompiled_branches() -> dict:
    """Run the fused form uncompiled, with recording stubs for the alternatives, for both selections."""
    import numpy as np

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dispatch_uncompiled.py"
        path.write_text(variants_source())
        module = load("dispatch_uncompiled", path)
    calls = {"hll_alt": 0, "mc_alt": 0}
    original_hll, original_mc = module.hll_alt, module.mc_alt

    def hll_stub(*args):
        calls["hll_alt"] += 1
        return original_hll(*args)

    def mc_stub(*args):
        calls["mc_alt"] += 1
        return original_mc(*args)

    module.hll_alt, module.mc_alt = hll_stub, mc_stub
    nx = ny = 8
    u = state(nx, ny, 1)
    w = np.empty_like(u)
    fx, fy, fz = np.empty((NVAR, 1, ny, nx + 1)), np.empty((NVAR, 1, ny + 1, nx)), np.empty((NVAR, 2, ny, nx))
    du = np.empty((NVAR, 1, ny, nx))
    result = {}
    for tag in (0, 1):
        calls.update(hll_alt=0, mc_alt=0)
        module.rhs_fused(u, w, fx, fy, fz, du, nx, ny, 1, G, 1.0 / nx, tag, tag)
        result[f"tags {tag}"] = dict(calls)
    result["correct"] = (result["tags 0"] == {"hll_alt": 0, "mc_alt": 0}
                         and result["tags 1"]["hll_alt"] > 0 and result["tags 1"]["mc_alt"] > 0)
    return result


def run(label: str, output: Path) -> None:
    import numpy as np

    results = {"label": label, "python": sys.version, "platform": platform.platform(), "cases": {}}
    results["uncompiled_fused_branches"] = uncompiled_branches()
    with tempfile.TemporaryDirectory() as tmp:
        module, compiler = build(Path(tmp))
        results["compiler"] = compiler
        for name, (nx, ny, nz) in SIZES.items():
            u = state(nx, ny, nz)
            w = np.empty_like(u)
            fx, fy, fz = (np.empty((NVAR, nz, ny, nx + 1)), np.empty((NVAR, nz, ny + 1, nx)),
                          np.empty((NVAR, nz + 1, ny, nx)))
            du = np.empty((NVAR, nz, ny, nx))
            dx = 1.0 / nx
            calls = {
                "direct": lambda: module.rhs(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
                "switch": lambda: module.rhs_switch_call(u, w, fx, fy, fz, du, nx, ny, nz, G, dx, 0, 0),
                "function pointer": lambda: module.rhs_pointer_call(u, w, fx, fy, fz, du, nx, ny, nz, G, dx, 0, 0),
                "switch, fixed per wrapper": lambda: module.rhs_fixed_call(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
                "fused types": lambda: module.rhs_fused_call(u, w, fx, fy, fz, du, nx, ny, nz, G, dx),
            }
            calls["direct"]()
            expected = du.copy()
            case = results["cases"][name] = {}
            for form, call in calls.items():
                du[:] = np.nan
                call()
                case[form] = {"bitwise_identical": bool(np.array_equal(du, expected))}
            best = dict.fromkeys(calls, float("inf"))
            for _ in range(REPEATS):
                for form, call in calls.items():
                    best[form] = min(best[form], mean_time(call))
            for form in calls:
                case[form]["cells_per_second"] = nx * ny * nz / best[form]
            print(label, name, case, flush=True)
    output.write_text(json.dumps(results, indent=1) + "\n")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
        return
    RESULTS.mkdir(exist_ok=True)
    script = ["uv", "run", "--locked", "--script"]
    subprocess.run([*script, str(HERE / "E10.1c-dispatch.py"), "run", "macos-native",
                    str(RESULTS / "E10.1c-macos-native.json")], check=True)
    subprocess.run(["docker", "build", "--quiet", "-t", IMAGE, "-f", str(HERE / "E10.1d-Dockerfile"), str(HERE)],
                   check=True)
    subprocess.run(["docker", "run", "--rm", "--platform", "linux/amd64", "-v", f"{HERE}:/work:ro",
                    "-v", f"{RESULTS}:/out", "-v", "mhdpy-e10-uv-cache:/root/.cache/uv", "-w", "/work", IMAGE,
                    *script, "E10.1c-dispatch.py", "run", "linux-container", "/out/E10.1c-linux-container.json"],
                   check=True)
    md = ["# E10.1: selecting components at run time", "",
          "One evaluation of the time derivative on one block, one thread. Million cells per second, and relative to "
          "the direct form; ✓ = bit-for-bit identical to the direct form.", ""]
    for label in ("macos-native", "linux-container"):
        r = json.loads((RESULTS / f"E10.1c-{label}.json").read_text())
        branches = r["uncompiled_fused_branches"]
        md += [f"## {label} ({r['compiler']})", "",
               f"Uncompiled fused form takes the selected branch: {branches['correct']} (calls of the alternatives "
               f"with tags 0: {branches['tags 0']}, with tags 1: {branches['tags 1']}).", "",
               "| Block | " + " | ".join(FORMS) + " |", "|" + "---|" * 6]
        for name, case in r["cases"].items():
            base = case["direct"]["cells_per_second"]
            md.append(f"| {name} | " + " | ".join(
                f"{case[f]['cells_per_second'] / 1e6:.1f} ({case[f]['cells_per_second'] / base:.2f}) "
                f"{'✓' if case[f]['bitwise_identical'] else '✗'}" for f in FORMS) + " |")
        md.append("")
    (RESULTS / "E10.1c-dispatch.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()

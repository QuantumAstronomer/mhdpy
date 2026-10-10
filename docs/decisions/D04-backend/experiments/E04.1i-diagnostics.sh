#!/bin/sh
# Experiment E04.1 (diagnostics): checks of two observations in the benchmark, run in the E04.1 container.
#
# 1. Compiled kernels ran about 1.5x slower in the Linux container than natively on macOS. Does the compiler explain it?
#    The C kernel is built with GCC with and without -fno-math-errno (which lets sqrt vectorise) and with Clang.
# 2. Does JAX's lead come from extra threads? It is timed with XLA's default threading and forced onto one thread.
#
# Run from this directory, after E04.1h-run.py has built the image (Docker must be running):
#
#     sh E04.1i-diagnostics.sh
#
# Output is written to results/E04.1i-diagnostics.txt.
set -e
cd "$(dirname "$0")"
docker run --rm --platform linux/amd64 -v "$PWD:/work:ro" -v mhdpy-e041-uv-cache:/root/.cache/uv mhdpy-e041 sh -c '
set -e
apt-get update -qq >/dev/null && apt-get install -y -qq --no-install-recommends clang libomp-dev >/dev/null 2>&1
cat > /tmp/time_c.py <<EOF
import ctypes, importlib.util, sys, time
import numpy as np
s = importlib.util.spec_from_file_location("r", "/work/E04.1a-hydro2d-numpy.py")
r = importlib.util.module_from_spec(s); s.loader.exec_module(r)
lib = ctypes.CDLL(sys.argv[1]); lib.set_threads(1)
n = 1024; m = n + 4; u = r.initial_state(n)
w, fx, fy, du = np.empty((4, m, m)), np.empty((4, n + 1, n)), np.empty((4, n, n + 1)), np.empty((4, n, n))
P = ctypes.POINTER(ctypes.c_double)
lib.rhs.argtypes = [P] * 5 + [ctypes.c_int, ctypes.c_int, ctypes.c_double]
def kernel(u, dx):
    lib.rhs(*[a.ctypes.data_as(P) for a in (u, w, fx, fy, du)], m, 2, dx)
    return du
r.ssp_rk2_step(u, 1e-4, 1 / n, kernel)
t = time.perf_counter()
for _ in range(5):
    r.ssp_rk2_step(u, 1e-4, 1 / n, kernel)
print(f"{sys.argv[2]:45s} {5 * n * n / (time.perf_counter() - t):.2e} cell updates/s (1 thread, 1024^2)")
EOF
cat > /tmp/time_jax.py <<EOF
import importlib.util, os, time
s = importlib.util.spec_from_file_location("r", "/work/E04.1a-hydro2d-numpy.py")
r = importlib.util.module_from_spec(s); s.loader.exec_module(r)
s = importlib.util.spec_from_file_location("j", "/work/E04.1e-hydro2d-jax.py")
j = importlib.util.module_from_spec(s); s.loader.exec_module(j)
import jax.numpy as jnp
n = 1024; u = jnp.asarray(r.initial_state(n)); j.step(u, 1e-4, 1 / n).block_until_ready()
t = time.perf_counter()
for _ in range(5):
    j.step(u, 1e-4, 1 / n).block_until_ready()
label = "JAX, " + ("one thread" if os.environ.get("XLA_FLAGS") else "default threading")
print(f"{label:45s} {5 * n * n / (time.perf_counter() - t):.2e} cell updates/s (1024^2)")
EOF
cd /work
gcc --version | head -1; clang --version | head -1
for build in "gcc -O3" "gcc -O3 -fno-math-errno" "gcc -O3 -march=native -fno-math-errno" "clang -O3"; do
  $build -fopenmp -shared -fPIC E04.1c-hydro2d-c.c -o /tmp/kernel.so
  uv run -q --no-project --with numpy python /tmp/time_c.py /tmp/kernel.so "C, $build"
done
uv run -q --no-project --with numpy --with jax python /tmp/time_jax.py
XLA_FLAGS="--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1" \
  uv run -q --no-project --with numpy --with jax python /tmp/time_jax.py
' | tee results/E04.1i-diagnostics.txt

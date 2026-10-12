# Function-pointer types for the dispatch variants of experiment E10.1, declared for the pure-Python-mode module that
# ``E10.1c-dispatch.py`` builds from ``E10.1a-kernels.py`` (a .pxd file next to a .py module augments it with C types).
ctypedef double (*limiter_t)(double, double) noexcept nogil
ctypedef void (*riemann_t)(double, double, double, double, double, double, double, double, double, double,
                           double[:, :, :, ::1], Py_ssize_t, Py_ssize_t, Py_ssize_t, Py_ssize_t, Py_ssize_t,
                           Py_ssize_t) noexcept nogil

# The pointer to the solver and the signatures of pointer.py alone, as in B2E2.
ctypedef (double, double, double, double) (*solver_t)(double, double, double, double, double, double, double,
                                                      double, double) noexcept nogil
cdef solver_t SOLVER
cdef double limit(double dl, double dr) noexcept nogil
cdef (double, double) face(double wm2, double wm1, double w0, double wp1) noexcept nogil
cdef (double, double, double, double) hlle(double rl, double ul, double vl, double pl, double rr, double ur,
                                           double vr, double pr, double gamma) noexcept nogil
cpdef void choose(str name)
cpdef void stage(double[:, :, ::1] u, double[:, :, ::1] w, double[:, :, ::1] fx, double[:, :, ::1] fy,
                 double[:, :, ::1] du, double gamma, int nscal, double dtdx, double dtdy)

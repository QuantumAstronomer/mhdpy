# The constants of config.h, which the build writes, and the signatures of fixed.py alone, as in B2E2.
cdef extern from "config.h":
    const double GAMMA
    const int NSCALARS

cdef double limit(double dl, double dr) noexcept nogil
cdef (double, double) face(double wm2, double wm1, double w0, double wp1) noexcept nogil
cdef (double, double, double, double) hlle(double rl, double ul, double vl, double pl, double rr, double ur,
                                           double vr, double pr, double gamma) noexcept nogil
cpdef int nscalars()
cpdef void stage(double[:, :, ::1] u, double[:, :, ::1] w, double[:, :, ::1] fx, double[:, :, ::1] fy,
                 double[:, :, ::1] du, double dtdx, double dtdy)

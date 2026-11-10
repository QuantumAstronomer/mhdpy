# The C types of held.py, which Cython reads beside it in its pure mode, as for the loops of B2E1.
cimport cython

@cython.locals(prod=double)
cdef double limit(double dl, double dr) noexcept nogil

@cython.locals(left=double, right=double)
cdef (double, double) face(double wm2, double wm1, double w0, double wp1) noexcept nogil

@cython.locals(cl=double, cr=double, bm=double, bp=double, el=double, er=double, scale=double,
               fd=double, fn=double, ft=double, fe=double)
cdef (double, double, double, double) hlle(double rl, double ul, double vl, double pl, double rr, double ur,
                                           double vr, double pr, double gamma) noexcept nogil

@cython.locals(ny4=Py_ssize_t, nx4=Py_ssize_t, j=Py_ssize_t, i=Py_ssize_t, k=Py_ssize_t,
               rho=double, vx=double, vy=double, rl=double, rr=double, ul=double, ur=double,
               vl=double, vr=double, pl=double, pr=double, fd=double, fn=double, ft=double, fe=double)
cpdef void stage(double[:, :, ::1] u, double[:, :, ::1] w, double[:, :, ::1] fx, double[:, :, ::1] fy,
                 double[:, :, ::1] du, double gamma, double dtdx, double dtdy)

/* C kernel of experiment E04.1: the same arithmetic as E04.1a-hydro2d-numpy.py, as explicit loops.
 *
 * Stands in for every compiled extension written in C or C++ (whether bound with ctypes, nanobind or pybind11): the
 * binding layer does not change the speed of the kernel itself. Compiled ahead of time by the experiment, with OpenMP
 * where the compiler supports it, and called through ctypes with NumPy arrays. Arrays are C-contiguous [var][i][j].
 */
#include <math.h>
#include <stddef.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define GAMMA 1.4
#define IDX(k, i, j, ni, nj) (((size_t)(k) * (ni) + (i)) * (nj) + (j))

void set_threads(int n) {
#ifdef _OPENMP
    omp_set_num_threads(n);
#else
    (void)n;
#endif
}

static inline double mc_slope(double left, double right) {
    if (left * right > 0.0) {
        double limited = fmin(fmin(2.0 * fabs(left), 2.0 * fabs(right)), 0.5 * fabs(left + right));
        return left > 0.0 ? limited : -limited;
    }
    return 0.0;
}

/* HLL flux of normal-frame states; writes (f0, f_normal, f_tangential, f3) or, if swap, the two momenta exchanged. */
static inline void hll(double rl, double ul, double vl, double pl, double rr, double ur, double vr, double pr,
                       double *out, size_t stride, int swap) {
    double cl = sqrt(GAMMA * pl / rl), cr = sqrt(GAMMA * pr / rr);
    double sl = fmin(ul - cl, ur - cr), sr = fmax(ul + cl, ur + cr);
    double el = pl / (GAMMA - 1.0) + 0.5 * rl * (ul * ul + vl * vl);
    double er = pr / (GAMMA - 1.0) + 0.5 * rr * (ur * ur + vr * vr);
    double fl0 = rl * ul, fl1 = rl * ul * ul + pl, fl2 = rl * ul * vl, fl3 = (el + pl) * ul;
    double fr0 = rr * ur, fr1 = rr * ur * ur + pr, fr2 = rr * ur * vr, fr3 = (er + pr) * ur;
    double f0, f1, f2, f3;
    if (sl >= 0.0) {
        f0 = fl0; f1 = fl1; f2 = fl2; f3 = fl3;
    } else if (sr <= 0.0) {
        f0 = fr0; f1 = fr1; f2 = fr2; f3 = fr3;
    } else {
        f0 = (sr * fl0 - sl * fr0 + sl * sr * (rr - rl)) / (sr - sl);
        f1 = (sr * fl1 - sl * fr1 + sl * sr * (rr * ur - rl * ul)) / (sr - sl);
        f2 = (sr * fl2 - sl * fr2 + sl * sr * (rr * vr - rl * vl)) / (sr - sl);
        f3 = (sr * fl3 - sl * fr3 + sl * sr * (er - el)) / (sr - sl);
    }
    out[0] = f0;
    out[stride] = swap ? f2 : f1;
    out[2 * stride] = swap ? f1 : f2;
    out[3 * stride] = f3;
}

void rhs(const double *u, double *w, double *fx, double *fy, double *du, int m, int g, double dx) {
    int n = m - 2 * g;
    size_t sfx = (size_t)(n + 1) * n, sfy = (size_t)n * (n + 1);
#pragma omp parallel for schedule(static)
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < m; j++) {
            double rho = u[IDX(0, i, j, m, m)];
            double vx = u[IDX(1, i, j, m, m)] / rho, vy = u[IDX(2, i, j, m, m)] / rho;
            w[IDX(0, i, j, m, m)] = rho;
            w[IDX(1, i, j, m, m)] = vx;
            w[IDX(2, i, j, m, m)] = vy;
            w[IDX(3, i, j, m, m)] = (GAMMA - 1.0) * (u[IDX(3, i, j, m, m)] - 0.5 * rho * (vx * vx + vy * vy));
        }
    }
#define W(k, i, j) w[IDX(k, i, j, m, m)]
#define LEFT(k, i, j, di, dj) (W(k, i - di, j - dj) + 0.5 * mc_slope(W(k, i - di, j - dj) - W(k, i - 2 * di, j - 2 * dj), \
                                                                  W(k, i, j) - W(k, i - di, j - dj)))
#define RIGHT(k, i, j, di, dj) (W(k, i, j) - 0.5 * mc_slope(W(k, i, j) - W(k, i - di, j - dj), W(k, i + di, j + dj) - W(k, i, j)))
    /* Written out per variable, exactly as the Cython kernel, so that both give the C compiler the same code. */
#pragma omp parallel for schedule(static)
    for (int f = 0; f < n + 1; f++) {
        int i = g + f;
        for (int jj = 0; jj < n; jj++) {
            int j = g + jj;
            double rl = LEFT(0, i, j, 1, 0), ul = LEFT(1, i, j, 1, 0), vl = LEFT(2, i, j, 1, 0), pl = LEFT(3, i, j, 1, 0);
            double rr = RIGHT(0, i, j, 1, 0), ur = RIGHT(1, i, j, 1, 0), vr = RIGHT(2, i, j, 1, 0), pr = RIGHT(3, i, j, 1, 0);
            hll(rl, ul, vl, pl, rr, ur, vr, pr, &fx[IDX(0, f, jj, n + 1, n)], sfx, 0);
        }
    }
#pragma omp parallel for schedule(static)
    for (int ii = 0; ii < n; ii++) {
        int i = g + ii;
        for (int f = 0; f < n + 1; f++) {
            int j = g + f;
            /* normal velocity is w[2] in y: pass (rho, vy, vx, p) and swap the momenta back */
            double rl = LEFT(0, i, j, 0, 1), ul = LEFT(2, i, j, 0, 1), vl = LEFT(1, i, j, 0, 1), pl = LEFT(3, i, j, 0, 1);
            double rr = RIGHT(0, i, j, 0, 1), ur = RIGHT(2, i, j, 0, 1), vr = RIGHT(1, i, j, 0, 1), pr = RIGHT(3, i, j, 0, 1);
            hll(rl, ul, vl, pl, rr, ur, vr, pr, &fy[IDX(0, ii, f, n, n + 1)], sfy, 1);
        }
    }
#undef LEFT
#undef RIGHT
#undef W
#pragma omp parallel for schedule(static)
    for (int ii = 0; ii < n; ii++) {
        for (int jj = 0; jj < n; jj++) {
            for (int k = 0; k < 4; k++) {
                du[IDX(k, ii, jj, n, n)] = -(fx[IDX(k, ii + 1, jj, n + 1, n)] - fx[IDX(k, ii, jj, n + 1, n)]) / dx
                                           - (fy[IDX(k, ii, jj + 1, n, n + 1)] - fy[IDX(k, ii, jj, n, n + 1)]) / dx;
            }
        }
    }
}

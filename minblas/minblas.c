/*
 * minblas - a tiny drop-in replacement for the OpenBLAS library bundled with NumPy
 * Copyright (C) 2026 NomadBal
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * NumPy links to scipy-openblas (about 20 MB) and refuses to import without it, but EarBear never does linear algebra:
 * it no longer calls BLAS at all (the moving averages it used are computed with running sums). This library exports the same symbols:
 *
 * - the CBLAS functions used by numpy._core (dot, axpy, gemv, gemm, syrk) are implemented with plain loops,
 *   correct but without the speed of OpenBLAS for large matrices;
 * - the LAPACK and copy functions used only by numpy.linalg stop the program with a message if they are ever called.
 *
 * The file must keep the exact name of the DLL it replaces (see docs/BUILDING.md):
 *   x86_64-w64-mingw32-gcc -O2 -shared -s -static-libgcc -o <original name>.dll minblas.c
 */
#include <complex.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

typedef int64_t blasint;                       /* the "64_" symbols use 64-bit integers (ILP64) */
typedef float complex cf;
typedef double complex cd;

enum { RowMajor = 101, ColMajor = 102 };
enum { NoTrans = 111, Trans = 112, ConjTrans = 113 };
enum { Upper = 121, Lower = 122 };

/* With a negative increment BLAS walks the vector backwards, starting from its last element. */
static inline blasint first(blasint n, blasint inc) { return inc < 0 ? (1 - n) * inc : 0; }

#define ID(v) (v)
#define AT(M, ld, order, i, j) ((M)[(order) == ColMajor ? (i) + (j) * (ld) : (i) * (ld) + (j)])
#define VAL(T, a) (*(const T *)(a))

/* ---- level 1 ---- */

#define DOT(NAME, T)                                                                                     \
    EXPORT T NAME(blasint n, const T *x, blasint incx, const T *y, blasint incy)                         \
    {                                                                                                    \
        T s = 0;                                                                                         \
        x += first(n, incx), y += first(n, incy);                                                        \
        for (blasint i = 0; i < n; i++)                                                                  \
            s += x[i * incx] * y[i * incy];                                                              \
        return s;                                                                                        \
    }
DOT(scipy_cblas_sdot64_, float)
DOT(scipy_cblas_ddot64_, double)

#define DOTSUB(NAME, T, CJ)                                                                              \
    EXPORT void NAME(blasint n, const void *xv, blasint incx, const void *yv, blasint incy, void *ret)   \
    {                                                                                                    \
        const T *x = (const T *)xv + first(n, incx), *y = (const T *)yv + first(n, incy);                \
        T s = 0;                                                                                         \
        for (blasint i = 0; i < n; i++)                                                                  \
            s += CJ(x[i * incx]) * y[i * incy];                                                          \
        *(T *)ret = s;                                                                                   \
    }
DOTSUB(scipy_cblas_cdotu_sub64_, cf, ID)
DOTSUB(scipy_cblas_cdotc_sub64_, cf, conjf)
DOTSUB(scipy_cblas_zdotu_sub64_, cd, ID)
DOTSUB(scipy_cblas_zdotc_sub64_, cd, conj)

#define AXPY(NAME, T, AT_, A)                                                                            \
    EXPORT void NAME(blasint n, AT_ alpha, const void *xv, blasint incx, void *yv, blasint incy)         \
    {                                                                                                    \
        const T *x = (const T *)xv + first(n, incx);                                                     \
        T *y = (T *)yv + first(n, incy), a = A;                                                          \
        for (blasint i = 0; i < n; i++)                                                                  \
            y[i * incy] += a * x[i * incx];                                                              \
    }
AXPY(scipy_cblas_saxpy64_, float, float, alpha)
AXPY(scipy_cblas_daxpy64_, double, double, alpha)
AXPY(scipy_cblas_caxpy64_, cf, const void *, VAL(cf, alpha))
AXPY(scipy_cblas_zaxpy64_, cd, const void *, VAL(cd, alpha))

/* ---- level 2: y = alpha * op(A) * x + beta * y ---- */

#define GEMV(NAME, T, AT_, A, B, CJ)                                                                     \
    EXPORT void NAME(int order, int trans, blasint m, blasint n, AT_ alpha, const void *av, blasint lda, \
                     const void *xv, blasint incx, AT_ beta, void *yv, blasint incy)                     \
    {                                                                                                    \
        const T *a = (const T *)av, al = A, be = B;                                                      \
        blasint ly = trans == NoTrans ? m : n, lx = trans == NoTrans ? n : m;                            \
        const T *x = (const T *)xv + first(lx, incx);                                                    \
        T *y = (T *)yv + first(ly, incy);                                                                \
        for (blasint i = 0; i < ly; i++) {                                                               \
            T s = 0;                                                                                     \
            for (blasint k = 0; k < lx; k++) {                                                           \
                T e = trans == NoTrans ? AT(a, lda, order, i, k) : AT(a, lda, order, k, i);              \
                s += (trans == ConjTrans ? CJ(e) : e) * x[k * incx];                                     \
            }                                                                                            \
            y[i * incy] = be == 0 ? al * s : al * s + be * y[i * incy];                                  \
        }                                                                                                \
    }
GEMV(scipy_cblas_sgemv64_, float, float, alpha, beta, ID)
GEMV(scipy_cblas_dgemv64_, double, double, alpha, beta, ID)
GEMV(scipy_cblas_cgemv64_, cf, const void *, VAL(cf, alpha), VAL(cf, beta), conjf)
GEMV(scipy_cblas_zgemv64_, cd, const void *, VAL(cd, alpha), VAL(cd, beta), conj)

/* ---- level 3 ---- */

/* C = alpha * op(A) * op(B) + beta * C, with C m x n and k the inner size */
#define GEMM(NAME, T, AT_, A, B, CJ)                                                                     \
    EXPORT void NAME(int order, int ta, int tb, blasint m, blasint n, blasint k, AT_ alpha,              \
                     const void *av, blasint lda, const void *bv, blasint ldb, AT_ beta, void *cv,       \
                     blasint ldc)                                                                        \
    {                                                                                                    \
        const T *a = (const T *)av, *b = (const T *)bv, al = A, be = B;                                  \
        T *c = (T *)cv;                                                                                  \
        for (blasint i = 0; i < m; i++)                                                                  \
            for (blasint j = 0; j < n; j++) {                                                            \
                T s = 0;                                                                                 \
                for (blasint p = 0; p < k; p++) {                                                        \
                    T x = ta == NoTrans ? AT(a, lda, order, i, p) : AT(a, lda, order, p, i);             \
                    T y = tb == NoTrans ? AT(b, ldb, order, p, j) : AT(b, ldb, order, j, p);             \
                    s += (ta == ConjTrans ? CJ(x) : x) * (tb == ConjTrans ? CJ(y) : y);                  \
                }                                                                                        \
                T *e = &AT(c, ldc, order, i, j);                                                         \
                *e = be == 0 ? al * s : al * s + be * *e;                                                \
            }                                                                                            \
    }
GEMM(scipy_cblas_sgemm64_, float, float, alpha, beta, ID)
GEMM(scipy_cblas_dgemm64_, double, double, alpha, beta, ID)
GEMM(scipy_cblas_cgemm64_, cf, const void *, VAL(cf, alpha), VAL(cf, beta), conjf)
GEMM(scipy_cblas_zgemm64_, cd, const void *, VAL(cd, alpha), VAL(cd, beta), conj)

/* C = alpha * A * A^T + beta * C (or A^T * A), n x n, only the triangle chosen by uplo is written */
#define SYRK(NAME, T, AT_, A, B)                                                                         \
    EXPORT void NAME(int order, int uplo, int trans, blasint n, blasint k, AT_ alpha, const void *av,    \
                     blasint lda, AT_ beta, void *cv, blasint ldc)                                       \
    {                                                                                                    \
        const T *a = (const T *)av, al = A, be = B;                                                      \
        T *c = (T *)cv;                                                                                  \
        for (blasint i = 0; i < n; i++)                                                                  \
            for (blasint j = uplo == Upper ? i : 0; j < (uplo == Upper ? n : i + 1); j++) {              \
                T s = 0;                                                                                 \
                for (blasint p = 0; p < k; p++)                                                          \
                    s += trans == NoTrans ? AT(a, lda, order, i, p) * AT(a, lda, order, j, p)            \
                                          : AT(a, lda, order, p, i) * AT(a, lda, order, p, j);           \
                T *e = &AT(c, ldc, order, i, j);                                                         \
                *e = be == 0 ? al * s : al * s + be * *e;                                                \
            }                                                                                            \
    }
SYRK(scipy_cblas_ssyrk64_, float, float, alpha, beta)
SYRK(scipy_cblas_dsyrk64_, double, double, alpha, beta)
SYRK(scipy_cblas_csyrk64_, cf, const void *, VAL(cf, alpha), VAL(cf, beta))
SYRK(scipy_cblas_zsyrk64_, cd, const void *, VAL(cd, alpha), VAL(cd, beta))

/* ---- numpy.linalg: not available ---- */

static void missing(const char *name)
{
    fprintf(stderr, "minblas: %s is not available (this NumPy build has no linear algebra)\n", name);
    fflush(stderr);
    abort();
}
#define STUB(NAME) EXPORT void NAME(void) { missing(#NAME); }
STUB(scipy_scopy_64_) STUB(scipy_dcopy_64_) STUB(scipy_ccopy_64_) STUB(scipy_zcopy_64_)
STUB(scipy_sgesv_64_) STUB(scipy_dgesv_64_) STUB(scipy_cgesv_64_) STUB(scipy_zgesv_64_)
STUB(scipy_sgetrf_64_) STUB(scipy_dgetrf_64_) STUB(scipy_cgetrf_64_) STUB(scipy_zgetrf_64_)
STUB(scipy_spotrf_64_) STUB(scipy_dpotrf_64_) STUB(scipy_cpotrf_64_) STUB(scipy_zpotrf_64_)
STUB(scipy_sgesdd_64_) STUB(scipy_dgesdd_64_) STUB(scipy_cgesdd_64_) STUB(scipy_zgesdd_64_)
STUB(scipy_sgelsd_64_) STUB(scipy_dgelsd_64_) STUB(scipy_cgelsd_64_) STUB(scipy_zgelsd_64_)
STUB(scipy_sgeev_64_) STUB(scipy_dgeev_64_) STUB(scipy_zgeev_64_)
STUB(scipy_ssyevd_64_) STUB(scipy_dsyevd_64_) STUB(scipy_cheevd_64_) STUB(scipy_zheevd_64_)
STUB(scipy_dgeqrf_64_) STUB(scipy_zgeqrf_64_) STUB(scipy_dorgqr_64_) STUB(scipy_zungqr_64_)

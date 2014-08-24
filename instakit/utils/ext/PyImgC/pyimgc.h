#ifndef PY_ARRAY_UNIQUE_SYMBOL
#define PY_ARRAY_UNIQUE_SYMBOL PyImgC_PyArray_API_Symbol
#endif

#include <Python.h>
#include <structmember.h>

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION

#include <numpy/arrayobject.h>
#include <numpy/ndarraytypes.h>

/// lil' bit pythonic
#ifndef False
#define False 0
#endif
#ifndef True
#define True 1
#endif
#ifndef None
#define None NULL
#endif


#ifndef IMGC_DEBUG
#define IMGC_DEBUG False
#endif

/// UGH
#ifndef SENTINEL
#define SENTINEL {NULL}
#endif
#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC void
#endif

#ifndef BAIL_WITHOUT
#define BAIL_WITHOUT(thing) if (!thing) return None
#endif

//////////////// CONSTANTS
#if PY_VERSION_HEX <= 0x03000000
#define IMGC_PY3 False
#define IMGC_PY2 True
#else
#define IMGC_PY3 True
#define IMGC_PY2 False
#endif

#ifndef PyGetNone
#define PyGetNone Py_BuildValue("")
#endif

//////////////// TYPEDEFS
typedef struct {
    Py_ssize_t len;
    void *buf;
} rawbuffer_t;

//////////////// MACROS
void IMGC_OUT(FILE *stream, const char *format, ...) {
    va_list args;
    va_start(args, format);
    vfprintf(stream, format, args);
    va_end(args);
}
#define IMGC_STDOUT(format, ...) IMGC_OUT(stdout, format, ##__VA_ARGS__)
#define IMGC_STDERR(format, ...) IMGC_OUT(stderr, format, ##__VA_ARGS__)
#if IMGC_DEBUG > 0
    #define IMGC_TRACE(format, ...) IMGC_OUT(stderr, format, ##__VA_ARGS__)
#else
    #define IMGC_TRACE(format, ...) ((void)0)
#endif
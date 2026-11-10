"""Compile the kernels of the package of B4E1 with Cython."""

from Cython.Build import cythonize
from setuptools import setup

DIRECTIVES = {"boundscheck": False, "wraparound": False, "cdivision": True, "cpow": True, "annotation_typing": False,
              "infer_types": True, "freethreading_compatible": True}

setup(ext_modules=cythonize(["src/mhdpy/core/loops.py", "src/mhdpy/core/loops2.py"], language_level=3,
                            compiler_directives=DIRECTIVES))

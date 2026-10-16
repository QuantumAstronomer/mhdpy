## The kernel modes: the switch between compiled and uncompiled kernels, and the first kernel, backend (D04).
py.install_sources('__init__.py', 'mode.py', 'backend.py', 'backend.pyi', subdir: 'mhdpy/foundation/kernels')

## Kernels are .py files in Cython's pure Python mode (D04.1). Meson only recognises Cython in .pyx files, so each
## kernel is translated to C by an explicit cython call and then compiled as an extension module. The extension is
## installed next to its .py source, under the same name; Python imports the extension, unless the kernels are run
## uncompiled (mode.py).
backend_c = custom_target(
  'backend_c',
  input: 'backend.py',
  output: 'backend.c',
  command: [cython, '-3', '@INPUT@', '-o', '@OUTPUT@'],
)
py.extension_module('backend', backend_c, install: true, subdir: 'mhdpy/foundation/kernels')

subdir('tests')

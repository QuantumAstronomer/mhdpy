py.install_sources('__init__.py', 'conftest.py', 'py.typed', '_kernel_mode.py', '_backend.py', '_backend.pyi', subdir: 'mhdpy')

## Kernels are .py files in Cython's pure Python mode (D04.1). Meson only recognises Cython in .pyx files, so each
## kernel is translated to C by an explicit cython call and then compiled as an extension module.
backend_c = custom_target(
  '_backend_c',
  input: '_backend.py',
  output: '_backend.c',
  command: [cython, '-3', '@INPUT@', '-o', '@OUTPUT@'],
)
py.extension_module('_backend', backend_c, install: true, subdir: 'mhdpy')

subdir('foundation')
subdir('tests')

project('mhdpy', 'c')

py = import('python').find_installation(pure: false)
cython = find_program('cython')
directives = ['-X', 'boundscheck=False', '-X', 'wraparound=False', '-X', 'cdivision=True', '-X', 'cpow=True',
              '-X', 'annotation_typing=False', '-X', 'infer_types=True', '-X', 'freethreading_compatible=True']

## Meson takes only files .pyx as Cython, so a target of its own runs Cython on each kernel in the pure mode
foreach name : ['loops', 'loops2']
  c = custom_target(name + '.c', input: 'src/mhdpy/core/' + name + '.py', output: name + '.c',
                    depend_files: 'src/mhdpy/core/' + name + '.pxd',
                    command: [cython, '-3', directives, '@INPUT@', '-o', '@OUTPUT@'])
  py.extension_module(name, c, subdir: 'mhdpy/core', install: true)
endforeach

py.install_sources('src/mhdpy/__init__.py', subdir: 'mhdpy')
py.install_sources('src/mhdpy/infrastructure/__init__.py', 'src/mhdpy/infrastructure/units.py',
                   subdir: 'mhdpy/infrastructure')
py.install_sources('src/mhdpy/core/__init__.py', 'src/mhdpy/core/eos.py', subdir: 'mhdpy/core')

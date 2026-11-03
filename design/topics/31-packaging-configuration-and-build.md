# Packaging, configuration and build

## 1. Overview

A code reaches its users as a package or a source tree, and its physics and algorithms are chosen either when it is built or when it runs. The Python codes, pyro and Ulula, are packages on PyPI that install with one command of pip, while Zingale's one-dimensional scripts stand alone without a shared framework. Athena and Athena++ are compiled codes whose physics, coordinates, equation of state and Riemann solver are fixed at configuration, by a script that writes the makefile and a header of macros, and which depend on as little as possible. The references also show how releases, licences and the development of contributions are organised. Runtime parameters and the driver follow in topic 33, and testing and continuous integration in topic 25.

## 2. Designs

### 2.1 Python packages

pyro is the package pyro-hydro, built with setuptools, which takes its version from the tags of git through setuptools_scm; it needs NumPy, Numba, Matplotlib and h5py and installs with `pip install pyro-hydro`, or editable from a clone for work on the solvers, so that changes to the source take effect without a new installation. Installation puts the driver on the path, and a quick run of the advection of a smooth pulse checks it. Ulula is the package ulula, built with setuptools from its project file, which takes its version from a file of the package; it needs NumPy, SciPy, Matplotlib and h5py and installs with `pip install ulula`, or editable from a fork. **[GK]** The wheels of both on PyPI are pure Python, pyro's with kernels that Numba compiles at run time. Ulula's base class of setups imports the library six, which its project file does not declare and which arrives only through the dependencies of Matplotlib.

Detail: [pyro 3.1](../references/pyro-synthesis.md#31-packaging-installation-and-development), [Ulula 3.1](../references/ulula-synthesis.md#31-packaging-and-installation).

### 2.2 Self-contained scripts

The scripts that accompany Zingale's text, hydro_examples, are simple one-dimensional solvers in Python, organised in directories named after the chapters, each self-contained and without a shared framework ([Zingale's text](#zingale-2025), §A.3). A few classes recur, such as an exact Riemann solver for a gamma-law gas and, for multigrid, a class of cell-centred data on a one-dimensional grid with ghost cells, prolongation and restriction. pyro, by contrast, gives all its solvers one framework of grids and data, a driver and runtime parameters (topic 32).

Detail: [Zingale 3.4](../references/computational-hydrodynamics-synthesis.md#34-hydro_examples), [Zingale 3.5](../references/computational-hydrodynamics-synthesis.md#35-pyro).

### 2.3 Configuration at build time

Athena exists in C and in Fortran95, adheres strictly to the standards of each language so that it compiles on any machine, and avoids external libraries apart from MPI for parallel runs, leaving special formats to post-processing ([Stone et al.](#stone-et-al-2008) 2008, §7). In C a configure script from autoconf sets the physics and the algorithms at compile time, and in Fortran95 a Perl script chooses the modules. Athena++ builds in four steps.

1. Run its configuration script with the problem generator, the coordinates, the equation of state, the Riemann solver and flags for MHD, relativity, super time-stepping, FFT, MPI, OpenMP, HDF5 and further modules.
2. Let the script refuse incompatible choices, such as HLLC with MHD or relativity with an isothermal equation of state.
3. Let it write the makefile and a header from templates, whose macros fix the choices and sizes, such as the numbers of variables, scalars and ghost cells.
4. Compile the selected sources into one executable for that configuration.

A change of physics thus needs a new build, while the parameters of a run come from its input file.

Detail: [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop).

### 2.4 Dependencies, licences and development

Athena++ depends on as little as possible: its default configuration needs only a compiler of C++11 and Python, parallel runs a compiler with OpenMP or a library of MPI, and optional features FFTW3 and HDF5 ([Stone et al.](#stone-et-al-2020) 2020, §2.6). It is free and open, under the BSD licence of three clauses, chosen over version 3 of the GNU General Public License because it eases the redistribution of derived works, for instance within closed frameworks of national laboratories. Stable releases appear in a public repository, while a core team develops in a private one and welcomes reports and contributions, and the authors consider separating the framework of refinement from the physics so that the framework could be developed openly. pyro takes contributions as pull requests from forks, tests each automatically and reviews it, and may squash small commits on merge; Ulula's contributors work in forks on Bitbucket.

Detail: [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop), [pyro 3.1](../references/pyro-synthesis.md#31-packaging-installation-and-development), [Ulula 3.1](../references/ulula-synthesis.md#31-packaging-and-installation).

## 3. Tests

The references test their builds rather than their packages. pyro's installation is checked by a quick run of the advection solver, Athena++'s regression suite includes tests that only check that the code compiles for each metric of general relativity, and its continuous integration builds every change with several compilers, architectures and versions of libraries (topic 25). No reference tests the installation of its package on a clean system.

Detail: [pyro 3.1](../references/pyro-synthesis.md#31-packaging-installation-and-development), [Athena 3.1](../references/athena-synthesis.md#31-configuration-build-and-the-main-loop).

## 4. Assessment

Athena's adherence to standards lets it compile on any machine, and the default configuration of Athena++ needs only a compiler and Python (Stone et al. 2008, 2020). **[GK]** A pure-Python package with NumPy as its main dependency meets the exception of the project's priorities, installation by a single command of pip or uv, on macOS and Linux alike, and keeps the code readable. Compiled kernels raise performance, which ranks above readability, but each route costs something: Numba installs from wheels with one command but compiles at run time and restricts the Python it accepts, while extension modules in C or Cython need wheels built for every platform to keep the single command. Configuration at build time, as in Athena++, lets the compiler specialise every loop, which Python cannot exploit, so that mhdpy chooses its physics at run time by composing objects, at some cost per call that vectorised kernels hide. Versions from the tags of git keep releases and code in step, and undeclared dependencies, as in Ulula, break clean installations. A permissive licence such as BSD eases reuse, while the GPL headers of some modules of Athena++ would bind any code copied from them to that licence. Open are the build backend, whether compiled kernels are admitted and in which form, the licence, and a test of installation on clean macOS and Linux systems.

## 5. Sources

- <a id="stone-et-al-2008"></a>Stone, J. M., Gardiner, T. A., Teuben, P., Hawley, J. F. and Simon, J. B., Athena: a new code for astrophysical MHD, ApJS 178, 137–177 (2008), [arXiv:0804.0402](https://arxiv.org/abs/0804.0402), [doi:10.1086/588755](https://doi.org/10.1086/588755).
- <a id="stone-et-al-2020"></a>Stone, J. M., Tomida, K., White, C. J. and Felker, K. G., The Athena++ adaptive mesh refinement framework: design and magnetohydrodynamic solvers, ApJS 249, 4 (2020), [arXiv:2005.06651](https://arxiv.org/abs/2005.06651), [doi:10.3847/1538-4365/ab929b](https://doi.org/10.3847/1538-4365/ab929b).
- <a id="zingale-2025"></a>Zingale, M., *Introduction to Computational Astrophysical Hydrodynamics*, the Open Astrophysics Bookshelf, version of 26 January 2025, [PDF](https://open-astrophysics-bookshelf.github.io/numerical_exercises/CompHydroTutorial.pdf).

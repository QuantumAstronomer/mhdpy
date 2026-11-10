cmake_minimum_required(VERSION 3.21...4.0)
project(${SKBUILD_PROJECT_NAME} LANGUAGES C)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
include(UseCython)

foreach(name loops loops2)
  cython_transpile(src/mhdpy/core/${name}.py LANGUAGE C OUTPUT_VARIABLE source
    CYTHON_ARGS -3 -X boundscheck=False -X wraparound=False -X cdivision=True -X cpow=True
                -X annotation_typing=False -X infer_types=True -X freethreading_compatible=True)
  python_add_library(${name} MODULE ${source} WITH_SOABI)
  install(TARGETS ${name} DESTINATION mhdpy/core)
endforeach()

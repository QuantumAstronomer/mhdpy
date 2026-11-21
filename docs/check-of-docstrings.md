# The check of docstrings

Outside the tests, every docstring of mhdpy documents the parameters of its function, or the fields of its class, with their types and defaults, and its return value by its type, as §3.2 of [CLAUDE.md](../CLAUDE.md) asks. The check of docstrings makes sure that the docstrings and the signatures name the same parameters with the same annotations. It does so by walking through the code, collecting the signature and the docstring of every function, method and class, and comparing them. pyright checks the annotations but reads no docstring, so that without the check a type or default copied by hand would drift from its code unseen. This document explains each part to a reader new to the repository. The requirements that the parts meet, with their reasons, are [DOCS01](../design/requirements/infrastructure/check-of-docstrings.md#docs01) to [DOCS08](../design/requirements/infrastructure/check-of-docstrings.md#docs08) in the [requirements of the check](../design/requirements/infrastructure/check-of-docstrings.md), and the decisions behind them are taken in [B7D1](../design/briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check) and [B7D2](../design/briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares).

## Reading the code

The check is the module `tests/test_docstrings.py`, which relies on the standard library alone. It reads every module of `src/` and `tests/` and their folders from its source with the module `ast`, without importing it ([DOCS01](../design/requirements/infrastructure/check-of-docstrings.md#docs01)), so that a module which fails to import is still checked. No existing tool serves instead: pydoclint compares types with annotations as well, but reads only titles underlined by dashes and puts the fields of a class under Attributes, so that it would have demanded another form of the docstrings ([B7D1](../design/briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check)).

The objects are the functions and classes at the head of a module, and the functions and classes in the body of such a class. Each is named by the path of its module and its qualified name, as `src/mhdpy/infrastructure/units.py::Units.factor`. The tests are left out, as §3.2 gives the sections to the docstrings outside them: in a test module, the functions at its head whose names begin with `test`, and the classes at its head whose names begin with `Test` with everything that they hold, their helpers and fixtures among them. The helpers at the head of a test module, such as `check` and `tree` of the check of requirements, are checked. Properties are left out as well, as their docstrings keep a summary alone.

The signature of a function, read by `function_signature`, is its parameters in the order that Python defines, positional, `*name`, keyword only and `**name`, each with its annotation and its default, and its return annotation. The first parameter of a method, as `self`, is left out unless the method is static, as no caller passes it, and a return annotation `None` counts as none. The signature of a dataclass or named tuple, read by `class_signature`, is its fields: the names annotated in its body, without the class variables annotated `ClassVar`, each with its default, given directly or as the keyword `default` of `field`. Any other class has no parameters, and no class has a return value.

The annotations and defaults are taken as the source text that the code holds, by the function `text`, and compared verbatim, as the author decided. A default written `1e5` in the code is therefore written `1e5` in the docstring, not `100000.0`, and the spaces by which the fields of `Units` are aligned take no part, as each annotation and default is cut from the source alone.

## Reading the docstrings

A section is a line that holds its title, Parameters or Returns, alone, followed by a line of `=` alone, and it holds the lines up to the next blank line ([DOCS02](../design/requirements/infrastructure/check-of-docstrings.md#docs02)). Its entries, read by `read_sections`, are its lines at the indentation of its title, while the lines indented further describe them. An entry of Parameters reads `name : type`, followed by `(default = value)` where it shows a default, as in the docstring of `Units`:

```text
    Parameters
    ====================================================================================================================
    mass : float (default = 1.0)
        The code unit of mass in grams.
```

An entry of Returns is a type alone. The line "Implements UNIT01 and UNIT12." after a blank line lies outside every section, and Raises and the descriptions are not read. A docstring that is missing counts as one without sections, and a section whose title or rule is malformed is not found. Either then fails as a missing section wherever one is due, rather than hiding the docstring from the check ([B7D2](../design/briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares)).

## Faults

The function `check` reads every object with its signature and its sections, kept in a record `Documented`, and fails on five faults, each found by a function of its own:

- Entries of Parameters that do not name the parameters or fields in their order and without others, as after a parameter added, renamed or removed in the code alone, found by `misnamed_parameters` ([DOCS03](../design/requirements/infrastructure/check-of-docstrings.md#docs03)).
- An entry whose type differs from the annotation, or whose parameter has none, found by `mistyped_parameters` ([DOCS04](../design/requirements/infrastructure/check-of-docstrings.md#docs04)).
- An entry whose default differs from that of the code, or that shows a default where the code has none or none where it has one, found by `mistaken_defaults` ([DOCS05](../design/requirements/infrastructure/check-of-docstrings.md#docs05)).
- A Returns that is missing where the return annotation is other than `None`, or that stands where it is `None` or missing, found by `misplaced_returns` ([DOCS06](../design/requirements/infrastructure/check-of-docstrings.md#docs06)).
- A Returns that holds other than one entry, or whose entry differs from the return annotation, found by `mistyped_returns` ([DOCS07](../design/requirements/infrastructure/check-of-docstrings.md#docs07)).

Each fault is one line of the failure, which names the object with what its docstring and its code hold. All faults are gathered before the check fails, so that one run names every one of them. Were the default mass of `Units` changed to `1e3` in the code alone, the check would fail with:

```text
src/mhdpy/infrastructure/units.py::Units documents the default of mass as '1.0', the code gives '1e3'
```

## The check as a test

The check runs as the test `test_docstrings` of the class `TestMhdpy`, on the checkout itself ([DOCS08](../design/requirements/infrastructure/check-of-docstrings.md#docs08)), beside the test `test_citations` of the [check of requirements](check-of-requirements.md). Every full run of the tests, and so every commit, then fails on a docstring that no longer repeats its signature. The check reads its own module too, whose helpers lie at the head of a test module and carry the sections like any other code.

The other tests of the module show that the check works. As mhdpy itself has no fault, each of them writes a small tree of made-up modules into the temporary folder that pytest gives it, with the function `tree` of the check of requirements, and runs the check on that tree instead. The classes `TestReading`, `TestParameters` and `TestReturns` follow the sections of the requirement document. In `TestParameters` and `TestReturns`, a tree without faults receives one kind of fault in each test, and the test requires the failure to name each object concerned.

## Working with the check

The check runs with the other tests:

```bash
uv run pytest
```

A function or class that is added or changed outside the tests carries the sections of §3.2 in step with its code: an entry for each parameter or field in its order, with its annotation and default written as in the code, and Returns with the return annotation wherever it is other than `None`.

# The check of requirements

Every test of mhdpy names the requirements that it checks at the start of its docstring, as "Checks RIEM04 and RIEM05.", so that the reasoning which the test leaves out is one search away. The check of requirements makes sure that these citations stay true. It fails on a test that cites nothing, or that cites a requirement which does not exist or is withdrawn, and on two requirements that bear one identifier. It warns, without failing, of the requirements that no test cites yet, and run as a script it lists each requirement with its tests. This document explains each part to a reader new to the repository. The requirements that the parts meet, with their reasons, are [CITE01](../design/requirements/infrastructure/check-of-requirements.md#cite01) to [CITE09](../design/requirements/infrastructure/check-of-requirements.md#cite09) in the [requirements of the check](../design/requirements/infrastructure/check-of-requirements.md), the decision behind them is taken in [B6D7](../design/briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements), and the forms of citation are set by [§1 of the rules of the requirements](../design/templates/requirements-rules.md#1-files-and-identifiers).

## Reading

The check is the module `tests/test_requirements.py`, which relies on the standard library alone. It reads every test from the source of its module with the module `ast`, without importing it ([CITE01](../design/requirements/infrastructure/check-of-requirements.md#cite01)), so that a module which fails to import still shows its citations and the check needs no run of pytest. A test is a function whose name begins with `test` at the head of a module `test_*.py` or `*_test.py` in `tests/` or its folders, or such a method of a class at the head of the module whose name begins with `Test`, as pytest collects them. It is named by its node id, as `tests/test_package.py::TestLayout::test_package`, by which pytest runs it alone. Its citation is the opening sentence of its docstring, where that sentence begins with the word "Checks" and names at least one identifier, a word of capitals followed by two digits. The sentence ends at the first full stop followed by whitespace or by the end of the docstring, so that a dotted name such as `mhdpy.core` does not end it.

The requirements are read from the documents in `design/requirements/` and its folders themselves, so that no second list of identifiers can drift from them ([CITE02](../design/requirements/infrastructure/check-of-requirements.md#cite02)). A requirement is a paragraph that opens with an anchor named by its identifier in lower case and then that identifier in bold, as `<a id="cite01"></a>**CITE01**`. It is withdrawn where its text then opens with "Withdrawn on", as [§5 of the rules](../design/templates/requirements-rules.md#5-agreement-and-change) has every withdrawn paragraph open. A paragraph whose anchor is not its identifier is no requirement to the check, so that a citation of it fails and its broken link comes to light.

## Faults

The function `check` reads both and fails on four faults, each found by a function of its own:

- A test whose docstring opens with no citation, found by `uncited_tests` ([CITE03](../design/requirements/infrastructure/check-of-requirements.md#cite03)).
- A test that cites an identifier which no requirement bears, as after a typing error, found by `unknown_citations` ([CITE04](../design/requirements/infrastructure/check-of-requirements.md#cite04)).
- A test that cites a withdrawn requirement, whose tests should have moved to its successor, found by `withdrawn_citations` ([CITE05](../design/requirements/infrastructure/check-of-requirements.md#cite05)).
- An identifier that two requirements bear, which would make every citation of it ambiguous, found by `duplicate_identifiers` ([CITE06](../design/requirements/infrastructure/check-of-requirements.md#cite06)).

Each fault is one line of the failure, which names the test with the identifier concerned, or the document of each requirement that bears the duplicate. All faults are gathered before the check fails, so that one run names every one of them.

## Requirements without tests

A requirement that is in force and that no test cites is no fault. Requirements are written before their tests, which follow one at a time, each committed with its code, so that such a requirement is normal until its component is finished. The check names every such requirement, found by `untested_requirements`, in one warning of the category `UntestedRequirementWarning`, a subclass of `UserWarning`, which pytest lists at the end of a run ([CITE07](../design/requirements/infrastructure/check-of-requirements.md#cite07)). The category of its own lets a filter tell the warning from others, should warnings once be turned into errors. The warning shrinks as the tests of a stratum are written, and a finished stratum runs without it.

## The list

Run as a script, the module prints every requirement with the node ids of the tests that cite it ([CITE08](../design/requirements/infrastructure/check-of-requirements.md#cite08)). The function `listing` gives each document by its path, below it each of its requirements, marked `(withdrawn)` or `(no test)` where that holds, and below each requirement the tests that cite it:

```text
design/requirements/infrastructure/package.md
    PACK13
        tests/test_package.py::TestVersion::test_build_at_tag
        tests/test_package.py::TestVersion::test_build_after_tag
```

The list shows what a run of the tests does not print: which test checks which requirement, and the tests that still cite a withdrawn one. It serves when a requirement document is agreed or a component is judged finished, as [§5 of the rules](../design/templates/requirements-rules.md#5-agreement-and-change) asks.

## The check as a test

The check runs as the test `test_citations` of the class `TestMhdpy`, on the checkout itself ([CITE09](../design/requirements/infrastructure/check-of-requirements.md#cite09)). Every full run of the tests, and so every commit, then fails on a fault in the tests or documents of mhdpy, as the check of imports fails on a forbidden import ([B1D5](../design/briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule)). A run of some tests alone leaves it out, so that it neither fails nor warns about the tests that were not run. The check sees the tests as written rather than as pytest collects them, so that a test made at run time would escape it, which [B6D7](../design/briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) accepts until tests come to be made so.

The other tests of the module show that the check works. As mhdpy itself has no fault, each of them writes a small tree of made-up test modules and requirement documents into the temporary folder that pytest gives it, with identifiers such as FOO01 that no document of mhdpy bears, and runs the check on that tree instead. The classes `TestReading`, `TestFaults`, `TestUntested` and `TestList` follow the sections of the requirement document. In `TestFaults`, a tree without faults receives one fault in each test, and the test requires the failure to name it.

## Working with the check

The check runs with the other tests, and the list is printed by:

```bash
uv run pytest
uv run python tests/test_requirements.py
```

A test that is added cites its requirements in the first sentence of its docstring, and a requirement that is withdrawn keeps its paragraph, which opens with "Withdrawn on", while the tests that cite it move to its successor.

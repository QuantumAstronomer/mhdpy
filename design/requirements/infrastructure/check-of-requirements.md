# Check of requirements

**Prefix.** CITE.

**Status.** Agreed on 2026-11-11.

**Briefs.** [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements).

## Scope

The check of requirements reads the tests of mhdpy and its requirement documents, and judges whether every test cites, at the start of its docstring, requirements that exist and are not withdrawn, as §2.5 and [§1 of the rules of the requirements](../../templates/requirements-rules.md#1-files-and-identifiers) ask. It warns of the requirements that no test cites yet and, run as a script, lists each requirement with its tests, as [§5 of the rules](../../templates/requirements-rules.md#5-agreement-and-change) asks of it. What a test checks is left to the test, and what a requirement states, and how a document is agreed or changed, to the rules.

A test is a function whose name begins with `test` at the head of a module `test_*.py` or `*_test.py` in `tests/` or its folders, or a method whose name begins with `test` of a class at the head of such a module whose name begins with `Test`, as pytest collects them by default. A test is named by its node id of pytest, as `tests/test_imports.py::test_contracts`, by which pytest runs it alone. A citation is the opening sentence of the docstring of a test, where it begins with the word `Checks` and names at least one identifier, as "Checks RIEM04 and RIEM05.". An identifier is a word of capitals followed by two digits, as §1 of the rules forms it. A requirement is a paragraph of a document in `design/requirements/` or its folders that opens with an anchor named by an identifier in lower case and then that identifier in bold, and it is withdrawn where its text then opens with `Withdrawn on`, as §5 of the rules has every withdrawn paragraph open. The check is the test `test_citations` of the module `tests/test_requirements.py`, which also holds the tests of the check and prints the list when run as a script. It relies on the standard library alone, and on pytest to run it.

## Reading

<a id="cite01"></a>**CITE01** The check shall read every test from the source of its module, without importing it. [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) reads the files with the module `ast` of the standard library rather than the tests that pytest collects, so that the check needs no dependency and sees every test as written, free of partial runs and of the hooks of pytest. A module that fails to import still shows its citations, as none of its code runs. A test made at run time escapes the check, which B6D7 accepts until tests come to be made so.

<a id="cite02"></a>**CITE02** The check shall read the requirements, and whether each is withdrawn, from every document in `design/requirements/` and its folders. [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) reads the anchors and the withdrawn requirements from the documents themselves, so that no second list of identifiers can drift from them ([§5 of the rules](../../templates/requirements-rules.md#5-agreement-and-change)). As each document lies in the folder of its stratum ([§1 of the rules](../../templates/requirements-rules.md#1-files-and-identifiers)), the check reads every folder below `design/requirements/`. A paragraph whose anchor is not its identifier in lower case is no requirement to the check, so that a citation of it fails as unknown and its broken link comes to light.

## Faults

<a id="cite03"></a>**CITE03** If the docstring of a test opens with no citation, then the check shall fail, naming each such test. Every test names the requirements that it checks (§2.5), at the start of its docstring ([§1 of the rules](../../templates/requirements-rules.md#1-files-and-identifiers)), so that the reasoning which the test leaves out is one search away. [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) counts a test that cites nothing as a fault at every stage of a component, unlike a requirement without a test.

<a id="cite04"></a>**CITE04** If a test cites an identifier that no requirement bears, then the check shall fail, naming each such test with the identifier. A mistyped or invented identifier would send a reader to a requirement that does not exist, and [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) fails on it in every full run, and so in every commit, as the check of the rule fails on a forbidden import ([B1D5](../../briefs/B01-strata-in-package.md#b1d5-the-check-of-the-rule)).

<a id="cite05"></a>**CITE05** If a test cites a withdrawn requirement, then the check shall fail, naming each such test with the requirement. A withdrawn requirement no longer holds, and the tests and code that cite it move to its successor ([§5 of the rules](../../templates/requirements-rules.md#5-agreement-and-change)), which [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) enforces for the tests.

<a id="cite06"></a>**CITE06** If two requirements bear the same identifier, then the check shall fail, naming the document of each. An identifier names one requirement and its number is never reused ([§1 of the rules](../../templates/requirements-rules.md#1-files-and-identifiers)), so that a duplicate would make every citation of it ambiguous. [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) leaves the case unnamed, and the check, which reads every identifier, enforces the rule at no further cost, as the author decided.

## Requirements without tests

<a id="cite07"></a>**CITE07** When any requirement that is not withdrawn is cited by no test, the check shall name every such requirement in one warning of the category `UntestedRequirementWarning`, a subclass of `UserWarning`, without failing. Requirements come before their tests, which follow one at a time, each committed with its code (§2.5, §2.6 and §3.4), so that a requirement without a test is normal until its component is finished ([B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements)). pytest lists the warning at the end of a run, as one entry however many requirements it names. As no brief turns warnings into errors, the category of its own only lets a filter tell the warning from others, so that a later decision to turn them into errors can exempt it, as the author decided.

## The list

<a id="cite08"></a>**CITE08** When `tests/test_requirements.py` runs as a script, it shall print every requirement with the node ids of the tests that cite it, and mark each requirement that no test cites and each that is withdrawn. [§5 of the rules](../../templates/requirements-rules.md#5-agreement-and-change) asks for a list of each requirement with its tests, of those without tests and of the tests that cite a withdrawn requirement, derived from the tests rather than kept by hand. [B6D7](../../briefs/B06-testing-and-verification.md#b6d7-the-check-of-requirements) prints it from the module that checks, by `uv run python tests/test_requirements.py`, so that the full list, which a run of the tests does not print, is one command away when a document is agreed or a component judged finished.

## The tests and documents of mhdpy

<a id="cite09"></a>**CITE09** The tests and requirement documents of mhdpy shall give the check none of the faults of [CITE03](#cite03) to [CITE06](#cite06). [§5 of the overview](../../overview.md#5-crosscutting-concepts) has every test name the requirements that it checks, which the check verifies over the whole suite in every full run, and so in every commit. CITE03 to CITE06 state how the check meets each fault, and the tests of the check try each on small trees of tests and documents made for it, while this requirement holds for the tests and documents of mhdpy themselves.

## Verification

None. The check judges the tests and documents of mhdpy rather than a result of it, on which [§1.3 of the overview](../../overview.md#13-success-criteria) sets its criteria.

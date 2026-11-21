# Check of docstrings

**Prefix.** DOCS.

**Status.** Agreed on 2026-11-21.

**Briefs.** [B7D1](../../briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check) and [B7D2](../../briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares).

## Scope

The check of docstrings reads the source of mhdpy and judges whether every docstring outside the tests repeats the signature of its code, as §3.2 of [CLAUDE.md](../../../CLAUDE.md) and [B7D2](../../briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares) ask: the names, types and defaults of the parameters of a function, or of the fields of a class, in their order, and the type of its return value. The descriptions, the section Raises and the form of a docstring beyond what is needed to read it are left unjudged, and the annotations themselves are left to pyright.

The code checked is every module `*.py` in `src/` and `tests/` and their folders, the trees that pyright checks. An object is a function or class at the head of a module, or a function or class in the body of such a class, and it is named by the path of its module and its qualified name, as `src/mhdpy/infrastructure/units.py::Units.factor`. The tests are, in a test module as the [check of requirements](check-of-requirements.md#scope) defines it, the functions at its head whose names begin with `test`, and the classes at its head whose names begin with `Test` with every object that they hold. Properties, the functions decorated by `property` or `cached_property`, are left out with the tests, as their docstrings keep a summary alone.

The signature of a function is its parameters in their order, positional only, positional or keyword, `*name`, keyword only and `**name`, each with its annotation and default, without the first parameter of a method that is not a static method, and its return annotation. The signature of a class decorated by `dataclass`, or derived from `NamedTuple`, is its fields: the names annotated in its body, other than the class variables annotated `ClassVar`, each with its annotation and default, given directly or as the keyword `default` of `field`. The signature of any other class is empty, and no class has a return value. The annotations and defaults are taken as the source text that the code holds, as `ast.get_source_segment` gives it, so that `1e5` stays `1e5`.

A section is a line of the docstring that holds its title, `Parameters` or `Returns`, alone, followed by a line of `=` alone, and it holds the lines up to the next blank line or the end of the docstring. Its entries are its lines at the indentation of its title, and the lines indented further below an entry describe it. An entry of Parameters reads `name : type`, followed by ` (default = value)` where it shows a default, and names a variadic parameter as `*name` or `**name`. An entry of Returns is a type alone. A docstring that is missing counts as one without sections.

The check gathers every fault before it fails, and names each on a line of its own. It is the test `test_docstrings` of the module `tests/test_docstrings.py`, which also holds the tests of the check. It relies on the standard library alone, and on pytest to run it.

## Reading

<a id="docs01"></a>**DOCS01** The check shall read every object outside the tests, with its docstring and signature, from the source of its module, without importing it. [B7D1](../../briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check) reads the files with the module `ast` of the standard library, as the [check of requirements](check-of-requirements.md#cite01) reads the tests, so that the check needs no dependency and sees the code as written. The tests are left out as §3.2 gives the sections to the docstrings outside them, and with a class of tests go the helpers and fixtures that it holds, which the revision of the docstrings left without sections, as the author decided.

<a id="docs02"></a>**DOCS02** The check shall read the sections Parameters and Returns of a docstring, and the entries of each, in the form that the scope defines. The form is that of §3.2, which [B7D1](../../briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check) keeps rather than the form of a tool. A section whose title or rule is malformed is not found, so that the check then fails on a missing section rather than passing it unseen ([B7D2](../../briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares)).

## Parameters

<a id="docs03"></a>**DOCS03** If the entries of Parameters do not name the parameters of a function, or the fields of a class, in their order and without others, then the check shall fail, naming the object with the names of both. [B7D2](../../briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares) compares the whole signature, so that a parameter added, renamed or removed without its entry, the drift least likely to be seen in review, fails. The first parameter of a method is left out, as no caller passes it.

<a id="docs04"></a>**DOCS04** If the type of an entry of Parameters differs from the source text of the annotation of the parameter or field that it names, or that parameter has no annotation, then the check shall fail, naming the object and the entry with both types. §3.2 writes the types as in the annotations, which pyright checks while it reads no docstring, so that the check carries the annotations into the docstrings ([B7D1](../../briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check)). The types are compared as text, verbatim, as the author decided, so that a type is written once and read the same in both places. A parameter without an annotation fails as well, as the author decided, so that the check holds without pyright, which in its strict mode already asks for every annotation.

<a id="docs05"></a>**DOCS05** If the default of an entry of Parameters differs from the source text of the default of the parameter or field that it names, or the entry shows a default where the code has none or none where it has one, then the check shall fail, naming the object and the entry with both defaults. The defaults are copied by hand as the types are and drift in the same way ([B7D2](../../briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares)). A field given by `field` without the keyword `default` has no default to the check.

## Returns

<a id="docs06"></a>**DOCS06** If a function has a return annotation other than `None` and its docstring no Returns, or a docstring has Returns while its object has no return annotation, or `None`, then the check shall fail, naming the object. [B7D2](../../briefs/B07-check-of-docstrings.md#b7d2-what-the-check-compares) has Returns stand exactly where the return annotation is other than `None`, so that a function that comes to return a value fails until its docstring says what it returns.

<a id="docs07"></a>**DOCS07** If Returns holds other than one entry, or its entry differs from the source text of the return annotation, then the check shall fail, naming the object with both. A function returns one value, whose type the annotation gives, a tuple among them, and §3.2 writes it as a type alone, compared as the types of DOCS04 are.

## The docstrings of mhdpy

<a id="docs08"></a>**DOCS08** The docstrings of mhdpy outside the tests shall give the check none of the faults of [DOCS03](#docs03) to [DOCS07](#docs07). The check runs over the whole of `src/` and `tests/` in every full run of the tests, and so in every commit, as [B7D1](../../briefs/B07-check-of-docstrings.md#b7d1-the-tool-of-the-check) places it at the top of `tests/` after the check of requirements. DOCS03 to DOCS07 state how the check meets each fault, and the tests of the check try each on small trees of modules made for it, while this requirement holds for the code of mhdpy itself.

## Verification

None. The check judges the docstrings of mhdpy rather than a result of it, on which [§1.3 of the overview](../../overview.md#13-success-criteria) sets its criteria.

"""Templates of parameter files: every parameter of a run at its default, documented, as a TOML document.

A user who starts a new run needs to know which parameters exist, what they mean, and what their defaults are.
``mhdpy parameters`` answers this by writing a template parameter file for a problem (D15.5), which the user then edits
and passes to ``mhdpy run``. The template gives every parameter at its default, as declared, a default given with a
unit as that string, such as ``"100 pc"``, so that the template, read back unchanged as a parameter file, resolves to
exactly the defaults (PAR20). Comments give each parameter's documentation, unit, condition and restart behaviour, so
that what a parameter means is at hand where its value is set.

The parameters are written in one table per section, the section of a name being everything before its last dot, so
that ``output.snapshot.dt`` is the key ``dt`` of the table ``[output.snapshot]``. The tables follow the order in which
their first parameter was declared, and the parameters in a table the order of their declarations. Where a quantity
can be given in more than one way, the parameters of every group but the default are written as comments, with their
defaults, so that the template selects the default group of each set of alternatives; a comment before the first
parameter of a set names its groups (PAR22).

TOML is written here, by mhdpy itself: the standard library reads TOML but does not write it. The types of PAR03 are
simple enough to write exactly: a float as the shortest digits that read back as the same double, which every default
has, being finite (PAR24), and a string with every character that TOML does not allow as it is escaped.

For example, the template of a run, as ``mhdpy parameters`` writes it::

    from mhdpy.foundation.parameters.templates import template

    Path("run.toml").write_text(template(declarations))

The requirement this module fulfils is in ``docs/requirements/L0-foundation/parameters.md`` (PAR20), and it is tested in
``tests/test_templates.py``.
"""

import textwrap

from mhdpy.foundation.parameters.declarations import Alternatives, Declarations, Parameter
from mhdpy.foundation.parameters.values import is_list
from mhdpy.foundation.units import notation

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["template"]

## The width of the lines of a template, as of mhdpy's own code (D01.7), to which its comments are wrapped.
_WIDTH = 120

## The comment at the top of every template: what its values are, and how values with a unit and alternatives are given.
_HEADER = (
    "The parameters of the run, each at its default. A plain number is a value in code units; a number with a unit is "
    'given as a string, such as "100 pc". A parameter written as a comment belongs to another way of giving a '
    "quantity: give the parameters of one way only."
)

## The characters a TOML basic string writes with an escape of their own: the quotation mark and the backslash, which
## would end the string or start an escape, and the control characters that have a short escape. Every other control
## character is written by its code point (TOML 1.0, basic strings).
_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}


def _comment(text: str) -> list[str]:
    """Return text as the lines of a TOML comment, each starting with "# ", wrapped at the width of the template."""
    ## The width less the two characters of "# ". A word longer than a line, such as a long path, is kept whole.
    lines = textwrap.wrap(text, width=_WIDTH - 2, break_long_words=False, break_on_hyphens=False)
    return [f"# {line}" for line in lines]


def _string(text: str) -> str:
    """Return a string as a TOML basic string, in double quotes, with every character TOML refuses as it is escaped."""
    ## TOML refuses in a basic string, as they are, the characters with an escape of their own and every other control
    ## character, U+0000 to U+001F and U+007F (DEL), which are written as \uXXXX. Any other character is written as it
    ## is, a letter outside ASCII included, since a TOML document is UTF-8.
    characters = [
        _ESCAPES.get(
            character, f"\\u{ord(character):04X}" if ord(character) < 0x20 or ord(character) == 0x7F else character
        )
        for character in text
    ]
    return '"' + "".join(characters) + '"'


def _value(value: object) -> str:
    """Return a value of one of the types of PAR03 as TOML writes it, so that a TOML reader reads back that value."""
    ## A boolean first, as it is an integer to isinstance(), but written as true or false.
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _string(value)
    if is_list(value):
        return "[" + ", ".join(_value(element) for element in value) + "]"

    ## An integer or a float, the types left (PAR03). repr gives the shortest digits that read back as the same double,
    ## such as 0.1 or 1e+16, with the sign of -0.0 kept, all valid TOML; an integer is written as it is.
    return repr(value)


def _dimensions(dimensions: dict[str, float]) -> str:
    """Return dimensions in words, as the base dimensions with their exponents, such as "length^2 time^-1"."""
    ## In the order of the base dimensions, as a unit expression writes them, with an exponent of 1 left out and every
    ## other written in its shortest form: 2 rather than 2.0, and -0.5 as it is.
    words: list[str] = []
    for name in notation.DIMENSIONS:
        if name in dimensions:
            exponent = dimensions[name]
            words.append(name if exponent == 1 else f"{name}^{exponent:g}")
    return " ".join(words)


def _facts(parameter: Parameter) -> str:
    """Return the facts of a parameter in words, as a template writes them below its documentation (PAR20).

    Its unit, if it is a number: dimensionless, a named unit with its label in cgs, kelvin for a temperature, or its
    dimensions; its condition, in the words of its check; and whether it may change on restart (PAR16).
    """
    facts: list[str] = []
    if parameter.unit is not None:
        ## The dimensions the declaration has checked (PAR04): none for a dimensionless parameter, and a temperature
        ## alone for one in kelvin, which code units do not convert (UNI10).
        found = notation.unit_dimensions(parameter.unit)
        if not found:
            facts.append("Dimensionless.")
        elif isinstance(parameter.unit, str):
            facts.append(f"Unit: {parameter.unit} ({notation.LABELS[parameter.unit]}).")
        elif found == {"temperature": 1}:
            facts.append("Unit: kelvin.")
        else:
            facts.append(f"Dimensions: {_dimensions(found)}.")
    if parameter.check is not None:
        facts.append(f"Must be {parameter.check.description}.")
    facts.append("Changeable on restart." if parameter.changeable else "Fixed on restart.")
    return " ".join(facts)


def _ways(alternatives: Alternatives) -> str:
    """Return a set of alternatives in words: its name, its documentation, and its groups, the default named (PAR22)."""
    groups = [
        f"{group} ({', '.join(names)}){', the default' if group == alternatives.default else ''}"
        for group, names in alternatives.groups.items()
    ]
    return f"{alternatives.name}: {alternatives.doc} Given in one of these ways: {'; '.join(groups)}."


def template(declarations: Declarations) -> str:
    """Return a template parameter file for a set of declarations: every parameter at its default, documented (PAR20).

    The template is a TOML document with a table for each section of the names, in which every parameter is written at
    its default as declared, a default given with a unit as that string. Above each parameter, comments give its
    documentation, then its unit, its condition and whether it may change on restart. The parameters of every group of
    a set of alternatives but the default are written as comments, with their defaults, so that the template selects
    the default groups, and the set is described before its first parameter (PAR22). Read back unchanged as a parameter
    file, the template resolves to exactly the defaults.

    Parameters
    ----------
    declarations : Declarations
        The parameters of the run, as declared by its modules.

    Returns
    -------
    str
        The template, a TOML document, with lines of at most 120 characters but for a word longer than that.
    """
    ## The names of the parameters written as comments: those of every group but the default of each set (PAR22).
    commented = {
        name
        for alternatives in declarations.alternatives
        for group, names in alternatives.groups.items()
        if group != alternatives.default
        for name in names
    }

    ## Each set of alternatives by the name of its first parameter in the order of the declarations, before which the
    ## set is described.
    order = {parameter.name: index for index, parameter in enumerate(declarations.parameters)}
    first: dict[str, Alternatives] = {}
    for alternatives in declarations.alternatives:
        names = [name for group in alternatives.groups.values() for name in group]
        first[min(names, key=order.__getitem__)] = alternatives

    ## The parameters of each section, in the order of the declarations: a section is written as one table, in the
    ## order in which its first parameter was declared, so that no table is written twice.
    sections: dict[str, list[Parameter]] = {}
    for parameter in declarations.parameters:
        sections.setdefault(parameter.name.rpartition(".")[0], []).append(parameter)

    ## The header, then each table with its parameters, each after a blank line: the description of a set of
    ## alternatives before its first parameter, the documentation, the facts, and the key with the default, as a
    ## comment for a parameter of a group that is not the default.
    lines = _comment(_HEADER)
    for section, parameters in sections.items():
        lines += ["", f"[{section}]"]
        for index, parameter in enumerate(parameters):
            if index > 0:
                lines.append("")
            if parameter.name in first:
                lines += _comment(_ways(first[parameter.name]))
            lines += _comment(parameter.doc)
            lines += _comment(_facts(parameter))
            entry = f"{parameter.name.rpartition('.')[2]} = {_value(parameter.default)}"
            lines.append(f"# {entry}" if parameter.name in commented else entry)
    return "\n".join(lines) + "\n"

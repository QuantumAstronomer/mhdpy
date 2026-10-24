"""The resolution of parameters: the values a run uses, from its declarations, a parameter file and overrides.

The values of a run come in layers, each replacing the values of the layer below it for the parameters it gives: the
declared defaults, then a parameter file, then overrides (PAR06). The defaults suit most runs; a parameter file, in
TOML, holds the choices of one run and is kept with it; overrides vary one or two values without editing the file, for a
parameter scan or a quick test. Overrides come from the command line, as strings such as ``"hydro.cfl=0.3"``, or from
Python, as a dictionary; values in strings are read as TOML, the same as in a parameter file, and a value that is not
valid TOML, such as a bare word, as a string (PAR08).

A restarted run continues the original run: the record of its parameters (PAR19), which the restart file holds, replaces
the defaults as the lowest layer, and the parameter file and the overrides may change only the parameters declared
changeable. The rules of restarts, and the list of what a restart changed, are in ``restarts.py`` (PAR15-PAR17), and are
applied here, as steps among the checks.

A number on its own is a value in code units. A value with a unit, a string such as ``"100 pc"`` given for a number in
any layer, is converted to code units by the unit system of the run (PAR09). It is refused if the run has no unit
system, if the parameter is dimensionless, or if its unit has other dimensions than the parameter's. The unit system is
passed in by the run; this module only asks it for its conversion, and never imports it, nor NumPy behind it (PAR21).

Resolving gives the parameters of the run as one read-only mapping from each name to its value, of its declared type and
in code units, with the value of a list parameter as a tuple, so that no value can be changed once resolved, not even in
place (PAR18). The parameters convert to a record of plain values, every value in code units and the selected groups,
which outputs store as JSON and a restart starts from, exactly (PAR19). These types of what resolving gives, and of the
mistakes it reports, are in ``resolved.py``. The driver (L6) resolves the declarations of all the modules in a run once,
before the run starts, and hands each module the values it declared. Next to the values, the parameters record the
origin of each: the layer it came from, the parameter file by name, and the value as it was given there, such as
``"100 pc"`` (PAR10). The driver logs the values that are not defaults when a run starts, and every mistake is reported
with its origin (PAR14).

Every value is checked against its declaration before the parameters are returned. A name that no module declared is
refused, with the closest declared name as a suggestion where one is close enough to be a likely misspelling, so that
a misspelt parameter never silently leaves its default in place (PAR11). A value must have its parameter's type, with
one conversion only: an integer given for a float becomes a float; a float is never taken for an integer, a boolean
never for a number, and a string never for anything but a string, or a value with a unit for a number (PAR12). A
value must then satisfy its parameter's check, if one is declared, in code units, and is refused with the condition in
the words of the declaration, such as "'hydro.cfl' must be in (0, 1], got 1.5" (PAR13). Before that check, every
float in code units must be finite, neither infinite nor NaN, as standard JSON, the format of the record, has neither
(PAR24). The mistakes are reported together, as one ParameterError that lists each with its origin (PAR14).

Where a quantity can be given in more than one way, the values a run is given select the group of each set of
alternatives: the group of the parameters given in the parameter file or the overrides, and the default group when
none is. The parameters state the selected groups by the names of their sets, in ``selected``, and the module that
declared the alternatives derives the quantity from the group selected. Values given for the parameters of two groups
are refused, among the other mistakes, since one of them would otherwise be silently ignored (PAR22).

Last, the joint checks are evaluated: the conditions on several parameters together, such as an inner radius smaller
than the outer one, on the values in code units. A joint check is evaluated only once every value it involves has
passed its own checks, so that a mistake is never reported twice, and is refused among the other mistakes with its
description and the values involved (PAR23).

For example, a run with a parameter file, one override and a unit system::

    from mhdpy.foundation.parameters.resolution import resolve

    parameters = resolve(declarations, file="run.toml", overrides=["hydro.cfl=0.3"], units=units)
    parameters["hydro.cfl"]                         ## 0.3
    parameters.origins["hydro.cfl"].source          ## "override"

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR06-PAR16,
PAR22-PAR24), and they are tested in ``tests/test_supplying_values.py``, ``tests/test_checks.py``,
``tests/test_restarts.py``, ``tests/test_records.py`` and ``tests/test_alternatives.py``.
"""

import difflib
import math
import os
import tomllib
from collections.abc import Mapping, Sequence, Set
from typing import Any, Protocol, TypeIs

from mhdpy.foundation.parameters.declarations import Alternatives, Declarations, JointCheck, Parameter
from mhdpy.foundation.parameters.resolved import Mistake, Origin, ParameterError, Parameters, Record, given_as
from mhdpy.foundation.parameters.restarts import changes, fixed_mistake, restored
from mhdpy.foundation.parameters.values import element_type, fits, is_finite, is_list, type_name
from mhdpy.foundation.units import notation

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["UnitConverter", "resolve"]


class UnitConverter(Protocol):
    """What resolving needs of a unit system: the conversion of a value with a unit to code units (PAR09, PAR21).

    The unit system of a run, ``mhdpy.foundation.units.system.UnitSystem``, has this method. Asking for the method
    alone, rather than for the unit system itself, keeps this module from importing the unit system, and NumPy behind
    it (PAR21); a type checker still checks that what a run passes in has the method.
    """

    def to_code_units(self, text: str, unit: str | Mapping[str, float]) -> float:
        """Return a value with a unit, such as ``"100 pc"``, in code units of the given unit (UNI20)."""
        ...


def _is_table(value: object) -> TypeIs[Mapping[str, Any]]:
    """Return whether a value is a table of a TOML document, telling the type checker its keys are names."""
    ## TypeIs makes the type checker treat the value as Mapping[str, Any] where this returns True, rather than as a
    ## mapping of keys and values of unknown type, which strict type checking refuses to pass on.
    return isinstance(value, Mapping)


def _flatten(table: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Return the values of a TOML document, or of a dictionary nested like one, by their dotted names (PAR07, PAR08).

    A table and the keys in it give one name each, joined by dots: the key ``cfl`` in the table ``hydro`` gives
    ``"hydro.cfl"``. A dotted key such as ``hydro.cfl`` is read by TOML as the same table and key, and a dotted name
    in a dictionary stays as it is, so every form gives the same names.
    """
    values: dict[str, Any] = {}
    for key, value in table.items():
        name = f"{prefix}{key}"
        ## A table holds further names; anything else is a value, since no parameter takes a table (PAR03).
        if _is_table(value):
            values.update(_flatten(value, f"{name}."))
        else:
            values[name] = value
    return values


def _read_file(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Return the values of a parameter file by their names, refusing a file that is not valid TOML (PAR07)."""
    ## tomllib reads from a file opened in binary mode, as TOML documents are UTF-8 by definition.
    with open(path, "rb") as file:
        try:
            document = tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            ## The reader's message gives the line and column of the error, as "(at line 2, column 5)", but not the
            ## file, which is added. TOMLDecodeError is itself a ValueError, but one only a TOML reader would expect.
            raise ValueError(f"The parameter file {os.fspath(path)} is not valid TOML: {error}.") from error
    return _flatten(document)


def _read_value(text: str) -> Any:
    """Return the value of an override string, read as a TOML value, or as a string if it is not one (PAR08)."""
    ## Read as the value of a one-line TOML document, so that "0.3" is a float and "true" a boolean, as in a file.
    try:
        return tomllib.loads(f"value = {text}")["value"]
    except tomllib.TOMLDecodeError:
        ## A bare word such as "no" is not a TOML value. Taken as a string, without the spaces around it, it is refused
        ## for its type where the parameter is not a string, with a message about the parameter rather than about
        ## TOML syntax (PAR12).
        return text.strip()


def _read_overrides(overrides: Mapping[str, Any] | Sequence[str]) -> dict[str, Any]:
    """Return the values of the overrides by their names, a later override replacing an earlier one (PAR06, PAR08).

    An override string without "=" is refused, naming the string, as is a single string in place of a list of them.
    """
    if isinstance(overrides, Mapping):
        return _flatten(overrides)

    ## A string is itself a sequence of strings, one per character, so that a single override passed without a list
    ## around it would be read character by character, and refused for its first character, which has no "=".
    if isinstance(overrides, str):
        raise TypeError(
            f"The overrides must be a dictionary or a list of strings, such as [{overrides!r}], not a string."
        )

    ## Strings of the form name=value: the name is everything before the first "=", the value everything after it.
    ## Assigning in order makes a later override of the same name replace an earlier one.
    values: dict[str, Any] = {}
    for override in overrides:
        name, equals, text = override.partition("=")
        if not equals:
            raise ValueError(f"The override {override!r} is not of the form name=value, such as 'hydro.cfl=0.3'.")
        values[name.strip()] = _read_value(text)
    return values


def _unknown_name(name: str, origin: Origin, declared: Sequence[str]) -> Mistake:
    """Return the mistake of a name that is not declared, with the closest declared name if one is close (PAR11)."""
    ## difflib compares the names as strings of characters and returns the closest declared one whose similarity, a
    ## number between 0 for nothing in common and 1 for the same name, is at least 0.6: close enough to be a likely
    ## misspelling, as "hydro.cfll" and "hdyro.cfl" are of "hydro.cfl" (E15.2).
    closest = difflib.get_close_matches(name, declared, n=1)
    suggestion = f"; did you mean {closest[0]!r}?" if closest else "."
    return Mistake(name=name, origin=origin, message=f"{name!r} is not a declared parameter{suggestion}")


class _Refusal(Exception):
    """A value refused by the checks of its parameter, or values by those of their alternatives, with the message.

    Raised where a check fails (PAR09, PAR12, PAR13, PAR22), and caught by ``resolve``, which records it as a Mistake,
    so that every mistake is reported together (PAR14). It never leaves this module.
    """


def _convert(parameter: Parameter, value: object, units: UnitConverter | None) -> object:
    """Return a single value of a parameter, of its type, in code units: converted where needed (PAR09, PAR12).

    The value is of the parameter's type already, as checked by ``_resolved_value``.
    """
    ## An integer for a float is the one conversion of types (PAR12): a float, of the same value. type() rather than
    ## isinstance(), as a boolean is an integer to isinstance(), and is refused for a float by the check of the type.
    ## An integer too large for a float, which float() refuses with an OverflowError, becomes an infinity of its sign,
    ## the nearest a float comes to it, and is refused as such (PAR24).
    if type(value) is int and element_type(parameter.type) is float:
        if not is_finite(value):
            return math.inf if value > 0 else -math.inf
        return float(value)

    ## A string given for a number is a value with a unit. A plain number is in code units already, or in kelvin, and a
    ## string for a parameter without a unit, a str, is the value itself.
    if parameter.unit is None or not isinstance(value, str):
        return value

    ## The dimensions of the declared unit, which the declaration has checked (PAR04): none, for a dimensionless
    ## parameter, which takes plain numbers only.
    if not notation.unit_dimensions(parameter.unit):
        raise _Refusal(f"{parameter.name!r} is dimensionless and takes plain numbers only, got {value!r}.")
    if units is None:
        raise _Refusal(
            f"{parameter.name!r} is given {value!r}, a value with a unit, but the run has no unit system to convert it."
        )

    ## The unit system refuses a value whose unit has other dimensions; its message is passed on, after the name of
    ## the parameter.
    try:
        return units.to_code_units(value, parameter.unit)
    except ValueError as error:
        raise _Refusal(f"{parameter.name!r} cannot be given {value!r}: {error}") from error


def _resolved_value(parameter: Parameter, given: object, units: UnitConverter | None) -> object:
    """Return the value of a parameter as modules read it, from the value as given: checked and converted.

    The value must be of the parameter's type (PAR12), and is then converted, a list element by element: an integer
    for a float to a float (PAR12), and a value with a unit to code units (PAR09). A converted float, alone or in a
    list, must be finite (PAR24), and the converted value must then satisfy the parameter's check, if one is declared
    (PAR13). A value that is refused raises a _Refusal with the message of its mistake.
    """
    ## The type first, so that no conversion is tried on a value of the wrong type. The message names the type the
    ## value has, as "got float 4000.0", since the value alone does not always show it: "64" and 64 print alike in
    ## words.
    if not fits(given, parameter.type):
        raise _Refusal(
            f"{parameter.name!r} must be of type {type_name(parameter.type)}, got {type_name(type(given))} {given!r}."
        )
    if is_list(given):
        value = [_convert(parameter, element, units) for element in given]
    else:
        value = _convert(parameter, given, units)

    ## The value as given, shown in a message where it differs from the value in code units.
    as_given = given_as(given, value)

    ## Every float must be finite once converted (PAR24): an infinity or NaN given as such, as TOML writes them, inf and
    ## nan, or one that a conversion gave. Before the check, which a NaN could pass or fail by accident of how its
    ## condition is written.
    elements = value if is_list(value) else [value]
    if any(isinstance(element, float) and not math.isfinite(element) for element in elements):
        raise _Refusal(f"{parameter.name!r} must be finite, got {value!r}{as_given}.")

    ## The check last, on the value in code units, as modules read it (PAR13): a list as a whole, as the condition was
    ## written for.
    if parameter.check is not None and not parameter.check.condition(value):
        raise _Refusal(f"{parameter.name!r} must be {parameter.check.description}, got {value!r}{as_given}.")
    return value


def _kept(parameter: Parameter, value: object, recorded: object, units: UnitConverter | None) -> object:
    """Return the value of a parameter given anew on restart at a value equal to its recorded one: the recorded one.

    Equal values need not be the same: 0.0 and -0.0 compare equal, but differ in their sign bit, so that keeping the
    value given anew would no longer continue the original run bit for bit (PAR16, PAR19). The recorded value is kept,
    as a restored value would be, unless its declaration now refuses it (PAR15); then the value given anew is.
    """
    try:
        return _resolved_value(parameter, recorded, units)
    except _Refusal:
        ## A recorded value of another type, such as 128.0 for what is now an int, equals the value given anew, 128,
        ## only as Python compares numbers; the value given anew is the valid one of the two.
        return value


def _in_words(items: Sequence[str]) -> str:
    """Return items as they are written in a sentence: "a", "a and b", or "a, b and c"."""
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _selected_group(
    alternatives: Alternatives, origins: Mapping[str, Origin], recorded: str | None, fixed: Set[str]
) -> str:
    """Return the group of a set of alternatives that the values given select, refusing values for two (PAR22).

    A group is selected by a value given for any of its parameters, in the parameter file or the overrides. When none
    is, the group recorded by the original run is selected on restart, if it is still one of the groups (PAR15), and
    the default group otherwise. Values given for two groups or more raise a _Refusal that names, for each group, the
    parameters given and where. So does, on restart, a group other than the recorded one, unless no parameter of
    either group is among the fixed ones (PAR16).
    """
    ## The parameters given of each group, by the group's name: only the groups of which any parameter is given. A
    ## default is not given, nor a value restored from the record; the file and the overrides are.
    given = {
        group: [name for name in names if origins[name].source in ("file", "override")]
        for group, names in alternatives.groups.items()
    }
    given = {group: names for group, names in given.items() if names}

    ## The recorded group, if there is one and it is still a group of the set: a set declared since the restart file
    ## was written has none, and a group may have been renamed since (PAR15).
    if recorded not in alternatives.groups:
        recorded = None
    if not given:
        return alternatives.default if recorded is None else recorded
    if len(given) == 1:
        (group,) = given

        ## Another group than the recorded one changes the meaning of the parameters of both, so that every one of
        ## them must be changeable, as for a change of their values (PAR16).
        both = [*alternatives.groups[group], *alternatives.groups[recorded]] if recorded is not None else []
        if group != recorded and not fixed.isdisjoint(both):
            parameters = _in_words([f"{name!r} ({origins[name]})" for name in given[group]])
            raise _Refusal(
                f"{alternatives.name!r} is fixed by the restart file at the group {recorded!r}, got the group "
                f"{group!r} by {parameters}. Another group may be selected on restart only if every parameter of both "
                "groups is changeable."
            )
        return group

    ## Two groups or more: each with the parameters given for it and where, as "'ambient.rho' (override)".
    groups = [
        f"{_in_words([f'{name!r} ({origins[name]})' for name in names])} of the group {group!r}"
        for group, names in given.items()
    ]
    raise _Refusal(
        f"{alternatives.name!r} is given in more than one way: by {'; by '.join(groups)}. Give the parameters of one "
        "group only."
    )


def _joint_mistake(check: JointCheck, values: Mapping[str, Any], origins: Mapping[str, Origin]) -> Mistake | None:
    """Return the mistake of values that do not satisfy a joint check, or None if they do (PAR23).

    The message states the check's description, then each value involved in code units, with its origin, and the
    value as given where it differs, as "'domain.r_inner' = 500.0 (given as '0.5 kpc', override)".
    """
    involved = {name: values[name] for name in check.names}
    if check.condition(involved):
        return None
    described: list[str] = []
    for name, value in involved.items():
        origin = origins[name]
        where = str(origin) if origin.value == value else f"given as {origin.value!r}, {origin}"
        described.append(f"{name!r} = {value!r} ({where})")
    return Mistake(name=None, origin=None, message=f"{check.description}, got {_in_words(described)}.")


def resolve(
    declarations: Declarations,
    *,
    record: Record | None = None,
    file: str | os.PathLike[str] | None = None,
    overrides: Mapping[str, Any] | Sequence[str] = (),
    units: UnitConverter | None = None,
) -> Parameters:
    """Return the parameters of a run, resolved from the declared defaults, a parameter file and overrides (PAR06).

    Each layer replaces the values of the layer below it for the parameters it gives: the defaults, then the file, then
    the overrides, of which a later one replaces an earlier one. A parameter given by no layer keeps its default. A
    parameter file that is not valid TOML is refused with a ValueError, naming the file and the position of the error,
    as is an override string without "=", naming the string. A single override string in place of a list of them is
    refused with a TypeError.

    On restart, the record of the original run replaces the defaults as the lowest layer, for every parameter it holds
    that is still declared, and the group each set of alternatives selected stays selected unless the file or the
    overrides give a parameter of another group (PAR15, PAR22). A declared parameter missing from the record keeps
    its default, and a recorded name that is no longer declared is ignored; a recorded value is checked as any other.
    The file and the overrides may change only the parameters declared changeable, and select another group only if
    every parameter of both groups is: any other change is refused among the mistakes, stating that the restart file
    fixes the value, but a value equal to the recorded one in code units is no change, and leaves the recorded value
    (PAR16). What the restart changed is listed in ``parameters.changes`` (PAR17).

    Every value is then checked against its declaration. A value must be of its parameter's type, and an integer given
    for a float is converted to a float (PAR12). A value with a unit, such as ``"100 pc"``, is converted to code units
    by the unit system, in whichever layer it is given, the default included (PAR09). A float in code units must be
    finite (PAR24), and the value in code units must satisfy the parameter's check, if one is declared (PAR13). The
    mistakes are refused together, with a ParameterError that lists each with its origin (PAR14): a name that no
    parameter is declared by, with the closest declared name where one is close enough to be a likely misspelling
    (PAR11); a value of another type; a value with a unit if there is no unit system, if the parameter is
    dimensionless, or if its unit has other dimensions than the parameter's; a float that is not finite; and a value
    that does not satisfy its check, stating the condition in the words of the declaration.

    Where a quantity can be given in more than one way, the group of each set of alternatives is selected by the values
    given in the file and the overrides, and the default group when none is (PAR22). Values given for two groups are
    refused, among the other mistakes. Last, values that do not satisfy a joint check, a condition on several
    parameters, are refused among the other mistakes, provided each of them has passed its own checks (PAR23).

    Parameters
    ----------
    declarations : Declarations
        The parameters of the run, as declared by its modules.
    record : Record, optional
        On restart, the record of the original run's parameters (PAR19), as its restart file holds it: every value in
        code units, and the selected groups. Without it, the run is not a restart, and the defaults are the lowest
        layer.
    file : str or path, optional
        The parameter file, a TOML document. Without it, no value comes from a file.
    overrides : mapping or sequence of str, optional
        Values that replace those of the file and the defaults: a dictionary, by dotted names or nested as in a TOML
        document, or strings of the form ``"name=value"``, with the value written as in TOML; a value that is not
        valid TOML, such as a bare word, is taken as a string.
    units : unit system, optional
        The unit system of the run, which converts values with a unit to code units: anything with the method
        ``to_code_units`` of ``mhdpy.foundation.units.system.UnitSystem``. Without it, a value with a unit is refused.

    Returns
    -------
    parameters : Parameters
        The value of every declared parameter, by its name, with a list as a tuple, its origin, in
        ``parameters.origins``, the group selected of each set of alternatives, in ``parameters.selected``, and on
        restart what the restart changed, in ``parameters.changes``.
    """
    ## The layers, from the bottom up, each recording the origin of the values it gives, with the value as given: each
    ## replaces the origins of the names it gives, and leaves the others (PAR10).
    origins = {
        parameter.name: Origin(source="default", value=parameter.default) for parameter in declarations.parameters
    }
    if record is not None:
        ## On restart, the record replaces the defaults for every parameter it holds that is still declared (PAR15).
        origins.update(restored(declarations, record))
    if file is not None:
        ## The name as passed, a path turned into its string, as the user wrote it.
        file_name = os.fspath(file)
        for name, value in _read_file(file).items():
            origins[name] = Origin(source="file", value=value, file=file_name)
    for name, value in _read_overrides(overrides).items():
        origins[name] = Origin(source="override", value=value)

    ## Every name the file and the overrides give that no parameter is declared by, in the order they were given: the
    ## names of the defaults come first in the origins, and a new name joins them where it is first given (PAR11).
    declared = [parameter.name for parameter in declarations.parameters]
    mistakes = [_unknown_name(name, origin, declared) for name, origin in origins.items() if name not in declared]

    ## The value of every declared parameter, checked and converted from the value as given once the layers are
    ## combined, so that a default with a unit needs a unit system only if no other layer replaces it (PAR06, PAR09).
    ## A refused value is recorded as a mistake, and the other parameters are still checked, so that every mistake is
    ## reported at once, in the order the parameters were declared (PAR14).
    values: dict[str, Any] = {}
    for parameter in declarations.parameters:
        origin = origins[parameter.name]
        try:
            values[parameter.name] = _resolved_value(parameter, origin.value, units)
        except _Refusal as refusal:
            mistakes.append(Mistake(name=parameter.name, origin=origin, message=str(refusal)))

    ## On restart, a value given anew in the file or the overrides is compared with its recorded value, in code units
    ## (PAR16). A value equal to it is no change, and leaves the recorded value, so that the restart continues bit for
    ## bit (PAR19); a value that differs is refused for a fixed parameter. A parameter missing from the record has no
    ## recorded value (PAR15), and only values that passed their own checks are compared, so that a value that was
    ## refused is reported once, by itself.
    if record is not None:
        for parameter in declarations.parameters:
            name = parameter.name
            origin = origins[name]
            if name not in values or name not in record["values"] or origin.source not in ("file", "override"):
                continue
            original = record["values"][name]
            if values[name] == original:
                values[name] = _kept(parameter, values[name], original, units)
            elif not parameter.changeable:
                mistakes.append(fixed_mistake(parameter, values[name], origin, original))

    ## The group selected of each set of alternatives, from the values given, and on restart from the groups the
    ## original run selected, of which another may be selected only if every parameter of both groups is changeable;
    ## values for two groups are a mistake of several values, with no single origin, reported after those of single
    ## values (PAR15, PAR16, PAR22). Without a restart no group is recorded, so that the fixed parameters do not matter.
    recorded: Mapping[str, str] = record["selected"] if record is not None else {}
    fixed = {parameter.name for parameter in declarations.parameters if not parameter.changeable}
    selected: dict[str, str] = {}
    for alternatives in declarations.alternatives:
        try:
            selected[alternatives.name] = _selected_group(alternatives, origins, recorded.get(alternatives.name), fixed)
        except _Refusal as refusal:
            mistakes.append(Mistake(name=alternatives.name, origin=None, message=str(refusal)))

    ## The joint checks last, on values in code units, and only on values that have passed their own checks: a value
    ## that was refused is reported once, by itself, and not again through a condition it makes fail (PAR23).
    refused = {mistake.name for mistake in mistakes}
    for check in declarations.joint_checks:
        if refused.isdisjoint(check.names):
            mistake = _joint_mistake(check, values, origins)
            if mistake is not None:
                mistakes.append(mistake)

    if mistakes:
        raise ParameterError(mistakes)

    ## On restart, what the restart changed of the original run (PAR17); None for a run that is not a restart.
    changed = changes(declarations, record, values, origins, selected) if record is not None else None
    return Parameters(values, origins, selected, changed)

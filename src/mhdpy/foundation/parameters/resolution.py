"""The resolution of parameters: the values a run uses, from its declarations, a parameter file and overrides.

The values of a run come in layers, each replacing the values of the layer below it for the parameters it gives: the
declared defaults, then a parameter file, then overrides (PAR06). The defaults suit most runs; a parameter file, in
TOML, holds the choices of one run and is kept with it; overrides vary one or two values without editing the file, for a
parameter scan or a quick test. Overrides come from the command line, as strings such as ``"hydro.cfl=0.3"``, or from
Python, as a dictionary; values in strings are read as TOML, the same as in a parameter file, and a value that is not
valid TOML, such as a bare word, as a string (PAR08).

A restarted run continues the original run. The record of the original run's parameters (PAR19), which the restart
file holds, then replaces the defaults as the lowest layer, so that every value not given anew is the one the original
run used, and the group each set of alternatives selected stays selected. A parameter declared since the restart file
was written keeps its default, and a recorded name that is no longer declared is ignored, so that a run can be
continued after its modules were updated; a recorded value that its declaration now refuses is refused with the other
mistakes (PAR15). The parameter file and the overrides may then change only the parameters declared changeable: a new
value for a fixed parameter is refused, since the restart file would no longer describe the run, but a value equal to
the recorded one, compared in code units, is no change, so that the original parameter file can be used unchanged
(PAR16). Likewise, another group of a set of alternatives may be selected only if every parameter of both groups is
changeable (PAR22). What the restart changed is listed with the parameters, for the driver to log and the writers to
record: every value and every selected group that differs from the record, with both, every parameter missing from the
record, with the default it took, and every recorded name that was ignored, with its recorded value (PAR17).

A number on its own is a value in code units. A value with a unit, a string such as ``"100 pc"`` given for a number in
any layer, is converted to code units by the unit system of the run (PAR09). It is refused if the run has no unit
system, if the parameter is dimensionless, or if its unit has other dimensions than the parameter's. The unit system is
passed in by the run; this module only asks it for its conversion, and never imports it, nor NumPy behind it (PAR21).

Resolving gives the parameters of the run as one read-only mapping from each name to its value, of its declared type and
in code units, with the value of a list parameter as a tuple, so that no value can be changed once resolved, not even in
place (PAR18). The parameters convert to a record of plain values, every value in code units and the selected groups,
which outputs store as JSON and a restart starts from, exactly (PAR19). The driver (L6) resolves the declarations of all
the modules in a run once, before the run starts, and hands each module the values it declared. Next to the values, the
parameters record the origin of each: the layer it came from, the parameter file by name, and the value as it was given
there, such as ``"100 pc"`` (PAR10). The driver logs the values that are not defaults when a run starts, and every
mistake is reported with its origin (PAR14).

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

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR06-PAR17,
PAR18-PAR19, PAR22-PAR24), and they are tested in ``tests/test_supplying_values.py``, ``tests/test_checks.py``,
``tests/test_restarts.py``, ``tests/test_records.py`` and ``tests/test_alternatives.py``.
"""

import difflib
import math
import os
import tomllib
from collections.abc import Iterator, Mapping, Sequence, Set
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Literal, Protocol, TypedDict, TypeIs, cast

from mhdpy.foundation.parameters.declarations import Alternatives, Declarations, JointCheck, Parameter
from mhdpy.foundation.parameters.values import element_type, fits, is_finite, is_list, type_name
from mhdpy.foundation.units import notation

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = [
    "Change",
    "Changes",
    "Mistake",
    "Origin",
    "ParameterError",
    "Parameters",
    "Record",
    "UnitConverter",
    "resolve",
]


class UnitConverter(Protocol):
    """What resolving needs of a unit system: the conversion of a value with a unit to code units (PAR09, PAR21).

    The unit system of a run, ``mhdpy.foundation.units.system.UnitSystem``, has this method. Asking for the method
    alone, rather than for the unit system itself, keeps this module from importing the unit system, and NumPy behind
    it (PAR21); a type checker still checks that what a run passes in has the method.
    """

    def to_code_units(self, text: str, unit: str | Mapping[str, float]) -> float:
        """Return a value with a unit, such as ``"100 pc"``, in code units of the given unit (UNI20)."""
        ...


## frozen=True and kw_only=True, as for a declaration: an origin cannot be changed once recorded, and its items are
## given by name, Origin(source="file", value=0.3, file="run.toml").
@dataclass(frozen=True, kw_only=True)
class Origin:
    """Where the value of a parameter came from, and the value as it was given there (PAR10).

    Parameters
    ----------
    source : {"default", "restart", "file", "override"}
        The layer that gave the value: the declared default, the record of the original run on restart (PAR15), the
        parameter file or an override.
    value : bool, int, float, str or list
        The value as it was given, before any conversion: for a value with a unit the string, such as ``"100 pc"``,
        and for a list the whole list. The value in code units is the one the parameters give by name.
    file : str, optional
        The name of the parameter file, as it was passed to ``resolve``, if the value came from it; None otherwise.
    """

    ## A Literal, so that the type checker refuses a comparison with a misspelt layer, such as source == "defaults".
    source: Literal["default", "restart", "file", "override"]
    value: Any
    file: str | None = None

    def __str__(self) -> str:
        """Return where the value came from, in words, as a report of mistakes shows it (PAR14).

        "default", "override", "restart record", or "parameter file" with the file's name, such as "parameter file
        run.toml".
        """
        if self.source == "file":
            return f"parameter file {self.file}"
        return "restart record" if self.source == "restart" else self.source


class Record(TypedDict):
    """The record of a run's parameters: every value in code units, and the selected groups (PAR19).

    What outputs and restart files store of the parameters (D14.2), and what a restart starts from (PAR15). It holds
    plain values only, so that json.dumps writes it as standard JSON, the format D15 records parameters in, and
    json.loads reads it back identically: JSON writes each float with the shortest digits that read back as the same
    double, and every float is finite (PAR24). A TypedDict states the keys of the record and the types of their values
    for the type checker; the record itself is an ordinary dictionary.

    Parameters
    ----------
    values : dict of str to bool, int, float, str or list
        The value of every declared parameter, by its name, in the order declared: in code units (in kelvin, for a
        temperature), after any conversion, and a list as a list, as JSON has no tuples.
    selected : dict of str to str
        The group selected of each set of alternatives, by the name of the set (PAR22).
    """

    values: dict[str, Any]
    selected: dict[str, str]


## frozen=True and kw_only=True, as for an origin: a change cannot be changed once listed, and its items are given by
## name, Change(recorded=0.3, new=0.5).
@dataclass(frozen=True, kw_only=True)
class Change:
    """A value, or a selected group, that a restart changed: the one the record holds and the one resolved now (PAR17).

    Parameters
    ----------
    recorded : bool, int, float, str or tuple
        The value in the record of the original run, in code units, with a list as a tuple; for a set of
        alternatives, the name of the group the original run selected.
    new : bool, int, float, str or tuple
        The value resolved now, in code units, with a list as a tuple; for a set of alternatives, the name of the
        group selected now.
    """

    recorded: Any
    new: Any


## frozen=True and kw_only=True, as for a change, and for the same reasons.
@dataclass(frozen=True, kw_only=True)
class Changes:
    """What a restart changed of the parameters of the original run, as the driver logs it and the writers record it.

    D14.7 requires that the changes made on restart are recorded, in the history's header and in the provenance of
    later files (PAR17). They are listed by name, in the order the parameters and the sets of alternatives were
    declared, and the ignored names in the order the record holds them. Each list is a read-only mapping, so that the
    changes, like the parameters they belong to, cannot be changed once resolved (PAR18).

    Parameters
    ----------
    values : mapping of str to Change
        Every parameter whose value differs from the record, given anew in the parameter file or the overrides (PAR16).
    missing : mapping of str to bool, int, float, str or tuple
        Every declared parameter missing from the record that no other layer gives: the default it took, in code units
        (PAR15).
    ignored : mapping of str to bool, int, float, str or tuple
        Every name in the record that is no longer declared: its recorded value, with a list as a tuple (PAR15).
    selected : mapping of str to Change
        Every set of alternatives whose selected group differs from the group the record holds (PAR22).
    """

    values: Mapping[str, Change]
    missing: Mapping[str, Any]
    ignored: Mapping[str, Any]
    selected: Mapping[str, Change]

    def __post_init__(self) -> None:
        """Keep each list as a read-only mapping of its own, so that the changes cannot be changed once listed."""
        ## object.__setattr__, as the dataclass is frozen and refuses its own assignment even here. A copy behind a
        ## MappingProxyType, so that the changes cannot be changed through the dictionaries they were made from either.
        for name in ("values", "missing", "ignored", "selected"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


def _frozen(value: object) -> object:
    """Return a value as the parameters hold it: a list as a tuple of its elements, anything else as it is (PAR18).

    A tuple cannot be changed in place, and, as a new object, not through the list it was made from either. The
    elements need no copy: they are bools, numbers or strings (PAR03), none of which can be changed.
    """
    return tuple(value) if is_list(value) else value


def _thawed(value: object) -> object:
    """Return a value as the record holds it: a tuple as a list of its elements, anything else as it is (PAR19).

    The reverse of ``_frozen``: JSON has no tuples, and a new list can be changed by a writer of the record without
    changing the parameters.
    """
    ## cast tells the type checker that the elements may be of any type, which isinstance() leaves unknown.
    return list(cast(tuple[object, ...], value)) if isinstance(value, tuple) else value


class Parameters(Mapping[str, Any]):
    """The resolved parameters of a run: each name with its value, read by name and never changed (PAR06, PAR18).

    A mapping, so that a value is read as ``parameters["hydro.cfl"]``, and the names and values can be gone through
    as those of a dictionary. It has no way of changing a value: Mapping, unlike dict, defines no assignment. The value
    of a list parameter is a tuple, which cannot be changed in place either; it is read as a list is, by index and in a
    loop. The origin of each value is recorded next to it, in ``origins`` (PAR10), and the group selected of each set of
    alternatives in ``selected`` (PAR22). On restart, what the restart changed of the original run is listed in
    ``changes`` (PAR17). ``to_record`` gives the record that outputs store and a restart starts from (PAR19).

    Parameters
    ----------
    values : mapping of str to bool, int, float, str or list
        The value of every declared parameter, by its name, in code units and of its declared type.
    origins : mapping of str to Origin
        The origin of each value, by its name.
    selected : mapping of str to str
        The group selected of each set of alternatives, by the name of the set.
    changes : Changes, optional
        On restart, what the restart changed of the parameters of the original run; None for a run that is not a
        restart.
    """

    def __init__(
        self,
        values: Mapping[str, Any],
        origins: Mapping[str, Origin],
        selected: Mapping[str, str],
        changes: Changes | None = None,
    ) -> None:
        ## Copies, so that the parameters cannot be changed through the dictionaries they were made from either, with
        ## every list, of a value or of a value as given, as a tuple of its own (PAR18). The origins and the selected
        ## groups are kept behind a MappingProxyType, a read-only view of a dictionary, since they are handed out as
        ## they are. replace() makes a copy of an origin with the value as given frozen, as an origin itself cannot be
        ## changed.
        self._values = {name: _frozen(value) for name, value in values.items()}
        self._origins = MappingProxyType(
            {name: replace(origin, value=_frozen(origin.value)) for name, origin in origins.items()}
        )
        self._selected = MappingProxyType(dict(selected))
        self._changes = changes

    def __getitem__(self, name: str) -> Any:
        """Return the value of a parameter by its name."""
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        """Go through the names of the parameters, in the order they were declared."""
        return iter(self._values)

    def __len__(self) -> int:
        """Return the number of parameters."""
        return len(self._values)

    @property
    def origins(self) -> Mapping[str, Origin]:
        """The origin of the value of each parameter, by its name: where it came from and how it was given (PAR10)."""
        return self._origins

    @property
    def selected(self) -> Mapping[str, str]:
        """The group selected of each set of alternatives, by the name of the set (PAR22)."""
        return self._selected

    @property
    def changes(self) -> Changes | None:
        """What a restart changed of the parameters of the original run (PAR17); None for a run that is no restart."""
        return self._changes

    def to_record(self) -> Record:
        """Return the record of the parameters: every value in code units, and the selected groups (PAR19).

        The record is written as JSON, by the writers of outputs and restart files, and read back exactly, every float
        bit for bit. Its values are those the parameters give, after conversion, so that a restart never converts them
        again, and cannot be changed by a change of the constants between the original run and its continuation
        (UNI10). The origins are not recorded: they describe how this run was given its values, while on restart every
        value comes from the record (PAR15). Each call returns a record of its own, which a writer may change without
        changing the parameters.
        """
        ## A list value, a tuple in the parameters (PAR18), as a new list. The other values are bools, numbers and
        ## strings, which cannot be changed, and are shared rather than copied.
        values = {name: _thawed(value) for name, value in self._values.items()}
        return {"values": values, "selected": dict(self._selected)}


## frozen=True and kw_only=True, as for an origin: a mistake cannot be changed once found, and its items are given by
## name.
@dataclass(frozen=True, kw_only=True)
class Mistake:
    """A mistake in the values of a run's parameters, found when they are resolved (PAR11-PAR14, PAR22-PAR23).

    Most mistakes are in the value of one parameter, and have its name and the origin of its value. A mistake that
    involves several values, such as values given for two groups of alternatives or values that fail a joint check
    (PAR23), has no single origin, and states the values involved, with their origins, in its message.

    Parameters
    ----------
    name : str or None
        The name the value was given for, declared or not; for values given for two groups of alternatives, the name
        of the alternatives; None for values that fail a joint check.
    origin : Origin or None
        Where the value came from, with the value as it was given there (PAR10); None for a mistake that involves
        several values.
    message : str
        What is wrong and what was expected, in words, starting with the name, such as
        ``"'hydro.cfll' is not a declared parameter; did you mean 'hydro.cfl'?"``.
    """

    name: str | None
    origin: Origin | None
    message: str

    def __str__(self) -> str:
        """Return the mistake as a line of a report: its origin, if it has one, then its message (PAR14)."""
        return f"{self.origin}: {self.message}" if self.origin is not None else self.message


class ParameterError(ValueError):
    """The mistakes in the values of a run's parameters, all reported at once, as one error (PAR14).

    A ValueError, as the values are wrong rather than of a wrong kind of object. Its message lists every mistake on a
    line of its own, with its origin; ``mistakes`` holds them, for a program to go through.

    Parameters
    ----------
    mistakes : sequence of Mistake
        The mistakes, in the order they are reported.
    """

    def __init__(self, mistakes: Sequence[Mistake]) -> None:
        ## A tuple, so that the mistakes cannot be changed once raised.
        self.mistakes = tuple(mistakes)

        ## The message: a heading with the number of mistakes, then each mistake on a line of its own.
        noun = "mistake" if len(self.mistakes) == 1 else "mistakes"
        heading = f"The parameters of the run have {len(self.mistakes)} {noun}:"
        lines = [f"- {mistake}" for mistake in self.mistakes]
        super().__init__("\n".join([heading, *lines]))


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


def _given_as(given: object, value: object) -> str:
    """Return the value as given, for a message, where it differs from the value in code units, or an empty string.

    A value with a unit is shown as it was given as well, as " (given as '100 pc')", so that the user recognises what
    was written; an integer given for a float equals its float, and is not shown twice.
    """
    ## A NaN is not equal even to itself, so a value that was not converted at all is told apart first, as the same
    ## object.
    return "" if given is value or given == value else f" (given as {given!r})"


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
    given_as = _given_as(given, value)

    ## Every float must be finite once converted (PAR24): an infinity or NaN given as such, as TOML writes them, inf and
    ## nan, or one that a conversion gave. Before the check, which a NaN could pass or fail by accident of how its
    ## condition is written.
    elements = value if is_list(value) else [value]
    if any(isinstance(element, float) and not math.isfinite(element) for element in elements):
        raise _Refusal(f"{parameter.name!r} must be finite, got {value!r}{given_as}.")

    ## The check last, on the value in code units, as modules read it (PAR13): a list as a whole, as the condition was
    ## written for.
    if parameter.check is not None and not parameter.check.condition(value):
        raise _Refusal(f"{parameter.name!r} must be {parameter.check.description}, got {value!r}{given_as}.")
    return value


def _changed_fixed(parameter: Parameter, value: object, origin: Origin, recorded: Mapping[str, Any]) -> Mistake | None:
    """Return the mistake of a fixed parameter given a new value on restart, or None if there is none (PAR16).

    Only the parameter file and the overrides can change a value; the value is compared with the recorded one in code
    units, after any conversion, so that a value equal to it is no change, however it is given. A parameter missing
    from the record has no recorded value to keep (PAR15).
    """
    if parameter.changeable or origin.source not in ("file", "override") or parameter.name not in recorded:
        return None
    kept = recorded[parameter.name]
    if value == kept:
        return None
    message = (
        f"{parameter.name!r} is fixed by the restart file at {kept!r}, got {value!r}{_given_as(origin.value, value)}."
    )
    return Mistake(name=parameter.name, origin=origin, message=message)


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


def _changes(
    declarations: Declarations,
    record: Record,
    values: Mapping[str, Any],
    origins: Mapping[str, Origin],
    selected: Mapping[str, str],
) -> Changes:
    """Return what a restart changed of the parameters of the original run, once every value has passed (PAR17).

    A value is compared with the recorded one in code units, as for a fixed parameter (PAR16): a value restored from
    the record is the recorded one, and a value given anew that equals it is no change. Lists are listed as tuples,
    as the parameters hold them (PAR18).
    """
    recorded = record["values"]
    declared = {parameter.name for parameter in declarations.parameters}

    ## Every value that differs from the recorded one, in the order the parameters were declared, as the values are.
    changed = {
        name: Change(recorded=_frozen(recorded[name]), new=_frozen(value))
        for name, value in values.items()
        if name in recorded and value != recorded[name]
    }

    ## Every declared parameter missing from the record that took its default, and not a value of another layer
    ## (PAR15); and every recorded name that is no longer declared, with its recorded value.
    missing = {
        name: _frozen(value)
        for name, value in values.items()
        if name not in recorded and origins[name].source == "default"
    }
    ignored = {name: _frozen(value) for name, value in recorded.items() if name not in declared}

    ## Every set of alternatives whose selected group differs from the recorded one, a recorded group that no longer
    ## exists included; a set missing from the record has no recorded group to differ from (PAR15, PAR22).
    groups = record["selected"]
    switched = {
        name: Change(recorded=groups[name], new=group)
        for name, group in selected.items()
        if name in groups and groups[name] != group
    }
    return Changes(values=changed, missing=missing, ignored=ignored, selected=switched)


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
    fixes the value, but a value equal to the recorded one in code units is no change (PAR16). What the restart
    changed is listed in ``parameters.changes`` (PAR17).

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
        ## On restart, the record replaces the defaults for every parameter it holds that is still declared, which are
        ## the only names in the origins so far. A parameter missing from the record keeps its default, and a recorded
        ## name that is no longer declared is ignored, rather than refused as an unknown name, so that a run can be
        ## continued after its modules were updated (PAR15).
        for name, value in record["values"].items():
            if name in origins:
                origins[name] = Origin(source="restart", value=value)
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

    ## On restart, a value given anew for a fixed parameter must equal its recorded value (PAR16). Only values that
    ## passed their own checks are compared, so that a value that was refused is reported once, by itself.
    if record is not None:
        for parameter in declarations.parameters:
            if parameter.name in values:
                origin = origins[parameter.name]
                mistake = _changed_fixed(parameter, values[parameter.name], origin, record["values"])
                if mistake is not None:
                    mistakes.append(mistake)

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
    changes = _changes(declarations, record, values, origins, selected) if record is not None else None
    return Parameters(values, origins, selected, changes)

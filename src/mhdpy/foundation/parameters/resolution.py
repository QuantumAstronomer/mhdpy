"""The resolution of parameters: the values a run uses, from its declarations, a parameter file and overrides.

The values of a run come in layers, each replacing the values of the layer below it for the parameters it gives: the
declared defaults, then a parameter file, then overrides (PAR06). The defaults suit most runs; a parameter file, in
TOML, holds the choices of one run and is kept with it; overrides vary one or two values without editing the file, for a
parameter scan or a quick test. Overrides come from the command line, as strings such as ``"hydro.cfl=0.3"``, or from
Python, as a dictionary; values in strings are read as TOML, the same as in a parameter file, and a value that is not
valid TOML, such as a bare word, as a string (PAR08).

A number on its own is a value in code units. A value with a unit, a string such as ``"100 pc"`` given for a number in
any layer, is converted to code units by the unit system of the run (PAR09). It is refused if the run has no unit
system, if the parameter is dimensionless, or if its unit has other dimensions than the parameter's. The unit system is
passed in by the run; this module only asks it for its conversion, and never imports it, nor NumPy behind it (PAR21).

Resolving gives the parameters of the run as one read-only mapping from each name to its value. The driver (L6)
resolves the declarations of all the modules in a run once, before the run starts, and hands each module the values it
declared. Next to the values, the parameters record the origin of each: the layer it came from, the parameter file by
name, and the value as it was given there, such as ``"100 pc"`` (PAR10). The driver logs the values that are not
defaults when a run starts, and every mistake is reported with its origin (PAR14).

Every value is checked against its declaration before the parameters are returned. A name that no module declared is
refused, with the closest declared name as a suggestion where one is close enough to be a likely misspelling, so that
a misspelt parameter never silently leaves its default in place (PAR11). The mistakes are reported together, as one
ParameterError that lists each with its origin (PAR14).

For example, a run with a parameter file, one override and a unit system::

    from mhdpy.foundation.parameters.resolution import resolve

    parameters = resolve(declarations, file="run.toml", overrides=["hydro.cfl=0.3"], units=units)
    parameters["hydro.cfl"]                         ## 0.3
    parameters.origins["hydro.cfl"].source          ## "override"

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR06-PAR14), and they
are tested in ``tests/test_supplying_values.py`` and ``tests/test_checks.py``.
"""

import difflib
import os
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, Protocol, TypeIs

from mhdpy.foundation.parameters.declarations import Declarations, Parameter
from mhdpy.foundation.parameters.values import is_list
from mhdpy.foundation.units import notation

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["Mistake", "Origin", "ParameterError", "Parameters", "UnitConverter", "resolve"]


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
    source : {"default", "file", "override"}
        The layer that gave the value: the declared default, the parameter file or an override.
    value : bool, int, float, str or list
        The value as it was given, before any conversion: for a value with a unit the string, such as ``"100 pc"``,
        and for a list the whole list. The value in code units is the one the parameters give by name.
    file : str, optional
        The name of the parameter file, as it was passed to ``resolve``, if the value came from it; None otherwise.
    """

    ## A Literal, so that the type checker refuses a comparison with a misspelt layer, such as source == "defaults".
    ## The restart record joins the layers with the restarts (PAR15).
    source: Literal["default", "file", "override"]
    value: Any
    file: str | None = None

    def __str__(self) -> str:
        """Return where the value came from, in words, as a report of mistakes shows it (PAR14).

        "default", "override", or "parameter file" with the file's name, such as "parameter file run.toml".
        """
        return f"parameter file {self.file}" if self.source == "file" else self.source


class Parameters(Mapping[str, Any]):
    """The resolved parameters of a run: each name with its value, read by name and never changed (PAR06, PAR18).

    A mapping, so that a value is read as ``parameters["hydro.cfl"]``, and the names and values can be gone through
    as those of a dictionary. It has no way of changing a value: Mapping, unlike dict, defines no assignment. The
    origin of each value is recorded next to it, in ``origins`` (PAR10).
    """

    def __init__(self, values: Mapping[str, Any], origins: Mapping[str, Origin]) -> None:
        ## Copies, so that the parameters cannot be changed through the dictionaries they were made from either. The
        ## origins are kept behind a MappingProxyType, a read-only view of a dictionary, since they are handed out
        ## as they are.
        self._values = dict(values)
        self._origins = MappingProxyType(dict(origins))

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


## frozen=True and kw_only=True, as for an origin: a mistake cannot be changed once found, and its items are given by
## name.
@dataclass(frozen=True, kw_only=True)
class Mistake:
    """A mistake in the value of a parameter, found when the parameters of a run are resolved (PAR11-PAR14).

    Parameters
    ----------
    name : str
        The name the value was given for, declared or not.
    origin : Origin
        Where the value came from, with the value as it was given there (PAR10).
    message : str
        What is wrong and what was expected, in words, starting with the name, such as
        ``"'hydro.cfll' is not a declared parameter; did you mean 'hydro.cfl'?"``.
    """

    name: str
    origin: Origin
    message: str

    def __str__(self) -> str:
        """Return the mistake as a line of a report: its origin, then its message (PAR14)."""
        return f"{self.origin}: {self.message}"


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


def _convert(parameter: Parameter, value: object, units: UnitConverter | None) -> object:
    """Return a single value of a parameter in code units: a value with a unit converted, any other as it is (PAR09)."""
    ## A string given for a number is a value with a unit. A plain number is in code units already, or in kelvin, and a
    ## string for a parameter without a unit, a bool or a str, is the value itself.
    if parameter.unit is None or not isinstance(value, str):
        return value

    ## The dimensions of the declared unit, which the declaration has checked (PAR04): none, for a dimensionless
    ## parameter, which takes plain numbers only.
    if not notation.unit_dimensions(parameter.unit):
        raise ValueError(f"{parameter.name!r} is dimensionless and takes plain numbers only, got {value!r}.")
    if units is None:
        raise ValueError(
            f"{parameter.name!r} is given {value!r}, a value with a unit, but the run has no unit system to convert it."
        )

    ## The unit system refuses a value whose unit has other dimensions, or that is not a value with a unit at all;
    ## its message is passed on with the name of the parameter.
    try:
        return units.to_code_units(value, parameter.unit)
    except ValueError as error:
        raise ValueError(f"The value of {parameter.name!r} is invalid. {error}") from error


def _to_code_units(parameter: Parameter, value: object, units: UnitConverter | None) -> object:
    """Return the value of a parameter in code units, a list converted element by element (PAR09)."""
    if is_list(value):
        return [_convert(parameter, element, units) for element in value]
    return _convert(parameter, value, units)


def resolve(
    declarations: Declarations,
    *,
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

    A name that no parameter is declared by is refused with a ParameterError, which lists every such name with its
    origin, and with the closest declared name where one is close enough to be a likely misspelling (PAR11, PAR14).

    A value with a unit, such as ``"100 pc"``, is converted to code units by the unit system, in whichever layer it is
    given, the default included. It is refused with a ValueError, naming the parameter, if there is no unit system, if
    the parameter is dimensionless, or if its unit has other dimensions than the parameter's.

    Parameters
    ----------
    declarations : Declarations
        The parameters of the run, as declared by its modules.
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
        The value of every declared parameter, by its name, and its origin, in ``parameters.origins``.
    """
    ## The layers, from the bottom up, each recording the origin of the values it gives, with the value as given: each
    ## replaces the origins of the names it gives, and leaves the others (PAR10).
    origins = {
        parameter.name: Origin(source="default", value=parameter.default) for parameter in declarations.parameters
    }
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
    if mistakes:
        raise ParameterError(mistakes)

    ## The values, from the values as given, those with a unit converted once the layers are combined, so that a
    ## default with a unit needs a unit system only if no other layer replaces it (PAR06, PAR09).
    values = {name: origin.value for name, origin in origins.items()}
    for parameter in declarations.parameters:
        values[parameter.name] = _to_code_units(parameter, values[parameter.name], units)
    return Parameters(values, origins)

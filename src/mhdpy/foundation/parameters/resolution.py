"""The resolution of parameters: the values a run uses, from its declarations, a parameter file and overrides.

The values of a run come in layers, each replacing the values of the layer below it for the parameters it gives: the
declared defaults, then a parameter file, then overrides (PAR06). The defaults suit most runs; a parameter file, in
TOML, holds the choices of one run and is kept with it; overrides vary one or two values without editing the file, for a
parameter scan or a quick test. Overrides come from the command line, as strings such as ``"hydro.cfl=0.3"``, or from
Python, as a dictionary; values in strings are read as TOML, the same as in a parameter file (PAR08).

Resolving gives the parameters of the run as one read-only mapping from each name to its value. The driver (L6)
resolves the declarations of all the modules in a run once, before the run starts, and hands each module the values it
declared.

For example, a run with a parameter file and one override::

    from mhdpy.foundation.parameters.resolution import resolve

    parameters = resolve(declarations, file="run.toml", overrides=["hydro.cfl=0.3"])
    parameters["hydro.cfl"]                         ## 0.3

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR06-PAR10), and they
are tested in ``tests/test_supplying_values.py``.
"""

import os
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, TypeIs

from mhdpy.foundation.parameters.declarations import Declarations

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["Parameters", "resolve"]


class Parameters(Mapping[str, Any]):
    """The resolved parameters of a run: each name with its value, read by name and never changed (PAR06, PAR18).

    A mapping, so that a value is read as ``parameters["hydro.cfl"]``, and the names and values can be gone through
    as those of a dictionary. It has no way of changing a value: Mapping, unlike dict, defines no assignment.
    """

    def __init__(self, values: Mapping[str, Any]) -> None:
        ## A copy, so that the parameters cannot be changed through the dictionary they were made from either.
        self._values = dict(values)

    def __getitem__(self, name: str) -> Any:
        """Return the value of a parameter by its name."""
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        """Go through the names of the parameters, in the order they were declared."""
        return iter(self._values)

    def __len__(self) -> int:
        """Return the number of parameters."""
        return len(self._values)


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


def _read_overrides(overrides: Mapping[str, Any] | Sequence[str]) -> dict[str, Any]:
    """Return the values of the overrides by their names, a later override replacing an earlier one (PAR06, PAR08)."""
    if isinstance(overrides, Mapping):
        return _flatten(overrides)

    ## Strings of the form name=value: the name is everything before the first "=", the value everything after it,
    ## read as the value of a one-line TOML document, so that "0.3" is a float and "true" a boolean, as in a file.
    ## Assigning in order makes a later override of the same name replace an earlier one.
    values: dict[str, Any] = {}
    for override in overrides:
        name, _, text = override.partition("=")
        values[name.strip()] = tomllib.loads(f"value = {text}")["value"]
    return values


def resolve(
    declarations: Declarations,
    *,
    file: str | os.PathLike[str] | None = None,
    overrides: Mapping[str, Any] | Sequence[str] = (),
) -> Parameters:
    """Return the parameters of a run, resolved from the declared defaults, a parameter file and overrides (PAR06).

    Each layer replaces the values of the layer below it for the parameters it gives: the defaults, then the file, then
    the overrides, of which a later one replaces an earlier one. A parameter given by no layer keeps its default. A
    parameter file that is not valid TOML is refused with a ValueError, naming the file and the position of the error.

    Parameters
    ----------
    declarations : Declarations
        The parameters of the run, as declared by its modules.
    file : str or path, optional
        The parameter file, a TOML document. Without it, no value comes from a file.
    overrides : mapping or sequence of str, optional
        Values that replace those of the file and the defaults: a dictionary, by dotted names or nested as in a TOML
        document, or strings of the form ``"name=value"``, with the value written as in TOML.

    Returns
    -------
    parameters : Parameters
        The value of every declared parameter, by its name.
    """
    ## The layers, from the bottom up: each update replaces the values of the names it gives, and leaves the others.
    values = {parameter.name: parameter.default for parameter in declarations.parameters}
    if file is not None:
        values.update(_read_file(file))
    values.update(_read_overrides(overrides))
    return Parameters(values)

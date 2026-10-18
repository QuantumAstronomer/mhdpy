"""The types of the values of parameters: which types a parameter may have, and when a value is of its type.

A parameter's values are of one of four types, bool, int, float and str, or a list of one of them (PAR03): exactly the
types TOML writes without ambiguity and JSON records exactly, so that every value survives a parameter file and a record
unchanged (PAR19, PAR20). Whether a value is of its parameter's type is decided by the same rules everywhere: for a
default when a parameter is declared (PAR03), and for every value a run is given when its parameters are resolved
(PAR12). An integer is accepted for a float, and a string for a number only if it is a value with a unit, such as
``"100 pc"`` (PAR09); a boolean is never accepted for a number, nor a float for an integer.

The rules live in this module of their own, rather than in either of the modules that apply them, so that the
declarations (``declarations.py``) and the resolution (``resolution.py``) share one copy. Like the rest of the
component, it depends on nothing beyond the standard library and the notation of units (PAR21).

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR03, PAR12), and they
are tested through the modules that apply them, in ``tests/test_declarations.py`` and ``tests/test_checks.py``.
"""

from types import GenericAlias
from typing import TypeIs, get_args, get_origin

from mhdpy.foundation.units import notation

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["element_type", "fits", "is_list", "type_name"]

## The four types of PAR03 a value, or every element of a list, may have: exactly those TOML writes without ambiguity
## and JSON records exactly.
_SCALARS = (bool, int, float, str)


def element_type(type_: type | GenericAlias) -> type | None:
    """Return the type of a parameter's single values: the type itself, or the type of a list's elements (PAR03).

    None means that the type is not one of PAR03: neither one of the four types, nor a list of one of them.
    """
    ## get_origin(list[float]) is list and get_args(list[float]) is (float,); for list itself, without the type of its
    ## elements, get_origin is None. Comparing the arguments with (scalar,) refuses list[int | str] and list[int, str].
    for scalar in _SCALARS:
        if type_ is scalar or (get_origin(type_) is list and get_args(type_) == (scalar,)):
            return scalar
    return None


def type_name(type_: object) -> str:
    """Return the name of a type as it is written in Python, such as ``float`` or ``list[float]``, for messages."""
    ## A generic type such as list[float] is written by str(); its __name__ would be "list" alone.
    return str(type_) if isinstance(type_, GenericAlias) else getattr(type_, "__name__", repr(type_))


def is_list(value: object) -> TypeIs[list[object]]:
    """Return whether a value is a list, telling the type checker that its elements may be of any type."""
    ## TypeIs makes the type checker treat the value as list[object] where this returns True, rather than as a list of
    ## elements of unknown type, which strict type checking refuses to iterate over.
    return isinstance(value, list)


def _has_unit(text: str) -> bool:
    """Return whether a string is a value with a unit (UNI19), such as ``"100 pc"``."""
    try:
        notation.parse(text)
    except ValueError:
        return False
    return True


def _of_type(value: object, scalar: type | None) -> bool:
    """Return whether a single value is of one of the four types of PAR03, by the rules of PAR12.

    An integer is accepted for a float, and a string only if it is a value with a unit (PAR09); a boolean is accepted
    for nothing but a bool, and a float is not accepted for an int even when its value is whole. A scalar of None, for
    a type that is not one of PAR03, accepts no value at all.
    """
    ## bool is a subclass of int in Python, so True would pass for an integer: it is told apart first.
    if isinstance(value, bool):
        return scalar is bool
    if scalar is float:
        return isinstance(value, int | float) or (isinstance(value, str) and _has_unit(value))

    ## For the others the type must be exactly the declared one: type(64.0) is float, not int.
    return type(value) is scalar


def fits(value: object, type_: type | GenericAlias) -> bool:
    """Return whether a value is of its parameter's type: a single value, or a list whose every element is (PAR03).

    The rules are those of PAR12, the same for a default when a parameter is declared and for every value a run is
    given.
    """
    scalar = element_type(type_)
    if get_origin(type_) is not list:
        return _of_type(value, scalar)

    ## A list takes a list only, not a tuple or a single value, and every one of its elements is checked alike.
    return is_list(value) and all(_of_type(element, scalar) for element in value)

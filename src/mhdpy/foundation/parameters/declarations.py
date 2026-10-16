"""The declarations of parameters: what a module states about each parameter it needs.

A parameter exists in mhdpy because a module declares it (D12.1, D15.2). Its declaration states everything the rest of
mhdpy needs to know about it: its name, the type of its values, its value when nobody sets it, what it means, its unit,
optionally a condition every value must satisfy, and whether it may change when a run is restarted (PAR01). Users never
introduce parameters of their own; they only give values to declared ones, which is what makes it possible to refuse a
misspelt name instead of silently ignoring it (PAR11).

A declaration is checked as soon as it is made, so that a mistake in it is found in the module that made it, by that
module's own tests, rather than in a user's run.

For example, the Courant number of the hydrodynamics::

    from mhdpy.foundation.parameters.declarations import Check, Parameter

    cfl = Parameter(
        name="hydro.cfl",
        type=float,
        default=0.4,
        doc="The Courant number: the time step as a fraction of the time a signal takes to cross a cell.",
        unit="dimensionless",
        check=Check(lambda value: 0 < value <= 1, "in (0, 1]"),
        changeable=True,
    )

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR01-PAR05), and they
are tested in ``tests/test_declarations.py``.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import GenericAlias
from typing import Any

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["Check", "Parameter"]


## frozen=True: a check cannot be changed once made, like the declaration it belongs to. A dataclass rather than a
## NamedTuple, because a type checker reads the type of a lambda's argument from the constructor of a dataclass, but
## not from that of a NamedTuple, and would report every check written as a lambda as untyped.
@dataclass(frozen=True)
class Check:
    """A condition every value of a parameter must satisfy, with its description in words (PAR01).

    The condition is a function of the value in code units that returns whether the value is acceptable. The
    description is what an error message states as the expected condition, as in "'hydro.cfl' must be in (0, 1], got
    1.5" (PAR13), since the function itself cannot be shown to a user.
    """

    condition: Callable[[Any], bool]
    description: str


## frozen=True: a declaration cannot be changed once made, so that what was checked when it was made stays true.
## kw_only=True: every item is given by name, Parameter(name=..., type=..., default=...), so that a declaration reads as
## what it states and its items cannot be mixed up by their order.
@dataclass(frozen=True, kw_only=True)
class Parameter:
    """The declaration of a parameter: everything mhdpy needs to know about it (PAR01).

    Parameters
    ----------
    name : str
        The name of the parameter: two or more parts separated by dots, the first naming the module that declares it,
        as ``"hydro.cfl"`` or ``"output.snapshot.dt"``.
    type : type
        The type of its values, written as in Python: ``bool``, ``int``, ``float`` or ``str``, or a list of one of
        these, such as ``list[float]``.
    default : bool, int, float, str or list
        The value of the parameter when no parameter file or override gives one. Every parameter has a default, so that
        a run can always start. The default of a number may also be given with a unit, as a string such as
        ``"100 pc"``; it is converted to code units when the parameters of a run are resolved.
    doc : str
        What the parameter means, in words, as templates and the reference documentation show it.
    unit : str or mapping, optional
        What the values of the parameter are measured in. A plain number given for the parameter is always a value in
        code units (in kelvin, for a temperature); the unit is what lets a value also be given with a unit of its own,
        such as ``"100 pc"``, which is then checked for its dimensions and converted to code units. Parameters of type
        ``int`` and ``float``, and lists of them, declare a unit; parameters of type ``bool`` and ``str`` have none. A
        unit takes one of three forms:

        - ``"dimensionless"``, for a pure number such as a Courant number or an adiabatic index. Parameters of type
          ``int`` are always dimensionless, as they count things: cells, blocks or steps.
        - The name of a unit of the unit system, such as ``"length"``, ``"density"`` or ``"magnetic_field"``. The
          magnetic field is declared this way, because its code unit contains the factor sqrt(4 pi), which its
          dimensions do not show.
        - Dimensions, as the exponents of length, mass, time and temperature, for a quantity without a named unit:
          ``{"length": 2, "time": -1}`` for a diffusivity, or ``{"temperature": 1}`` for a temperature, which stays in
          kelvin.
    check : Check, optional
        A condition every value must satisfy, with its description in words, such as
        ``Check(lambda value: 0 < value <= 1, "in (0, 1]")``. It applies to the value in code units.
    changeable : bool, optional
        Whether the value may change when a run is restarted. ``False`` by default: a parameter is fixed unless it is
        declared changeable.
    """

    ## The default has no default of its own, so a declaration without one is refused by Python itself, with a
    ## TypeError, and marked by the type checker as soon as it is written (PAR01). Any, because a default may be of
    ## any of the types of PAR03, or a string with a unit for a number (PAR09); the type is checked against the
    ## declared one when the declaration is made.
    name: str
    type: type | GenericAlias
    default: Any
    doc: str
    unit: str | Mapping[str, float] | None = None
    check: Check | None = None
    changeable: bool = False

    def __post_init__(self) -> None:
        """Refuse a declaration that breaks the rules of PAR01-PAR05, naming the parameter.

        A dataclass calls this method at the end of its constructor, so no declaration that breaks them can exist. A
        type that breaks the rules of PAR03 is refused with a TypeError, as Python refuses values of the wrong type;
        every other broken rule with a ValueError.
        """
        ## The documentation is what templates and the reference documentation show of a parameter (PAR20). An empty
        ## one, or one of spaces only, documents nothing.
        if not self.doc.strip():
            raise ValueError(f"The declaration of {self.name!r} has no documentation.")

        ## A check must say in words what it expects, or its error messages could not (PAR01, PAR13). An empty
        ## description, or one of spaces only, says nothing.
        if self.check is not None and not self.check.description.strip():
            raise ValueError(f"The check of {self.name!r} has no description in words, such as 'in (0, 1]'.")

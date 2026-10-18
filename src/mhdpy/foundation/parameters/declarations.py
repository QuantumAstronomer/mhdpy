"""The declarations of parameters: what a module states about each parameter it needs.

A parameter exists in mhdpy because a module declares it (D12.1, D15.2). Its declaration states everything the rest of
mhdpy needs to know about it: its name, the type of its values, its value when nobody sets it, what it means, its unit,
optionally a condition every value must satisfy, and whether it may change when a run is restarted (PAR01). Users never
introduce parameters of their own; they only give values to declared ones, which is what makes it possible to refuse a
misspelt name instead of silently ignoring it (PAR11).

A declaration is checked as soon as it is made, so that a mistake in it is found in the module that made it, by that
module's own tests, rather than in a user's run. The declarations of all the modules in a run are then gathered into
one set, which is checked as a whole: no name may be declared twice, or be the start of another (PAR05).

A quantity that can be given in more than one way is declared as alternatives: named groups of declared parameters,
each of which gives the quantity, one of them the default, such as the density of the ambient medium as a mass density
or from a number density, a temperature and a metallicity (PAR22). Which group a run uses is decided when its
parameters are resolved, by the values it is given; the alternatives are checked with the set they belong to, since
only the set knows which parameters are declared.

For example, the Courant number of the hydrodynamics::

    from mhdpy.foundation.parameters.declarations import Check, Declarations, Parameter

    cfl = Parameter(
        name="hydro.cfl",
        type=float,
        default=0.4,
        doc="The Courant number: the time step as a fraction of the time a signal takes to cross a cell.",
        unit="dimensionless",
        check=Check(lambda value: 0 < value <= 1, "in (0, 1]"),
        changeable=True,
    )
    declarations = Declarations(parameters=[cfl, ...])

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR01-PAR05, PAR22),
and they are tested in ``tests/test_declarations.py`` and ``tests/test_alternatives.py``.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import GenericAlias, MappingProxyType
from typing import Any

from mhdpy.foundation.parameters.values import element_type, fits, is_list, type_name
from mhdpy.foundation.units import notation

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["Alternatives", "Check", "Declarations", "Parameter"]

## The form of a name (PAR02), as a regular expression: a part, then one or more parts each after a dot. A part is a
## lowercase letter or an underscore, followed by any number of lowercase letters, digits and underscores: a lowercase
## Python identifier, in ASCII only, which makes every part a bare key in TOML and a section on the command line without
## quoting. Python's own str.isidentifier would also accept letters outside ASCII, which TOML does not.
_NAME = re.compile(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+")


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
        ## The name comes first, since every other message names the parameter by it. fullmatch requires the whole
        ## name to have the form, so that "hydro.cfl." is refused rather than read up to its last dot.
        if not _NAME.fullmatch(self.name):
            raise ValueError(
                f"The name {self.name!r} is not lowercase identifiers joined by dots, such as 'hydro.cfl'."
            )

        ## The documentation is what templates and the reference documentation show of a parameter (PAR20). An empty
        ## one, or one of spaces only, documents nothing.
        if not self.doc.strip():
            raise ValueError(f"The declaration of {self.name!r} has no documentation.")

        ## A check must say in words what it expects, or its error messages could not (PAR01, PAR13). An empty
        ## description, or one of spaces only, says nothing.
        if self.check is not None and not self.check.description.strip():
            raise ValueError(f"The check of {self.name!r} has no description in words, such as 'in (0, 1]'.")

        ## The type must be one of PAR03, and the default of that type. Both are refused with a TypeError, as Python
        ## refuses a value of the wrong type.
        scalar = element_type(self.type)
        if scalar is None:
            raise TypeError(
                f"The type {type_name(self.type)} of {self.name!r} is not bool, int, float, str or a list of one."
            )

        ## The unit (PAR04): every number declares one, an integer is dimensionless, and a bool or str has none. The
        ## notation finds the dimensions of the unit and refuses one of none of the three forms, such as a misspelt
        ## named unit or dimension, without the unit system (PAR21).
        dimensions: dict[str, float] = {}
        if scalar not in (int, float):
            if self.unit is not None:
                raise ValueError(
                    f"{self.name!r} is of type {type_name(self.type)}, which has no unit, got {self.unit!r}."
                )
        else:
            if self.unit is None:
                raise ValueError(
                    f"{self.name!r} is a number and needs a unit: 'dimensionless', a named unit such as 'density', "
                    "or dimensions such as {'length': 1}."
                )
            try:
                dimensions = notation.unit_dimensions(self.unit)
            except ValueError as error:
                raise ValueError(f"The unit of {self.name!r} is invalid. {error}") from error
            if scalar is int and dimensions:
                raise ValueError(
                    f"{self.name!r} is an integer, which counts things and is dimensionless, but has the unit "
                    f"{self.unit!r}."
                )

        if not fits(self.default, self.type):
            raise TypeError(
                f"The default {self.default!r} of {self.name!r} is not of its type, {type_name(self.type)}."
            )

        ## A default given with a unit, a string for a float, alone or in a list, must have the dimensions of the
        ## parameter's unit, which the notation finds without the unit system (PAR03, PAR21).
        values = self.default if is_list(self.default) else [self.default]
        texts = [value for value in values if isinstance(value, str)] if scalar is float else []
        for text in texts:
            found = notation.dimensions(notation.parse(text)[1])
            if found != dimensions:
                raise ValueError(
                    f"The default {text!r} of {self.name!r} has the dimensions {found}, not those of its unit "
                    f"{self.unit!r}, {dimensions}."
                )

        ## The check applies to a plain default now. A default given with a unit is checked when the parameters are
        ## resolved: the condition applies in code units, and a declaration knows no unit system (PAR13).
        if self.check is not None and not texts and not self.check.condition(self.default):
            raise ValueError(f"The default of {self.name!r} must be {self.check.description}, got {self.default!r}.")


## frozen=True and kw_only=True, as for a declaration: the alternatives cannot be changed once checked, and their items
## are given by name.
@dataclass(frozen=True, kw_only=True)
class Alternatives:
    """A quantity that can be given in more than one way: two or more named groups of parameters (PAR22).

    Each group gives the quantity on its own, and one of them is the default. A run selects a group by giving a value
    for any of its parameters, and the default group by giving none; giving values for two groups is refused. The
    alternatives are checked when made for what they state themselves, and with the set they are gathered in
    (``Declarations``) for the parameters they name.

    Parameters
    ----------
    name : str
        The name of the quantity, in the form of a parameter's name (PAR02), such as ``"ambient.density"``: the name
        the resolved parameters state the selected group by.
    doc : str
        What the quantity is, and the ways it can be given, in words, as templates show it (PAR20).
    groups : mapping of str to sequence of str
        Each group by its name, with the names of its parameters: at least two groups, none of them empty, such as
        ``{"mass_density": ["ambient.rho"], "number_density": ["ambient.n", "ambient.temperature"]}``.
    default : str
        The name of the group selected when no parameter of any group is given.
    """

    name: str
    doc: str
    groups: Mapping[str, Sequence[str]]
    default: str

    def __post_init__(self) -> None:
        """Refuse alternatives that break the rules of PAR22 they state themselves, naming them, and keep them fixed.

        The groups are kept as a read-only mapping of tuples, so that they cannot be changed through what they were
        given as either.
        """
        ## The name, as a parameter's (PAR02), since it is written where names are: in the record and the templates.
        if not _NAME.fullmatch(self.name):
            raise ValueError(
                f"The name {self.name!r} of alternatives is not lowercase identifiers joined by dots, such as "
                "'ambient.density'."
            )
        if not self.doc.strip():
            raise ValueError(f"The alternatives {self.name!r} have no documentation.")
        object.__setattr__(
            self, "groups", MappingProxyType({group: tuple(names) for group, names in self.groups.items()})
        )

        ## A single group offers no alternative, and an empty group could not be selected by giving a value, nor give
        ## the quantity.
        if len(self.groups) < 2:
            raise ValueError(f"The alternatives {self.name!r} need at least two groups, got {list(self.groups)}.")
        for group, names in self.groups.items():
            if not names:
                raise ValueError(f"The group {group!r} of the alternatives {self.name!r} has no parameters.")
        if self.default not in self.groups:
            raise ValueError(
                f"The default {self.default!r} of the alternatives {self.name!r} is not one of its groups, "
                f"{list(self.groups)}."
            )


## frozen=True and kw_only=True, as for a declaration: the set cannot be changed once checked, and its items are given
## by name, Declarations(parameters=[...], alternatives=[...]).
@dataclass(frozen=True, kw_only=True)
class Declarations:
    """The parameters of a run, declared together as one set, with their alternatives (PAR05, PAR22).

    Parameters
    ----------
    parameters : sequence of Parameter
        The declarations of every module in the run, in the order they were made. No name may be declared twice, and
        no name may be the start of another, as ``"output.snapshot"`` is of ``"output.snapshot.dt"``.
    alternatives : sequence of Alternatives, optional
        The quantities that can be given in more than one way. Every parameter their groups name must be declared, and
        may be in one group only; no name may be given to two sets of alternatives. None by default.
    """

    parameters: Sequence[Parameter]
    alternatives: Sequence[Alternatives] = ()

    def __post_init__(self) -> None:
        """Refuse a set that breaks the rules of PAR05 or PAR22, naming what is involved, and keep it as tuples.

        Tuples, so that the set cannot be changed through the lists it was given as either.
        """
        object.__setattr__(self, "parameters", tuple(self.parameters))
        object.__setattr__(self, "alternatives", tuple(self.alternatives))

        ## A name declared twice, by two modules or by one: the two would compete for its value, and one would silently
        ## get a value meant for the other. The documentation of both tells a user which declarations they are.
        by_name: dict[str, Parameter] = {}
        for parameter in self.parameters:
            if parameter.name in by_name:
                first = by_name[parameter.name]
                raise ValueError(f"{parameter.name!r} is declared twice: as {first.doc!r} and as {parameter.doc!r}.")
            by_name[parameter.name] = parameter

        ## A name that is the start of another, part by part: "output.snapshot" of "output.snapshot.dt". TOML would
        ## have to write "output.snapshot" both as a value and as a table, which it cannot. Every shorter name a name
        ## starts with, of two parts or more, is looked up among the declared names; "output.snap" is not the start of
        ## "output.snapshot.dt", since only whole parts count.
        for name in by_name:
            parts = name.split(".")
            for length in range(2, len(parts)):
                start = ".".join(parts[:length])
                if start in by_name:
                    raise ValueError(
                        f"{start!r} and {name!r} cannot both be parameters: a parameter file would have to give "
                        f"{start!r} both a value and a table of its own."
                    )

        ## The alternatives (PAR22). Their names must be distinct, since the resolved parameters state each selection
        ## by it. Every parameter of a group must be declared, and in one group only, of all the sets: a value given for
        ## a parameter in two groups would select both.
        group_of: dict[str, str] = {}
        names_of_sets: set[str] = set()
        for alternatives in self.alternatives:
            if alternatives.name in names_of_sets:
                raise ValueError(f"The alternatives {alternatives.name!r} are declared twice.")
            names_of_sets.add(alternatives.name)
            for group, names in alternatives.groups.items():
                for name in names:
                    if name not in by_name:
                        raise ValueError(
                            f"The group {group!r} of the alternatives {alternatives.name!r} names {name!r}, which is "
                            "not declared."
                        )
                    where = f"the group {group!r} of {alternatives.name!r}"
                    if name in group_of:
                        raise ValueError(f"{name!r} is in more than one group: {group_of[name]} and {where}.")
                    group_of[name] = where

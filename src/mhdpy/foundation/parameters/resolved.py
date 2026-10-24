"""The resolved parameters of a run: the values it uses, where each came from, and what was wrong with them.

Resolving the parameters of a run (``resolution.py``) ends in one of two ways. Either every value passes its checks,
and the run is given its ``Parameters``: a read-only mapping from each name to its value, of its declared type and in
code units, with the value of a list parameter as a tuple, so that no value can be changed once resolved, not even in
place (PAR18). Next to the values, the parameters hold the ``Origin`` of each: the layer it came from, the parameter
file by name, and the value as it was given there, such as ``"100 pc"`` (PAR10); the group selected of each set of
alternatives (PAR22); and, on restart, the ``Changes`` the restart made to the original run, each a ``Change`` (PAR17).
They convert to a ``Record`` of plain values, which outputs store as JSON and a restart starts from, exactly (PAR19).

Or some values do not pass, and resolving raises one ``ParameterError``, which lists every mistake at once, each a
``Mistake`` with the name, the origin of the value and what was expected, so that a user corrects a parameter file in
one pass (PAR14).

The types live in this module of their own, apart from the process that makes them, so that the resolution and
everything that reads its results share one definition of each. Like the rest of the component, the module depends on
nothing beyond the standard library (PAR21).

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR10, PAR14,
PAR17-PAR19), and they are tested in ``tests/test_supplying_values.py``, ``tests/test_checks.py``,
``tests/test_records.py`` and ``tests/test_restarts.py``.
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Literal, TypedDict, cast

from mhdpy.foundation.parameters.values import is_list

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = [
    "Change",
    "Changes",
    "Mistake",
    "Origin",
    "ParameterError",
    "Parameters",
    "Record",
    "frozen",
    "given_as",
]


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


def frozen(value: object) -> object:
    """Return a value as the parameters hold it: a list as a tuple of its elements, anything else as it is (PAR18).

    A tuple cannot be changed in place, and, as a new object, not through the list it was made from either. The
    elements need no copy: they are bools, numbers or strings (PAR03), none of which can be changed.
    """
    return tuple(value) if is_list(value) else value


def _thawed(value: object) -> object:
    """Return a value as the record holds it: a tuple as a list of its elements, anything else as it is (PAR19).

    The reverse of ``frozen``: JSON has no tuples, and a new list can be changed by a writer of the record without
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
        self._values = {name: frozen(value) for name, value in values.items()}
        self._origins = MappingProxyType(
            {name: replace(origin, value=frozen(origin.value)) for name, origin in origins.items()}
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


def given_as(given: object, value: object) -> str:
    """Return the value as given, for a message, where it differs from the value in code units, or an empty string.

    A value with a unit is shown as it was given as well, as " (given as '100 pc')", so that the user recognises what
    was written; an integer given for a float equals its float, and is not shown twice.
    """
    ## A NaN is not equal even to itself, so a value that was not converted at all is told apart first, as the same
    ## object.
    return "" if given is value or given == value else f" (given as {given!r})"

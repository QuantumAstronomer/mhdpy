"""The parameters of a restarted run: what a restart keeps, what it may change, and what it changed (PAR15-PAR17).

A restarted run continues the original run. The record of the original run's parameters (PAR19), which the restart file
holds, then replaces the defaults as the lowest layer, so that every value not given anew is the one the original run
used, and the group each set of alternatives selected stays selected. A parameter declared since the restart file was
written keeps its default, and a recorded name that is no longer declared is ignored, so that a run can be continued
after its modules were updated; a recorded value that its declaration now refuses is refused with the other mistakes
(PAR15).

The parameter file and the overrides may then change only the parameters declared changeable: a new value for a fixed
parameter is refused, since the restart file would no longer describe the run, but a value equal to the recorded one,
compared in code units, is no change, and leaves the recorded value in place, so that the original parameter file can be
used unchanged and the restart still continues the original run bit for bit (PAR16). Likewise, another group of a set of
alternatives may be selected only if every parameter of both groups is changeable (PAR22).

What the restart changed is listed with the parameters, for the driver to log and the writers to record: every value and
every selected group that differs from the record, with both, every parameter missing from the record, with the default
it took, and every recorded name that was ignored, with its recorded value (PAR17).

The rules of this module are applied by ``resolve`` (``resolution.py``), as one step among its checks: the record layer
before the parameter file and the overrides, the comparison with the record once every value has passed its own checks,
and the list of changes last. Keeping a recorded value means resolving it, which only the resolution can do, and the
selection of another group is refused where the groups are selected; both stay there.

The requirements this module fulfils are in ``docs/requirements/L0-foundation/parameters.md`` (PAR15-PAR17), and they
are tested in ``tests/test_restarts.py``.
"""

from collections.abc import Mapping
from typing import Any

from mhdpy.foundation.parameters.declarations import Declarations, Parameter
from mhdpy.foundation.parameters.resolved import Change, Changes, Mistake, Origin, Record, frozen, given_as

## The public interface of this module (D15.7): only names listed here are meant for use outside it.
__all__ = ["changes", "fixed_mistake", "restored"]


def restored(declarations: Declarations, record: Record) -> dict[str, Origin]:
    """Return the origins of the values a restart restores from the record, by their names (PAR15).

    Every parameter the record holds that is still declared, with the restart record as its origin and its recorded
    value as the value as given. A recorded name that is no longer declared is left out, rather than refused as an
    unknown name (PAR11), so that a run can be continued after its modules were updated; a declared parameter missing
    from the record is left out too, and keeps its default.
    """
    declared = {parameter.name for parameter in declarations.parameters}
    return {name: Origin(source="restart", value=value) for name, value in record["values"].items() if name in declared}


def fixed_mistake(parameter: Parameter, value: object, origin: Origin, recorded: object) -> Mistake:
    """Return the mistake of a fixed parameter given a value on restart other than its recorded one (PAR16).

    The message states that the restart file fixes the value, and the recorded value it fixes it at.
    """
    message = (
        f"{parameter.name!r} is fixed by the restart file at {recorded!r}, got {value!r}"
        f"{given_as(origin.value, value)}."
    )
    return Mistake(name=parameter.name, origin=origin, message=message)


def changes(
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
        name: Change(recorded=frozen(recorded[name]), new=frozen(value))
        for name, value in values.items()
        if name in recorded and value != recorded[name]
    }

    ## Every declared parameter missing from the record that took its default, and not a value of another layer
    ## (PAR15); and every recorded name that is no longer declared, with its recorded value.
    missing = {
        name: frozen(value)
        for name, value in values.items()
        if name not in recorded and origins[name].source == "default"
    }
    ignored = {name: frozen(value) for name, value in recorded.items() if name not in declared}

    ## Every set of alternatives whose selected group differs from the recorded one, a recorded group that no longer
    ## exists included; a set missing from the record has no recorded group to differ from (PAR15, PAR22).
    groups = record["selected"]
    switched = {
        name: Change(recorded=groups[name], new=group)
        for name, group in selected.items()
        if name in groups and groups[name] != group
    }
    return Changes(values=changed, missing=missing, ignored=ignored, selected=switched)

"""Tests of the records of a unit system: fixed once created, comparable, and recorded exactly (UNI12-UNI14)."""

import dataclasses
import json
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mhdpy.foundation.units import constants
from mhdpy.foundation.units.system import UnitSystem
from mhdpy.foundation.units.tests.reference import LENGTH, MASS, TIME


class TestRecords:
    """UNI12-UNI14: a unit system is fixed once created, comparable, and recorded exactly in files."""

    ## Run this test for every defining value, and for a name that is not an attribute at all.
    @pytest.mark.parametrize("name", ["length", "mass", "time", "mu", "new_attribute"])
    def test_cannot_be_changed(self, name: str) -> None:
        """Check that changing a unit system after its creation is refused (UNI12)."""
        ## A unit system of its own rather than the shared fixture: should the refusal fail, the change must not reach
        ## the unit system the other tests use.
        system = UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)

        ## setattr(system, "mass", 1.0) is the same as system.mass = 1.0, and delattr(system, "mass") as del
        ## system.mass. A frozen dataclass refuses both with a FrozenInstanceError, for its fields and for any new
        ## attribute alike.
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(system, name, 1.0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            delattr(system, name)

        ## The refused change has left the unit system as it was.
        assert system == UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)

    def test_equality(self) -> None:
        """Check that two unit systems are equal if and only if their defining values are equal (UNI13).

        The defining values are the three code units and the default mean molecular weight.
        """
        system = UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)

        ## Two unit systems created from the same values are equal, though they are different objects. Equal objects
        ## must also have equal hashes, so that a unit system can serve as the key of a dictionary.
        same = UnitSystem(length=LENGTH, mass=MASS, time=TIME, mu=0.6)
        assert same is not system
        assert same == system
        assert hash(same) == hash(system)

        ## A difference in any one defining value makes them unequal: each code unit changed by a single ulp, the
        ## default mean molecular weight changed, and no default at all. math.nextafter(x, math.inf) is the next
        ## double above x, the smallest possible change.
        changes = [
            {"length": math.nextafter(LENGTH, math.inf)},
            {"mass": math.nextafter(MASS, math.inf)},
            {"time": math.nextafter(TIME, math.inf)},
            {"mu": 1.3},
            {"mu": None},
        ]
        for change in changes:
            ## dataclasses.replace creates a new unit system with the values of the old one, except those it is given.
            ## The new one is created, and checked, as any other: the old one stays as it is (UNI12).
            other = dataclasses.replace(system, **change)
            assert other != system, f"change {change}"

    ## Hypothesis draws code units from every positive, finite double, the very large and very small included, and a
    ## default mean molecular weight that is either absent (None) or a positive, finite double. st.one_of draws from
    ## one of the strategies it is given.
    @given(
        length=st.floats(min_value=0.0, exclude_min=True, allow_infinity=False),
        mass=st.floats(min_value=0.0, exclude_min=True, allow_infinity=False),
        time=st.floats(min_value=0.0, exclude_min=True, allow_infinity=False),
        mu=st.one_of(st.none(), st.floats(min_value=0.0, exclude_min=True, allow_infinity=False)),
    )
    def test_record_round_trip(self, length: float, mass: float, time: float, mu: float | None) -> None:
        """Check that a unit system created again from its record is equal to it (UNI14).

        Every value must be identical bit for bit.
        """
        system = UnitSystem(length=length, mass=mass, time=time, mu=mu)
        record = system.to_record()

        ## The record consists of plain values only, Python's own floats and strings, which any file format can
        ## store: HDF5 attributes, TOML, JSON. type() rather than isinstance(), since np.float64 is a subclass of
        ## float but not a plain value. A missing default is left out rather than recorded as None, which HDF5
        ## attributes cannot hold.
        assert all(type(value) in (float, str) for value in record.values())
        assert ("mu" in record) == (mu is not None)

        ## Write the record as text and read it back, as a file would. JSON writes each float with the shortest
        ## digits that read back as the same double, so text is no obstacle to exactness.
        stored = json.loads(json.dumps(record))

        ## The unit system created from the stored record is equal to the original (UNI13), and every defining value
        ## is identical bit for bit: float.hex() writes the exact bits of a double, sign, exponent and digits.
        restored = UnitSystem.from_record(stored)
        assert restored == system
        for name in ("length", "mass", "time"):
            assert float(getattr(restored, name)).hex() == float(getattr(system, name)).hex()
        if mu is not None:
            assert restored.mu is not None and float(restored.mu).hex() == float(mu).hex()

    def test_record_names_sources(self, system: UnitSystem) -> None:
        """Check that the record names the sources of the constants (UNI14).

        The sources are CODATA 2022, AME 2020, and the IAU resolutions of 2012 and 2015.
        """
        record = system.to_record()

        ## The sources are one line of text in the record, the one the constants module states. The isinstance check
        ## also tells the type checker that the value is a string, which the record's type leaves open.
        sources = record["sources"]
        assert isinstance(sources, str)
        assert sources == constants.SOURCES
        for source in ("CODATA 2022", "AME 2020", "IAU 2012", "IAU 2015"):
            assert source in sources

"""Tests of the unit system: requirements UNI01-UNI18 (docs/requirements/L0-foundation/units.md).

The tests are grouped in classes that follow the groups of requirements in that document. Each test names the
requirements it checks in its docstring.
"""

import itertools
import math
from decimal import Decimal, localcontext

import pytest

from mhdpy.foundation import units

## Tests that can only be written once later layers exist: physics modules declaring what they need (D12.1) and a
## simulation that can be set up and run (D13).
NEEDS_DRIVER = pytest.mark.skip(reason="needs physics modules and the driver of a simulation (layers L6 and above)")

## A test that is planned but not written yet. Its body is pytest.fail("Not written yet."), which this marker declares
## an expected failure ("xfail"), so the suite stays green while the test is visibly unfinished: pytest reports it as
## "x" rather than as passed or failed. raises= accepts only that deliberate failure, so a stub that crashed for any
## other reason would still fail. strict=True turns a stub that unexpectedly passes into a failure, so the marker cannot
## be forgotten once the test is written. When a test is written, its marker is removed.
NOT_WRITTEN = pytest.mark.xfail(reason="not written yet", raises=pytest.fail.Exception, strict=True)

## Code units of 1 kpc, 1e5 solar masses and 1 Myr, written out in cgs. The tests of the definition use these literal
## values so that they do not depend on the astronomical constants of the unit system itself, which are tested
## separately (UNI11).
LENGTH = 3.0856775814913673e21
MASS = 1.988409870698051e38
TIME = 3.15576e13

## The same values by name, so that a test can look up the value a code unit was given.
CODE_UNITS = {"length": LENGTH, "mass": MASS, "time": TIME}

## The named units of UNI03 with the exponents of their dimensions in length, mass and time. A dimension that does not
## occur is left out (its exponent is 0). This table is the specification the test checks the unit system against.
# fmt: off
NAMED_UNITS: dict[str, dict[str, float]] = {
    "length":           {"length":  1                        },
    "mass":             {              "mass": 1             },
    "time":             {                         "time":  1 },
    "velocity":         {"length":  1,            "time": -1 },  ## cm s^-1
    "acceleration":     {"length":  1,            "time": -2 },  ## cm s^-2
    "density":          {"length": -3, "mass": 1             },  ## g cm^-3
    "momentum_density": {"length": -2, "mass": 1, "time": -1 },  ## g cm^-2 s^-1
    "mass_flux":        {"length": -2, "mass": 1, "time": -1 },  ## g cm^-2 s^-1
    "pressure":         {"length": -1, "mass": 1, "time": -2 },  ## dyn cm^-2 = g cm^-1 s^-2
    "energy_density":   {"length": -1, "mass": 1, "time": -2 },  ## erg cm^-3 = g cm^-1 s^-2
    "energy":           {"length":  2, "mass": 1, "time": -2 },  ## erg = g cm^2 s^-2
    "specific_energy":  {"length":  2,            "time": -2 },  ## erg g^-1 = cm^2 s^-2
    "energy_flux":      {              "mass": 1, "time": -3 },  ## erg cm^-2 s^-1 = g s^-3
}
# fmt: on

## The label of each named unit's cgs unit (UNI04), exactly as it is to appear in the headers of the history and the
## attributes of outputs. Units are written with their cgs names where those exist (dyn, erg), and exponents with ^.
# fmt: off
LABELS = {
    "length"            : "cm",
    "mass"              : "g",
    "time"              : "s",
    "velocity"          : "cm s^-1",
    "acceleration"      : "cm s^-2",
    "density"           : "g cm^-3",
    "momentum_density"  : "g cm^-2 s^-1",
    "mass_flux"         : "g cm^-2 s^-1",
    "pressure"          : "dyn cm^-2",
    "energy_density"    : "erg cm^-3",
    "energy"            : "erg",
    "specific_energy"   : "erg g^-1",
    "energy_flux"       : "erg cm^-2 s^-1",
}
# fmt: on


class TestDefinition:
    """UNI01-UNI04: a unit system is defined by three code units, from which every other unit derives."""

    ## Run this test once for each code unit. Each name in the list becomes a separate test case, reported for example
    ## as test_defined_by_three_code_units[mass], so a failure names the unit that was not kept.
    @pytest.mark.parametrize("name", ["length", "mass", "time"])
    def test_defined_by_three_code_units(self, name: str) -> None:
        """Check that a unit system keeps its three defining code units exactly as given (UNI01)."""
        ## Set up a unit system with the code units defined at the top of this file.
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## getattr(system, "mass") is the same as system.mass: it reads the attribute whose name is in the variable.
        ## The value read back must be exactly the value given. Exact equality of floats is right here, because no
        ## arithmetic happens in between: any difference at all means the unit system altered its input.
        assert getattr(system, name) == CODE_UNITS[name]

    ## Run this test for every combination of a code unit and an invalid value. Two parametrize decorators multiply:
    ## 3 names x 5 values = 15 test cases, each reported by its values, for example
    ## test_invalid_code_unit_is_refused[nan-mass].
    @pytest.mark.parametrize("name", ["length", "mass", "time"])
    @pytest.mark.parametrize("value", [0.0, -1.0, math.inf, -math.inf, math.nan])
    def test_invalid_code_unit_is_refused(self, name: str, value: float) -> None:
        """Check that a code unit that is not positive and finite is refused at creation (UNI01).

        Zero, negative, infinite and undefined values are all refused, with an error that names the offending unit.
        """
        ## Start from the valid code units and replace the one under test by the invalid value. The | operator merges
        ## two dictionaries; where both have the same key, the value of the right-hand one wins.
        arguments = CODE_UNITS | {name: value}

        ## Creating the unit system must raise a ValueError. The match argument is searched for in the error message,
        ## so the test also checks that the message names the offending unit: an error about "mass" when the length
        ## is wrong would fail it.
        with pytest.raises(ValueError, match=name):
            units.UnitSystem(**arguments)

    def test_unit_from_dimensions(self) -> None:
        """Check that the unit of dimensions L^a M^b T^c is the code units' product to those powers (UNI02).

        The product must agree to within 4 ulp, for integer and half-integer exponents alike.
        """
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        ## All exponents from -4 to 4 in steps of 1/2: integers and half-integers, as the requirement asks.
        exponents = [k / 2 for k in range(-8, 9)]

        ## Every combination of three exponents, 17^3 = 4913 in all. itertools.product(exponents, repeat=3) gives each
        ## triplet (length, mass, time) once. Checking them all is fast (about a second) and, unlike a random sample,
        ## cannot miss the one combination where the error is largest.
        for length, mass, time in itertools.product(exponents, repeat=3):
            ## The reference, computed independently with Python's decimal module at 50 significant digits.
            ## Decimal(LENGTH) is the exact value of the double LENGTH, and the powers and products are rounded only at
            ## the 50th digit, so the reference is exact for any comparison in double precision. localcontext() sets
            ## the precision for this block only, without affecting decimal arithmetic elsewhere.
            with localcontext() as context:
                context.prec = 50
                exact = (
                    Decimal(LENGTH) ** Decimal(length) * Decimal(MASS) ** Decimal(mass) * Decimal(TIME) ** Decimal(time)
                )
            expected = float(exact)  ## the double nearest to the exact value

            ## math.ulp(x) is the gap between x and the next larger double, the "unit in the last place". Three powers
            ## (about 1 ulp each) and two products (1/2 ulp each) give a bound of 4 ulp. The message after the comma is
            ## shown when the assert fails, and names the exponents of the failing combination.
            actual = system.unit(length=length, mass=mass, time=time)
            assert abs(actual - expected) <= 4 * math.ulp(expected), f"exponents {length}, {mass}, {time}"

    ## Run this test once for every named unit. Each key of NAMED_UNITS becomes a separate test case, reported for
    ## example as test_named_units_follow_from_dimensions[density].
    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_named_units_follow_from_dimensions(self, name: str) -> None:
        """Check that every named unit equals the unit computed from its dimensions, to within 4 ulp (UNI03)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)
        ## The named unit, read as an attribute: getattr(system, "density") is system.density.
        named = getattr(system, name)

        ## The same unit from its dimensions through the general rule of UNI02, which is tested on its own.
        from_dimensions = system.unit(**NAMED_UNITS[name])

        ## Both must agree to within 4 ulp, the tolerance of UNI02.
        assert abs(named - from_dimensions) <= 4 * math.ulp(from_dimensions)

        ## Run this test once for every named unit, as the test of UNI03 does.

    @pytest.mark.parametrize("name", list(NAMED_UNITS))
    def test_named_unit_labels(self, name: str) -> None:
        """Check that every named unit has the label of its cgs unit, as written in file headers (UNI04)."""
        system = units.UnitSystem(length=LENGTH, mass=MASS, time=TIME)

        ## The expected label is looked up in LABELS. A named unit missing from that table makes this lookup fail with
        ## a KeyError, so a new named unit cannot be added without deciding on its label.
        assert system.label(name) == LABELS[name]


class TestConversions:
    """UNI05-UNI06: conversions are a multiplication or a division by the unit, exact up to rounding."""

    @NOT_WRITTEN
    def test_conversion_of_numbers(self) -> None:
        """Check that a number converts to cgs by multiplication with its unit and back by division (UNI05)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_conversion_of_arrays(self) -> None:
        """Check that arrays convert elementwise, keep their shape and come out in double precision (UNI05).

        The result must be in double precision whatever the precision of the input array.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_round_trip_from_code_units(self) -> None:
        """Check that converting from code units to cgs and back reproduces a value to within 2 ulp (UNI06)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_round_trip_from_cgs(self) -> None:
        """Check that converting from cgs to code units and back reproduces a value to within 2 ulp (UNI06)."""
        pytest.fail("Not written yet.")


class TestMagneticField:
    """UNI07: the factor 4 pi is absorbed into the magnetic field."""

    @NOT_WRITTEN
    def test_magnetic_field_unit(self) -> None:
        """Check that the code unit of the magnetic field is sqrt(4 pi p_u) gauss (UNI07).

        Here p_u is the code unit of pressure.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_magnetic_energy_density_agrees(self) -> None:
        """Check that a field's energy density is the same physical quantity in both systems (UNI07).

        B^2 / (8 pi), with B in gauss, must equal B_code^2 / 2 times the code unit of pressure, to within 4 ulp.
        """
        pytest.fail("Not written yet.")


class TestTemperature:
    """UNI08-UNI09: temperature converts from the ratio of pressure to density through the mean molecular weight."""

    @NOT_WRITTEN
    def test_temperature_from_pressure_over_density(self) -> None:
        """Check that T = mu m_H (p / rho) / k_B for a ratio p / rho in code units (UNI08).

        The mean molecular weight mu is in units of the mass of the hydrogen atom m_H.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_pressure_over_density_from_temperature(self) -> None:
        """Check that the conversion from temperature to p / rho in code units inverts the first (UNI08).

        The two conversions applied one after the other must reproduce the value to within rounding.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_mean_molecular_weight_per_cell(self) -> None:
        """Check that the mean molecular weight may be an array, applied cell by cell (UNI08).

        The array has the shape of the values to convert.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_invalid_mean_molecular_weight_is_refused(self) -> None:
        """Check that a mean molecular weight that is not positive and finite is refused (UNI08)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_default_mean_molecular_weight(self) -> None:
        """Check that a default mean molecular weight is used when a conversion gives none (UNI09).

        The default is the one given when the unit system was created.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_missing_mean_molecular_weight_is_refused(self) -> None:
        """Check that a temperature conversion without any mean molecular weight is refused (UNI09).

        Without a value given to the conversion and without a default, no value may be assumed silently.
        """
        pytest.fail("Not written yet.")


class TestPhysicalConstants:
    """UNI10-UNI11: physical constants and astronomical units from cited sources."""

    @NOT_WRITTEN
    def test_measured_constants_in_cgs(self) -> None:
        """Check the measured constants in cgs against the values of CODATA 2022 (UNI10)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_exact_constants_in_cgs(self) -> None:
        """Check that the exact constants are the doubles nearest to their exact values in cgs (UNI10).

        The constants exact by the definition of the SI are c, h and k_B.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_hydrogen_mass(self) -> None:
        """Check the mass of the hydrogen atom against the Atomic Mass Evaluation 2020 (UNI10).

        The reference is the atomic mass of 1H in units of the atomic mass unit.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_constants_in_code_units(self) -> None:
        """Check that every constant converts to code units by its dimensions (UNI10).

        A constant containing the kelvin, such as k_B, keeps it: code units have no temperature dimension.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_astronomical_units(self) -> None:
        """Check the astronomical units in cgs against the IAU resolutions (UNI11)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_unit_system_from_astronomical_units(self) -> None:
        """Check that a unit system can be defined in astronomical units (UNI11).

        The example of the requirement: 1 kpc, 1e5 solar masses and 1 Myr.
        """
        pytest.fail("Not written yet.")


class TestRecords:
    """UNI12-UNI14: a unit system is fixed once created, comparable, and recorded exactly in files."""

    @NOT_WRITTEN
    def test_cannot_be_changed(self) -> None:
        """Check that changing a unit system after its creation is refused (UNI12)."""
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_equality(self) -> None:
        """Check that two unit systems are equal if and only if their defining values are equal (UNI13).

        The defining values are the three code units and the default mean molecular weight.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_record_round_trip(self) -> None:
        """Check that a unit system created again from its record is equal to it (UNI14).

        Every value must be identical bit for bit.
        """
        pytest.fail("Not written yet.")

    @NOT_WRITTEN
    def test_record_names_sources(self) -> None:
        """Check that the record names the sources of the constants (UNI14).

        The sources are CODATA 2022, AME 2020, and the IAU resolutions of 2012 and 2015.
        """
        pytest.fail("Not written yet.")


class TestDimensionlessSimulations:
    """UNI15-UNI17: simulations without a unit system, and the independence of results from the unit system."""

    @NEEDS_DRIVER
    def test_simulation_without_unit_system_runs(self) -> None:
        """Check that a simulation without a unit system runs, with every quantity in code units (UNI15)."""
        pytest.fail("Not written yet.")

    @NEEDS_DRIVER
    def test_module_needing_units_is_refused(self) -> None:
        """Check that a module needing physical constants is refused in a dimensionless simulation (UNI16).

        The refusal comes at set-up, before the run starts, and names the module.
        """
        pytest.fail("Not written yet.")

    @NEEDS_DRIVER
    def test_results_independent_of_unit_system(self) -> None:
        """Check that a problem posed in code units gives the same state with any unit system or none (UNI17).

        The state in code units must be identical bit for bit.
        """
        pytest.fail("Not written yet.")


class TestDependencies:
    """UNI18: the unit system needs nothing beyond the standard library and NumPy."""

    @NOT_WRITTEN
    def test_no_further_dependencies(self) -> None:
        """Check that importing the unit system imports no third-party package other than NumPy (UNI18)."""
        pytest.fail("Not written yet.")

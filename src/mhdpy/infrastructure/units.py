"""The code units of a run, from its base units in cgs, with the named units and the constants in code units."""

import math
from dataclasses import dataclass


@dataclass(frozen = True)
class Units:
    """The code units of a run, from its base units of mass, length and time in cgs.

    Implements UNIT01.
    """

    ## the code unit of mass in g
    mass: float   = 1.0
    ## the code unit of length in cm
    length: float = 1.0
    ## the code unit of time in s
    time: float   = 1.0


    def __post_init__(self) -> None:
        """Refuse a base unit that is not a positive and finite number.

        Implements UNIT02.
        """

        for name, value in [("mass", self.mass), ("length", self.length), ("time", self.time)]:
            ## a NaN fails the comparison, as every comparison with it is false
            if not (value > 0 and math.isfinite(value)):
                raise ValueError(f"the base unit {name} must be positive and finite, not {value!r}")


    def code_unit(self, dimension: tuple[int, int, int, int]) -> float:
        """Return the code unit of a dimension in cgs.

        The dimension holds the exponents (a, b, c, d) of mass, length, time and temperature, as (1, 2, -2, -1) for
        erg/K. Its code unit is M0**a L0**b T0**c, the size in cgs of one code unit of that dimension, so that a value
        in code units, multiplied by it, gives the value in cgs. Mass, length and time give no scale of temperature,
        which keeps the kelvin, so that d takes no part.

        Implements UNIT03.
        """

        ## temperature keeps the kelvin, so that its exponent d takes no part
        a, b, c, _ = dimension
        return self.mass**a * self.length**b * self.time**c

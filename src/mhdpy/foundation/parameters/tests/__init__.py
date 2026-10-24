"""Tests of the parameters: requirements PAR01-PAR24 (docs/requirements/L0-foundation/parameters.md).

One test module per group of requirements in that document, each with a class of the same scope; each test names the
requirements it checks in its docstring. What several test modules need is defined here once.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import cast


def parameter_file(folder: Path, text: str) -> Path:
    """Return the path of a parameter file with the given text, written in a folder of the test's own."""
    path = folder / "run.toml"
    path.write_text(text)
    return path


def identical(first: object, second: object) -> bool:
    """Return whether two values are identical: of the same type, and equal bit for bit, a list or tuple element-wise.

    == alone cannot tell them apart: in Python, 1 == 1.0 == True and 0.0 == -0.0. float.hex() writes the exact bits of a
    double, sign, exponent and digits, so that two floats with the same hex are the same double.
    """
    if type(first) is not type(second):
        return False
    if isinstance(first, list | tuple):
        ## The type checker learns that second is a list or tuple as well only from the comparison of types above, which
        ## it does not follow; cast tells it so, and that the elements may be of any type.
        firsts = cast(Sequence[object], first)
        seconds = cast(Sequence[object], second)
        return len(firsts) == len(seconds) and all(identical(a, b) for a, b in zip(firsts, seconds, strict=True))
    if isinstance(first, float):
        return first.hex() == cast(float, second).hex()
    return first == second

"""Tests of the package as a whole: its layout, its rule of imports, its metadata and its version."""

import pkgutil
from pathlib import Path

import mhdpy
import tests


## the root of the checkout, the folder above tests/
ROOT = Path(__file__).resolve().parents[1]
## the strata from the bottom up
STRATA = ("infrastructure", "mesh", "core", "physics", "driver")


class TestLayout:
    """Tests of the layout of the package and its tests."""

    def test_package(self) -> None:
        """Checks PACK01.

        The installed package lies in src/mhdpy/ of this checkout, and its subpackages are exactly the five strata.
        """
        ## the file that Python ran for `import mhdpy`, which the editable installation finds in src/
        assert Path(mhdpy.__file__).resolve() == ROOT / "src" / "mhdpy" / "__init__.py"
        ## the modules directly below mhdpy, of which ispkg keeps the folders that hold an __init__.py
        assert {module.name for module in pkgutil.iter_modules(mhdpy.__path__) if module.ispkg} == set(STRATA)


    def test_tests(self) -> None:
        """Checks PACK02.

        The package of the tests lies in tests/ of this checkout, and its subpackages are exactly the five strata.
        """
        ## the file that Python ran for `import tests`, from the root of the checkout that pytest puts on the path
        assert Path(tests.__file__).resolve() == ROOT / "tests" / "__init__.py"
        ## the modules directly below tests, of which ispkg keeps the folders that hold an __init__.py
        assert {module.name for module in pkgutil.iter_modules(tests.__path__) if module.ispkg} == set(STRATA)

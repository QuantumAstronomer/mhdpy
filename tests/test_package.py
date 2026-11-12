"""Tests of the package as a whole: its layout, its rule of imports, its metadata and its version."""

import os
import pkgutil
import shutil
import subprocess
import sys
from importlib.metadata import distribution, metadata
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

import mhdpy
import tests


## the root of the checkout, the folder above tests/
ROOT = Path(__file__).resolve().parents[1]
## the strata from the bottom up
STRATA = ("infrastructure", "mesh", "core", "physics", "driver")


class TestImports:
    """Tests of the rule of imports and its check."""

    ## the violations of PACK07: the requirement whose contract each breaks, and the text it adds to files of a copy
    PLANTED = {
        "upward-at-head": (
            "PACK03", {
                "src/mhdpy/mesh/planted.py": "import mhdpy.driver\n"
                }
            ),
        "upward-in-function": (
            "PACK03", {
                "src/mhdpy/mesh/planted.py": "def late() -> None:\n    import mhdpy.driver\n"
                }
            ),
        "upward-for-type-checking": (
            "PACK03", {
                "src/mhdpy/mesh/planted.py": "import typing\nif typing.TYPE_CHECKING:\n    import mhdpy.driver\n"
                }
            ),
        "cycle-of-siblings": (
            "PACK04", {
                "src/mhdpy/core/first.py": "import mhdpy.core.second\n",
                "src/mhdpy/core/second.py": "import mhdpy.core.first\n"
                }
            ),
        "stratum-by-top-package": (
            "PACK05", {
                "src/mhdpy/__init__.py": "import mhdpy.core\n"
                }
            ),
        "module-of-stratum-by-top-package": (
            "PACK05", {
                "src/mhdpy/core/planted.py": "", "src/mhdpy/__init__.py": "import mhdpy.core.planted\n"
                }
            ),
        "upward-by-tests": (
            "PACK06", {
                "tests/mesh/test_planted.py": "import mhdpy.core\n"
                }
            ),
    }

    @staticmethod
    def lint(root: Path) -> subprocess.CompletedProcess[str]:
        """Run the check of imports on the package and tests below root, under the contracts of its pyproject.toml."""

        command = [Path(sys.executable).with_name("lint-imports"), "--no-cache", "--no-logo"]

        ## the package from src/ and the tests from root, ahead of the installed package
        ## a report too wide for rich to wrap, so that each contract stays on one line
        environment = os.environ | {"PYTHONPATH": f"{root / 'src'}{os.pathsep}{root}", "COLUMNS": "200"}
        return subprocess.run(command, cwd = root, env = environment, capture_output = True, text = True)


    @pytest.fixture
    def copy(self, tmp_path: Path) -> Path:
        """Return a copy of the package and its tests, with the contracts of the check."""

        ignore = shutil.ignore_patterns("__pycache__", "*.egg-info")

        for folder in ("src", "tests"):
            shutil.copytree(ROOT / folder, tmp_path / folder, ignore = ignore)
        shutil.copy(ROOT / "pyproject.toml", tmp_path)
        return tmp_path

    def test_check(self) -> None:
        """Checks PACK03, PACK04, PACK05 and PACK06.

        The check passes on the package and its tests, as every contract of the rule of imports is kept.
        """

        result = self.lint(ROOT)
        assert result.returncode == 0, result.stdout + result.stderr


    @pytest.mark.parametrize(("requirement", "files"), PLANTED.values(), ids = PLANTED.keys())
    def test_planted_violations(self, copy: Path, requirement: str, files: dict[str, str]) -> None:
        """Checks PACK07.

        The check fails on a copy that holds one planted violation, and reports the contract of the rule it breaks.
        """

        ## each text appended to its file, which it creates where the file does not yet exist
        for name, text in files.items():
            with open(copy / name, "a") as file:
                file.write(text)

        result = self.lint(copy)

        assert result.returncode != 0
        ## the contract named after the requirement, as pyproject.toml names each
        assert f"({requirement}) BROKEN" in result.stdout, result.stdout + result.stderr


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


class TestMetadata:
    """Tests of the metadata of the installed distribution."""

    def test_python(self) -> None:
        """Checks PACK08.

        The metadata admits no Python older than 3.14, as its specifier of Python holds a lower bound at 3.14 or later.
        """

        ## the specifier of Requires-Python, empty where the metadata lacks the line
        specifiers = SpecifierSet(metadata("mhdpy").get("Requires-Python", ""))
        
        ## the lower bounds, each of which holds alongside every other clause and so excludes every older Python
        floors = [Version(specifier.version) for specifier in specifiers if specifier.operator == ">="]
        assert any(floor >= Version("3.14") for floor in floors), repr(specifiers)


    def test_dependencies(self) -> None:
        """Checks PACK09.
        
        The metadata names NumPy as its only dependency at runtime, bounded below, at 2.3.2 or later, and not above.
        """

        ## the requirements of Requires-Dist, none where the metadata lacks the line
        requirements = [Requirement(text) for text in metadata("mhdpy").get_all("Requires-Dist", [])]

        ## names compare without regard to case
        assert [requirement.name.lower() for requirement in requirements] == ["numpy"]

        specifiers = requirements[0].specifier
        ## a lower bound at 2.3.2 or later, as in the test of Python
        floors = [Version(specifier.version) for specifier in specifiers if specifier.operator == ">="]
        assert any(floor >= Version("2.3.2") for floor in floors), repr(specifiers)

        ## only operators that bound from below or exclude, none that caps the version from above
        assert all(specifier.operator in (">=", ">", "!=") for specifier in specifiers), repr(specifiers)


    def test_extras(self) -> None:
        """Checks PACK10.

        The metadata names no extra, as it holds no Provides-Extra line.
        """

        ## all Provides-Extra lines, or an empty list if there are none
        assert metadata("mhdpy").get_all("Provides-Extra", []) == []


    def test_licence(self) -> None:
        """Checks PACK11.

        The metadata names the licence by the SPDX expression BSD-3-Clause, and the installation ships the file LICENSE.
        """

        assert metadata("mhdpy").get("License-Expression") == "BSD-3-Clause"

        ## the files named by License-File lines
        assert "LICENSE" in metadata("mhdpy").get_all("License-File", [])
        
        ## the copy shipped in the licenses/ folder of the metadata, identical to LICENSE in the checkout
        assert distribution("mhdpy").read_text("licenses/LICENSE") == (ROOT / "LICENSE").read_text()

"""The check of requirements: every test cites requirements that exist and are not withdrawn."""

import ast
import re
import subprocess
import sys
import warnings
from pathlib import Path
from typing import NamedTuple

import pytest


## the root of the checkout, the folder above tests/
ROOT = Path(__file__).resolve().parents[1]
## an identifier, a word of capitals followed by two digits, as RIEM04
IDENTIFIER = re.compile(r"\b[A-Z]+[0-9]{2}\b")
## the opening of a requirement: its anchor, its identifier in bold, and the rest of the line
OPENING = re.compile(r'<a id="([a-z]+[0-9]{2})"></a>\*\*([A-Z]+[0-9]{2})\*\*\s*(.*)')
## the end of a sentence, a full stop followed by whitespace or the end of the text
END = re.compile(r"\.(?:\s|$)")


class Requirement(NamedTuple):
    """A requirement, by its identifier, the document that holds it, and whether it is withdrawn."""

    identifier: str
    document: str
    withdrawn: bool


class UntestedRequirementWarning(UserWarning):
    """A warning of the requirements in force that no test cites."""


class TestReading:
    """Tests that the check finds every test with its citation, and every requirement with whether it is withdrawn."""

    def test_tests(self, tmp_path: Path) -> None:
        """Checks CITE01.

        The tests are the functions at the head of a test module and the methods of its test classes, read without
        importing the module.
        """

        root = tree(tmp_path, {
            "tests/test_first.py": "\n".join([
                ## a module that fails as soon as it is imported
                'raise RuntimeError("imported")',
                'def test_function():',
                '    """Checks FOO01."""',
                'def helper():',
                '    """Checks FOO02."""',
                'class TestGroup:',
                '    def test_method(self):',
                '        """Checks FOO03 and FOO04."""',
                '    def helper(self):',
                '        """Checks FOO05."""',
                'class Group:',
                '    def test_method(self):',
                '        """Checks FOO06."""',
                'def test_outer():',
                '    """Checks FOO07."""',
                '    def test_inner():',
                '        """Checks FOO08."""',
            ]),
            "tests/folder/second_test.py": "\n".join([
                'def test_function():',
                '    """Checks BAR01."""',
            ]),
            "tests/helpers.py": "\n".join([
                'def test_function():',
                '    """Checks BAZ01."""',
            ]),
        })

        assert read_tests(root) == {
            "tests/folder/second_test.py::test_function": ["BAR01"],
            "tests/test_first.py::test_function": ["FOO01"],
            "tests/test_first.py::TestGroup::test_method": ["FOO03", "FOO04"],
            "tests/test_first.py::test_outer": ["FOO07"],
        }


    def test_opening_sentence(self, tmp_path: Path) -> None:
        """Checks CITE01.

        A citation is the opening sentence of a docstring that begins with the word Checks, and it ends at a full stop
        followed by whitespace, which a dotted name does not end.
        """

        root = tree(tmp_path, {
            "tests/test_first.py": "\n".join([
                'def test_dotted():',
                '    """Checks FOO01 of mhdpy.core and FOO02. The test also checks FOO03."""',
                'def test_lines():',
                '    """Checks FOO04',
                '    and FOO05.',
                '',
                '    The test also checks FOO06.',
                '    """',
                'def test_other_word():',
                '    """Tests FOO07."""',
                'def test_no_identifier():',
                '    """Checks the layout."""',
                'def test_no_docstring():',
                '    pass',
            ]),
        })

        assert read_tests(root) == {
            "tests/test_first.py::test_dotted": ["FOO01", "FOO02"],
            "tests/test_first.py::test_lines": ["FOO04", "FOO05"],
            "tests/test_first.py::test_other_word": [],
            "tests/test_first.py::test_no_identifier": [],
            "tests/test_first.py::test_no_docstring": [],
        }


    def test_requirements(self, tmp_path: Path) -> None:
        """Checks CITE02.

        The requirements are the paragraphs that open with their identifier in lower case as an anchor and then in bold,
        read with whether each is withdrawn from every document below design/requirements/.
        """

        root = tree(tmp_path, {
            "design/requirements/infrastructure/first.md": "\n".join([
                '# First',
                '',
                '<a id="foo01"></a>**FOO01** The first shall hold, as [BAR01](../core/second.md#bar01) does.',
                '',
                '<a id="foo02"></a>**FOO02** Withdrawn on 2026-11-13, replaced by FOO03. The first shall hold.',
                '',
                '<a id="foo03"></a>**FOO03** The first shall hold.',
                '',
                '<a id="foo09"></a>**FOO04** The first shall hold, under an anchor that is not its identifier.',
            ]),
            "design/requirements/core/second.md": "\n".join([
                '<a id="bar01"></a>**BAR01** The second shall hold.',
            ]),
            "design/requirements/third.md": "\n".join([
                '<a id="baz01"></a>**BAZ01** The third shall hold.',
            ]),
            "design/fourth.md": "\n".join([
                '<a id="qux01"></a>**QUX01** The fourth, outside design/requirements/, shall hold.',
            ]),
        })

        assert read_requirements(root) == [
            Requirement("BAR01", "design/requirements/core/second.md", False),
            Requirement("FOO01", "design/requirements/infrastructure/first.md", False),
            Requirement("FOO02", "design/requirements/infrastructure/first.md", True),
            Requirement("FOO03", "design/requirements/infrastructure/first.md", False),
            Requirement("BAZ01", "design/requirements/third.md", False),
        ]


class TestFaults:
    """Tests that the check fails on a missing, unknown or withdrawn citation, and on an identifier borne twice."""

    ## a tree that the check passes, to which each test below adds one fault
    FILES = {
        "design/requirements/first.md": "\n".join([
            '<a id="foo01"></a>**FOO01** The first shall hold.',
            '',
            '<a id="foo02"></a>**FOO02** Withdrawn on 2026-11-13, replaced by FOO03. The first shall hold.',
            '',
            '<a id="foo03"></a>**FOO03** The first shall hold.',
        ]),
        "tests/test_first.py": "\n".join([
            'def test_function():',
            '    """Checks FOO01 and FOO03."""',
        ]),
    }

    @staticmethod
    def failure(root: Path) -> list[str]:
        """Return the lines of the message with which the check fails on the tree at root."""

        with pytest.raises(AssertionError) as error:
            check(root)
        return str(error.value).splitlines()


    def test_files(self, tmp_path: Path) -> None:
        """Checks CITE03, CITE04, CITE05 and CITE06.

        The check passes on the tree of the other tests before a fault is added to it.
        """

        check(tree(tmp_path, self.FILES))


    def test_no_citation(self, tmp_path: Path) -> None:
        """Checks CITE03.

        The check fails on tests whose docstring opens with no citation, and names each.
        """

        root = tree(tmp_path, self.FILES | {
            "tests/test_second.py": "\n".join([
                'def test_other_word():',
                '    """Tests FOO01."""',
                'class TestGroup:',
                '    def test_no_docstring(self):',
                '        pass',
            ]),
        })

        lines = self.failure(root)
        assert any("tests/test_second.py::test_other_word" in line for line in lines), lines
        assert any("tests/test_second.py::TestGroup::test_no_docstring" in line for line in lines), lines
        assert not any("tests/test_first.py" in line for line in lines), lines

    def test_unknown(self, tmp_path: Path) -> None:
        """Checks CITE04.

        The check fails on a test that cites an identifier that no requirement bears, and names the test with it.
        """

        root = tree(tmp_path, self.FILES | {
            "tests/test_second.py": "\n".join([
                'def test_function():',
                '    """Checks FOO01 and FOO09."""',
            ]),
        })

        lines = self.failure(root)
        assert any("tests/test_second.py::test_function" in line and "FOO09" in line for line in lines), lines
        assert not any("FOO01" in line for line in lines), lines


    def test_withdrawn(self, tmp_path: Path) -> None:
        """Checks CITE05.

        The check fails on a test that cites a withdrawn requirement, and names the test with the requirement.
        """

        root = tree(tmp_path, self.FILES | {
            "tests/test_second.py": "\n".join([
                'def test_function():',
                '    """Checks FOO02."""',
            ]),
        })

        lines = self.failure(root)
        assert any("tests/test_second.py::test_function" in line and "FOO02" in line for line in lines), lines


    def test_duplicate(self, tmp_path: Path) -> None:
        """Checks CITE06.

        The check fails on two requirements that bear the same identifier, and names the document of each.
        """

        root = tree(tmp_path, self.FILES | {
            "design/requirements/core/second.md": "\n".join([
                '<a id="foo03"></a>**FOO03** The second shall hold.',
            ]),
        })

        lines = self.failure(root)
        assert any(
            "FOO03" in line and "design/requirements/first.md" in line and "design/requirements/core/second.md" in line
            for line in lines
        ), lines


class TestUntested:
    """Tests that the check warns of the requirements that no test cites, without failing."""

    def test_warning(self, tmp_path: Path) -> None:
        """Checks CITE07.

        The check names every requirement in force that no test cites in one warning of its own category, and passes.
        """

        ## a small checkout in tmp_path: of its three requirements in force, the test cites FOO01 alone
        root = tree(tmp_path, {
            "design/requirements/first.md": "\n".join([
                '<a id="foo01"></a>**FOO01** The first shall hold.',
                '',
                '<a id="foo02"></a>**FOO02** The first shall hold.',
                '',
                '<a id="foo03"></a>**FOO03** Withdrawn on 2026-11-13, replaced by FOO02. The first shall hold.',
            ]),
            "design/requirements/core/second.md": "\n".join([
                '<a id="bar01"></a>**BAR01** The second shall hold.',
            ]),
            "tests/test_first.py": "\n".join([
                'def test_function():',
                '    """Checks FOO01."""',
            ]),
        })

        ## the check returns, rather than fails, and each warning that it gives is recorded
        with pytest.warns(UntestedRequirementWarning) as record:
            check(root)

        ## one warning, of a subclass of UserWarning, that names FOO02 and BAR01 but not the withdrawn FOO03
        assert issubclass(UntestedRequirementWarning, UserWarning)
        assert len(record) == 1
        assert set(IDENTIFIER.findall(str(record[0].message))) == {"FOO02", "BAR01"}


class TestList:
    """Tests that the module, run as a script, prints every requirement with the tests that cite it."""

    def test_listing(self, tmp_path: Path) -> None:
        """Checks CITE08.

        The list gives each requirement with the node ids of the tests that cite it, and marks those that no test cites
        and those withdrawn.
        """

        ## a small checkout in tmp_path: two tests cite FOO01, one of them the withdrawn FOO03 too, and none the rest
        root = tree(tmp_path, {
            "design/requirements/first.md": "\n".join([
                '<a id="foo01"></a>**FOO01** The first shall hold.',
                '',
                '<a id="foo02"></a>**FOO02** The first shall hold.',
                '',
                '<a id="foo03"></a>**FOO03** Withdrawn on 2026-11-13, replaced by FOO02. The first shall hold.',
                '',
                '<a id="foo04"></a>**FOO04** Withdrawn on 2026-11-13. The first shall hold.',
            ]),
            "design/requirements/core/second.md": "\n".join([
                '<a id="bar01"></a>**BAR01** The second shall hold.',
            ]),
            "tests/test_first.py": "\n".join([
                'def test_function():',
                '    """Checks FOO01 and FOO03."""',
                'class TestGroup:',
                '    def test_method(self):',
                '        """Checks FOO01."""',
            ]),
        })

        ## each document by its path, each of its requirements below it with its marks, and each test below that
        assert listing(root) == "\n".join([
            "design/requirements/core/second.md",
            "    BAR01 (no test)",
            "design/requirements/first.md",
            "    FOO01",
            "        tests/test_first.py::test_function",
            "        tests/test_first.py::TestGroup::test_method",
            "    FOO02 (no test)",
            "    FOO03 (withdrawn)",
            "        tests/test_first.py::test_function",
            "    FOO04 (withdrawn) (no test)",
        ])

    def test_script(self) -> None:
        """Checks CITE08.

        Run as a script, the module prints the list of the requirements and tests of mhdpy.
        """

        ## this module run by the Python of the tests, as `uv run python tests/test_requirements.py` runs it
        command = [sys.executable, Path(__file__)]
        result = subprocess.run(command, capture_output = True, text = True)
        assert result.returncode == 0, result.stderr

        ## what it prints is the list of this checkout, with the newline that print adds
        assert result.stdout == listing(ROOT) + "\n"


class TestMhdpy:
    """Tests that the tests and requirement documents of mhdpy give the check none of its faults."""

    def test_citations(self) -> None:
        """Checks CITE09.

        The check passes on this checkout, as every test cites requirements that exist and are not withdrawn, and no
        identifier is borne twice.
        """

        ## the check run on this checkout rather than on a small tree, warning of the requirements still without tests
        check(ROOT)


def check(root: Path) -> None:
    """Fail on each fault of the tests and requirements below root, and warn of the requirements without tests."""

    tests = read_tests(root)
    requirements = read_requirements(root)

    ## the requirements in force that no test cites, in one warning (CITE07)
    untested = untested_requirements(tests, requirements)
    if untested:
        warnings.warn(UntestedRequirementWarning(f"no test cites {', '.join(untested)}"))

    faults = [
        *uncited_tests(tests),
        *unknown_citations(tests, requirements),
        *withdrawn_citations(tests, requirements),
        *duplicate_identifiers(requirements)
    ]
    assert not faults, "\n".join(faults)


def citation(function: ast.FunctionDef) -> list[str]:
    """Return the identifiers that the opening sentence of the docstring of function cites, none without a citation."""

    sentence = END.split(ast.get_docstring(function) or "", maxsplit = 1)[0]
    if sentence.split()[:1] != ["Checks"]:
        return []
    return IDENTIFIER.findall(sentence)


def duplicate_identifiers(requirements: list[Requirement]) -> list[str]:
    """Return a fault for each identifier that two requirements or more bear, naming the document of each.

    Implements CITE06.
    """

    ## the documents that hold each identifier
    documents: dict[str, list[str]] = {}
    for requirement in requirements:
        documents.setdefault(requirement.identifier, []).append(requirement.document)

    return [
        f"{identifier} is borne in {' and '.join(names)}"
        for identifier, names in documents.items()
        if len(names) > 1
    ]


def listing(root: Path) -> str:
    """Return each requirement below root, by document, with the node ids of the tests that cite it.

    Implements CITE08.
    """

    tests = read_tests(root)
    lines: list[str] = []
    document = ""
    for requirement in read_requirements(root):

        ## the path of each document, above its requirements
        if requirement.document != document:
            document = requirement.document
            lines.append(document)

        ## the identifier with its marks, then each test that cites it on a line of its own
        citing = [test for test, identifiers in tests.items() if requirement.identifier in identifiers]
        marks = ""
        if requirement.withdrawn:
            marks += " (withdrawn)"
        if not citing:
            marks += " (no test)"
        lines.append(f"    {requirement.identifier}{marks}")
        lines.extend(f"        {test}" for test in citing)

    return "\n".join(lines)


def read_requirements(root: Path) -> list[Requirement]:
    """Return the requirements in the documents below root/design/requirements, in the order of their paths.

    Implements CITE02.
    """

    requirements: list[Requirement] = []
    for path in sorted((root / "design" / "requirements").rglob("*.md")):
        document = path.relative_to(root).as_posix()
        for line in path.read_text().splitlines():

            ## a paragraph whose anchor is its identifier in lower case
            match = OPENING.match(line)
            if match and match[1] == match[2].lower():
                requirements.append(Requirement(match[2], document, match[3].startswith("Withdrawn on")))
    return requirements


def read_tests(root: Path) -> dict[str, list[str]]:
    """Return the identifiers that each test in the modules below root/tests cites, by its node id.

    Implements CITE01.
    """

    cited: dict[str, list[str]] = {}
    folder = root / "tests"
    for path in sorted({*folder.rglob("test_*.py"), *folder.rglob("*_test.py")}):
        module = path.relative_to(root).as_posix()

        ## the functions at the head of the module, and the methods of the classes at its head
        for node in ast.parse(path.read_text(), filename = path).body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                cited[f"{module}::{node.name}"] = citation(node)

            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test"):
                        cited[f"{module}::{node.name}::{method.name}"] = citation(method)
    return cited


def tree(root: Path, files: dict[str, str]) -> Path:
    """Write each text to its file below root, with the folders that it needs, and return root."""

    for name, text in files.items():
        (root / name).parent.mkdir(parents = True, exist_ok = True)
        (root / name).write_text(text)
    return root


def uncited_tests(tests: dict[str, list[str]]) -> list[str]:
    """Return a fault for each test whose docstring opens with no citation, naming the test.

    Implements CITE03.
    """

    return [f"{test} cites no requirement" for test, identifiers in tests.items() if not identifiers]


def unknown_citations(tests: dict[str, list[str]], requirements: list[Requirement]) -> list[str]:
    """Return a fault for each identifier that a test cites and no requirement bears, naming the test with it.

    Implements CITE04.
    """

    known = {requirement.identifier for requirement in requirements}
    return [
        f"{test} cites {identifier}, which no requirement bears"
        for test, identifiers in tests.items()
        for identifier in identifiers
        if identifier not in known
    ]


def untested_requirements(tests: dict[str, list[str]], requirements: list[Requirement]) -> list[str]:
    """Return the identifiers of the requirements in force that no test cites, in the order of their documents.

    Implements CITE07.
    """

    cited = {identifier for identifiers in tests.values() for identifier in identifiers}
    return [
        requirement.identifier
        for requirement in requirements
        if not requirement.withdrawn and requirement.identifier not in cited
    ]


def withdrawn_citations(tests: dict[str, list[str]], requirements: list[Requirement]) -> list[str]:
    """Return a fault for each withdrawn requirement that a test cites, naming the test with it.

    Implements CITE05.
    """

    withdrawn = {requirement.identifier for requirement in requirements if requirement.withdrawn}
    return [
        f"{test} cites {identifier}, which is withdrawn"
        for test, identifiers in tests.items()
        for identifier in identifiers
        if identifier in withdrawn
    ]


if __name__ == "__main__":
    print(listing(ROOT))

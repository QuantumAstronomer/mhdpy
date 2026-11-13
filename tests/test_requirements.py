"""The check of requirements: every test cites requirements that exist and are not withdrawn."""

import ast
import re
from pathlib import Path
from typing import NamedTuple


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


class TestReading:
    """Tests of the reading of the tests and the requirements."""

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


def citation(function: ast.FunctionDef) -> list[str]:
    """Return the identifiers that the opening sentence of the docstring of function cites, none without a citation."""

    sentence = END.split(ast.get_docstring(function) or "", maxsplit = 1)[0]
    if sentence.split()[:1] != ["Checks"]:
        return []
    return IDENTIFIER.findall(sentence)


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


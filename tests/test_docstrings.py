"""The check of docstrings: every docstring outside the tests repeats the signature of its code.

Outside the tests, every docstring documents the parameters of its function, or the fields of its class, with their
types and defaults as the code writes them, and its return value by its type. The check keeps these sections true. It
reads every module of src/ and tests/ from its source, without importing it, and fails on entries that do not name the
parameters or fields in their order, on types or defaults that differ from the code, and on a section Returns that is
missing, out of place or of another type.

The check runs as a test on the checkout, so that every full run of the tests checks the docstrings. The other tests of
the module write a small tree of made-up modules into the temporary folder that pytest gives each test, and run the
check on that tree instead. The made-up modules are read as text and never imported.

The module lies in tests/ rather than in a stratum of the package, as the check serves the development of the code and
runs among the tests. The check relies on the standard library alone, and its tests on pytest as well, and on the
function tree of the check of requirements.

Contents
========================================================================================================================
ROOT
    The root of the checkout, the folder above tests/.
TITLES
    The titles of the sections that the check reads.
RULE
    The rule below the title of a section.
ENTRY
    An entry of Parameters: its name, its type and, where it shows one, its default.
Parameter
    A parameter of a function or a field of a class, or an entry that documents one.
Documented
    An object outside the tests, by its name, with its signature and what its docstring documents.
check
    Fail on each docstring outside the tests below root that does not repeat the signature of its code.
class_signature
    Return the fields of a dataclass or named tuple, and no field for any other class.
failure
    Return the lines of the message with which the check fails on the tree at root.
function_signature
    Return the parameters of a function and its return annotation.
last_name
    Return the last name of a name, a dotted name, a call or a subscript.
misnamed_parameters
    Return a fault for each object whose entries do not name its parameters or fields in their order.
misplaced_returns
    Return a fault for each object whose docstring has Returns without a return annotation, or lacks it with one.
mistaken_defaults
    Return a fault for each entry whose default differs from that of its parameter or field.
mistyped_parameters
    Return a fault for each entry whose type differs from the annotation of its parameter or field.
mistyped_returns
    Return a fault for each Returns that holds other than one entry, or whose entry differs from the annotation.
read_docstring
    Return an object with its signature and the entries of the sections Parameters and Returns of its docstring.
read_object
    Return the object that a statement defines, with those in its body if it is a class.
read_objects
    Return every object outside the tests in the modules below root/src and root/tests, in the order of their paths.
read_sections
    Return the entries of the sections Parameters and Returns of a docstring, by title.
text
    Return the source text of an annotation or default, or None where there is none.

Its requirements are in design/requirements/infrastructure/check-of-docstrings.md, and docs/check-of-docstrings.md
explains it.
"""

import ast
import re
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.test_requirements import tree


## the root of the checkout, the folder above tests/
ROOT = Path(__file__).resolve().parents[1]
## the titles of the sections that the check reads
TITLES = ("Parameters", "Returns")
## the rule below the title of a section
RULE = re.compile(r"=+")
## an entry of Parameters: its name, its type and, where it shows one, its default
ENTRY = re.compile(r"(\*{0,2}\w+) : (.+?)(?: \(default = (.+)\))?")


class Parameter(NamedTuple):
    """A parameter of a function or a field of a class, or an entry that documents one.

    Parameters
    ====================================================================================================================
    name : str
        The name, with * or ** before a variadic parameter, as *arguments.
    type : str | None
        The annotation as the source holds it, or None where it has none.
    default : str | None
        The default as the source holds it, or None where it has none.
    """

    name: str
    type: str | None
    default: str | None


class Documented(NamedTuple):
    """An object outside the tests, by its name, with its signature and what its docstring documents.

    Parameters
    ====================================================================================================================
    name : str
        The path of its module and its qualified name, as src/mhdpy/infrastructure/units.py::Units.factor.
    parameters : list[Parameter]
        The parameters of the function or the fields of the class, as the code gives them.
    returns : str | None
        The return annotation as the source holds it, or None where it is missing or None.
    entries : list[Parameter]
        The entries of the section Parameters of its docstring, in their order.
    returned : list[str] | None
        The entries of the section Returns of its docstring, or None where it has no such section.
    """

    name: str
    parameters: list[Parameter]
    returns: str | None
    entries: list[Parameter]
    returned: list[str] | None


class TestReading:
    """Tests that the check finds every object outside the tests, with its signature and its sections."""

    def test_objects(self, tmp_path: Path) -> None:
        """Checks DOCS01.

        The objects are the functions and classes at the head of a module and in the bodies of its classes, without
        the tests, the classes of tests with all that they hold, and the properties.
        """

        ## a module of the package and a test module, each with objects of every kind
        root = tree(tmp_path, {
            "src/package/module.py": "\n".join([
                ## a module that fails as soon as it is imported
                'raise RuntimeError("imported")',
                'def function():',
                '    def inner():',
                '        pass',
                'class Outer:',
                '    def method(self):',
                '        pass',
                '    @property',
                '    def value(self):',
                '        pass',
                '    class Inner:',
                '        pass',
            ]),
            "tests/test_module.py": "\n".join([
                'def test_function():',
                '    pass',
                'def helper():',
                '    pass',
                'class TestGroup:',
                '    def helper(self):',
                '        pass',
                'class Group:',
                '    def test_method(self):',
                '        pass',
            ]),
        })

        ## the objects alone, by name, so that inner, value, test_function and TestGroup with its helper are missing
        assert [documented.name for documented in read_objects(root)] == [
            "src/package/module.py::function",
            "src/package/module.py::Outer",
            "src/package/module.py::Outer.method",
            "src/package/module.py::Outer.Inner",
            "tests/test_module.py::helper",
            "tests/test_module.py::Group",
            "tests/test_module.py::Group.test_method",
        ]


    def test_functions(self, tmp_path: Path) -> None:
        """Checks DOCS01.

        The signature of a function holds its parameters in their order, with the annotations and defaults as written,
        without the first parameter of a method that is not static, and its return annotation unless it is None.
        """

        ## functions with every kind of parameter, and methods with and without a first parameter that is left out
        root = tree(tmp_path, {
            "src/module.py": "\n".join([
                'def function(a: int, /, b: float = 1e5, *c: str, d: bool = True, **e: int) -> tuple[int, int]:',
                '    pass',
                'def bare(a, b = None) -> None:',
                '    pass',
                'class Group:',
                '    def method(self, a: int) -> int:',
                '        pass',
                '    @staticmethod',
                '    def static(a: int):',
                '        pass',
            ]),
        })

        ## the parameters and return annotation of each, by name
        assert {documented.name: (documented.parameters, documented.returns) for documented in read_objects(root)} == {
            "src/module.py::function": ([
                Parameter("a", "int", None),
                Parameter("b", "float", "1e5"),
                Parameter("*c", "str", None),
                Parameter("d", "bool", "True"),
                Parameter("**e", "int", None),
            ], "tuple[int, int]"),
            "src/module.py::bare": ([Parameter("a", None, None), Parameter("b", None, "None")], None),
            "src/module.py::Group": ([], None),
            "src/module.py::Group.method": ([Parameter("a", "int", None)], "int"),
            "src/module.py::Group.static": ([Parameter("a", "int", None)], None),
        }

    def test_classes(self, tmp_path: Path) -> None:
        """Checks DOCS01.

        The signature of a dataclass or named tuple holds its fields with their annotations and defaults, given
        directly or by field, without its class variables, and that of any other class is empty.
        """

        ## a dataclass, a named tuple and another class, each with annotated names in its body
        root = tree(tmp_path, {
            "src/module.py": "\n".join([
                'from dataclasses import dataclass, field',
                'from typing import ClassVar, NamedTuple',
                '@dataclass(frozen = True)',
                'class Data:',
                '    table: ClassVar[str] = "units"',
                '    mass: float = field(default = 1.0, metadata = {"unit": "g"})',
                '    items: list[int] = field(default_factory = list)',
                '    name: str = "cloud"',
                '    size: int',
                'class Pair(NamedTuple):',
                '    first: int',
                '    second: int = 2',
                'class Plain:',
                '    value: int = 1',
            ]),
        })

        ## the fields of each class, by name
        assert {documented.name: documented.parameters for documented in read_objects(root)} == {
            "src/module.py::Data": [
                Parameter("mass", "float", "1.0"),
                Parameter("items", "list[int]", None),
                Parameter("name", "str", '"cloud"'),
                Parameter("size", "int", None),
            ],
            "src/module.py::Pair": [Parameter("first", "int", None), Parameter("second", "int", "2")],
            "src/module.py::Plain": [],
        }


    def test_sections(self, tmp_path: Path) -> None:
        """Checks DOCS02.

        The sections Parameters and Returns are found by their titles and rules, their entries are their lines at the
        indentation of the title up to the first blank line, and a malformed title or rule hides its section.
        """

        ## one function whose docstring holds both sections, one with a malformed title and a malformed rule, and one
        ## without a docstring
        root = tree(tmp_path, {
            "src/module.py": "\n".join([
                'def function():',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    mass : float (default = 1.0)',
                '        The mass.',
                '    *arguments : str',
                '        The arguments,',
                '        on two lines.',
                '    length: float',
                '',
                '    Returns',
                '    =======',
                '    tuple[int, int]',
                '        A pair.',
                '',
                '    Implements FOO01.',
                '    """',
                'def malformed():',
                '    """Do something.',
                '',
                '    Parameters:',
                '    ===========',
                '    mass : float',
                '',
                '    Returns',
                '    -------',
                '    int',
                '    """',
                'def bare():',
                '    pass',
            ]),
        })

        ## the entries of each, where a malformed entry is read as a name alone
        assert {documented.name: (documented.entries, documented.returned) for documented in read_objects(root)} == {
            "src/module.py::function": ([
                Parameter("mass", "float", "1.0"),
                Parameter("*arguments", "str", None),
                Parameter("length: float", None, None),
            ], ["tuple[int, int]"]),
            "src/module.py::malformed": ([], None),
            "src/module.py::bare": ([], None),
        }


class TestParameters:
    """Tests that the check fails on entries of Parameters whose names, types or defaults differ from the code."""

    ## a module that the check passes, to which each test below adds one fault
    FILES = {
        "src/module.py": "\n".join([
            'from dataclasses import dataclass',
            '@dataclass',
            'class Data:',
            '    """Hold data.',
            '',
            '    Parameters',
            '    ==========',
            '    mass : float (default = 1.0)',
            '        The mass.',
            '    """',
            '    mass: float = 1.0',
            'def function(a: int, *b: str) -> None:',
            '    """Do something.',
            '',
            '    Parameters',
            '    ==========',
            '    a : int',
            '        The first.',
            '    *b : str',
            '        The rest.',
            '    """',
        ]),
    }

    def test_files(self, tmp_path: Path) -> None:
        """Checks DOCS03, DOCS04 and DOCS05.

        The check passes on the tree of the other tests before a fault is added to it.
        """

        ## the tree of FILES alone, on which the check returns rather than fails
        check(tree(tmp_path, self.FILES))


    def test_names(self, tmp_path: Path) -> None:
        """Checks DOCS03.

        The check fails on entries that do not name the parameters or fields in their order and without others, and
        names each object with the names of both.
        """

        ## the tree of FILES, with functions whose entries miss a parameter, add one, swap two, or join two in one
        root = tree(tmp_path, self.FILES | {
            "src/second.py": "\n".join([
                'def missing(a: int, b: int) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : int',
                '        The first.',
                '    """',
                'def extra() -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : int',
                '        The first.',
                '    """',
                'def swapped(a: int, b: int) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    b : int',
                '        The second.',
                '    a : int',
                '        The first.',
                '    """',
                'def joined(a: int, b: int) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a, b',
                '        Both.',
                '    """',
            ]),
        })

        lines = failure(root)
        ## one line names each of the four functions, and none names an object of FILES
        assert any("src/second.py::missing" in line and "a, b" in line for line in lines), lines
        assert any("src/second.py::extra documents a for" in line for line in lines), lines
        assert any("src/second.py::swapped" in line and "b, a" in line for line in lines), lines
        assert any("src/second.py::joined" in line for line in lines), lines
        assert not any("src/module.py" in line for line in lines), lines


    def test_types(self, tmp_path: Path) -> None:
        """Checks DOCS04.

        The check fails on an entry whose type differs from the annotation as written, or whose parameter has no
        annotation, and names the object and the entry with both types.
        """

        ## the tree of FILES, with a field typed otherwise, an entry and an annotation each spaced otherwise, and two
        ## parameters without annotation, one documented with a type and one without
        root = tree(tmp_path, self.FILES | {
            "src/second.py": "\n".join([
                'from dataclasses import dataclass',
                '@dataclass',
                'class Data:',
                '    """Hold data.',
                '',
                '    Parameters',
                '    ==========',
                '    mass : int',
                '        The mass.',
                '    """',
                '    mass: float',
                'def spaced(a: tuple[int, int]) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : tuple[int,int]',
                '        The pair.',
                '    """',
                'def unspaced(a: tuple[int,int]) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : tuple[int, int]',
                '        The pair.',
                '    """',
                'def bare(a) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : int',
                '        The first.',
                '    """',
                'def untyped(a) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a',
                '        The first.',
                '    """',
            ]),
        })

        lines = failure(root)
        ## one line names each object with its entry and both types
        assert any("src/second.py::Data" in line and "'int'" in line and "'float'" in line for line in lines), lines
        assert any("src/second.py::spaced" in line and "'tuple[int,int]'" in line for line in lines), lines
        assert any("src/second.py::unspaced" in line and "'tuple[int,int]'" in line for line in lines), lines
        assert any("src/second.py::bare" in line and "'int'" in line and "None" in line for line in lines), lines
        assert any("src/second.py::untyped" in line and "None" in line for line in lines), lines


    def test_defaults(self, tmp_path: Path) -> None:
        """Checks DOCS05.

        The check fails on an entry whose default differs from the default as written, or that shows a default where
        the code has none or none where it has one, and names the object and the entry with both defaults.
        """

        ## the tree of FILES, with a default written otherwise, one missing from the entry, and one not in the code
        root = tree(tmp_path, self.FILES | {
            "src/second.py": "\n".join([
                'from dataclasses import dataclass, field',
                '@dataclass',
                'class Data:',
                '    """Hold data.',
                '',
                '    Parameters',
                '    ==========',
                '    mass : float (default = 100000.0)',
                '        The mass.',
                '    """',
                '    mass: float = field(default = 1e5)',
                'def missing(a: int = 1) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : int',
                '        The first.',
                '    """',
                'def extra(a: int) -> None:',
                '    """Do something.',
                '',
                '    Parameters',
                '    ==========',
                '    a : int (default = 1)',
                '        The first.',
                '    """',
            ]),
        })

        lines = failure(root)
        ## one line names each object with its entry and both defaults
        assert any("src/second.py::Data" in line and "'100000.0'" in line and "'1e5'" in line for line in lines), lines
        assert any("src/second.py::missing" in line and "None" in line and "'1'" in line for line in lines), lines
        assert any("src/second.py::extra" in line and "'1'" in line and "None" in line for line in lines), lines


class TestReturns:
    """Tests that the check fails on a section Returns that is missing, out of place, or of another type."""

    ## a module that the check passes, to which each test below adds one fault
    FILES = {
        "src/module.py": "\n".join([
            'def function() -> int:',
            '    """Return something.',
            '',
            '    Returns',
            '    =======',
            '    int',
            '        Something.',
            '    """',
        ]),
    }


    def test_files(self, tmp_path: Path) -> None:
        """Checks DOCS06 and DOCS07.

        The check passes on the tree of the other tests before a fault is added to it.
        """

        ## the tree of FILES alone, on which the check returns rather than fails
        check(tree(tmp_path, self.FILES))


    def test_presence(self, tmp_path: Path) -> None:
        """Checks DOCS06.

        The check fails on a function that returns a value without Returns, and on Returns where the return
        annotation is missing or None, and names the object.
        """

        ## the tree of FILES, with Returns missing, and Returns beside None, beside no annotation and in a class
        returns = ['    """Do something.', '', '    Returns', '    =======', '    int', '    """']
        root = tree(tmp_path, self.FILES | {
            "src/second.py": "\n".join([
                'def missing() -> int:',
                '    """Return something."""',
                'def none() -> None:',
                *returns,
                'def bare():',
                *returns,
                'class Group:',
                *returns,
            ]),
        })

        lines = failure(root)
        ## one line names each of the four objects, and none names the function of FILES
        for name in ["missing", "none", "bare", "Group"]:
            assert any(f"src/second.py::{name} " in line for line in lines), lines
        assert not any("src/module.py" in line for line in lines), lines


    def test_type(self, tmp_path: Path) -> None:
        """Checks DOCS07.

        The check fails on Returns whose entry differs from the return annotation as written, or that holds other
        than one entry, and names the object with both.
        """

        ## the tree of FILES, with Returns of another type, of two entries and of none, and Returns beside an annotation
        ## spaced otherwise
        root = tree(tmp_path, self.FILES | {
            "src/second.py": "\n".join([
                'def other() -> int:',
                '    """Return something.',
                '',
                '    Returns',
                '    =======',
                '    float',
                '    """',
                'def two() -> int:',
                '    """Return something.',
                '',
                '    Returns',
                '    =======',
                '    int',
                '    int',
                '    """',
                'def empty() -> int:',
                '    """Return something.',
                '',
                '    Returns',
                '    =======',
                '    """',
                'def unspaced() -> tuple[int,int]:',
                '    """Return something.',
                '',
                '    Returns',
                '    =======',
                '    tuple[int, int]',
                '    """',
            ]),
        })

        lines = failure(root)
        ## one line names each function with both
        assert any("src/second.py::other" in line and "'float'" in line and "'int'" in line for line in lines), lines
        assert any("src/second.py::two" in line and "'int', 'int'" in line for line in lines), lines
        assert any("src/second.py::empty" in line and "[]" in line for line in lines), lines
        assert any("src/second.py::unspaced" in line and "'tuple[int,int]'" in line for line in lines), lines


class TestMhdpy:
    """Tests that the docstrings of mhdpy outside the tests give the check none of its faults."""

    def test_docstrings(self) -> None:
        """Checks DOCS08.

        The check passes on this checkout, as every docstring outside the tests repeats the signature of its code.
        """

        ## the check run on this checkout rather than on a small tree
        check(ROOT)


def check(root: Path) -> None:
    """Fail on each docstring outside the tests below root that does not repeat the signature of its code.

    Parameters
    ====================================================================================================================
    root : Path
        The root of the tree whose modules are checked, as the checkout of mhdpy.

    Raises
    ====================================================================================================================
    AssertionError
        If an entry misnames, mistypes or misstates the default of a parameter or field, or Returns is missing, out
        of place or of another type, with a message that names each fault on a line of its own.
    """

    objects = read_objects(root)
    faults = [
        *misnamed_parameters(objects),
        *mistyped_parameters(objects),
        *mistaken_defaults(objects),
        *misplaced_returns(objects),
        *mistyped_returns(objects),
    ]
    assert not faults, "\n".join(faults)


def class_signature(cls: ast.ClassDef, source: str) -> list[Parameter]:
    """Return the fields of a dataclass or named tuple, and no field for any other class.

    Parameters
    ====================================================================================================================
    cls : ast.ClassDef
        The class, as ast reads it from source.
    source : str
        The source of its module.

    Returns
    ====================================================================================================================
    list[Parameter]
        The names annotated in the body of the class, other than its class variables, in their order, each with its
        annotation and its default, given directly or by the keyword default of field.

    Implements DOCS01.
    """

    kinds = [last_name(expression) for expression in [*cls.decorator_list, *cls.bases]]
    if "dataclass" not in kinds and "NamedTuple" not in kinds:
        return []

    fields: list[Parameter] = []
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if last_name(node.annotation) == "ClassVar":
                continue

            ## a default given directly, or by the keyword default of field
            default = node.value
            if isinstance(default, ast.Call) and last_name(default) == "field":
                default = next((keyword.value for keyword in default.keywords if keyword.arg == "default"), None)
            fields.append(Parameter(node.target.id, text(node.annotation, source), text(default, source)))
    return fields


def failure(root: Path) -> list[str]:
    """Return the lines of the message with which the check fails on the tree at root.

    Parameters
    ====================================================================================================================
    root : Path
        The root of a tree on which the check must fail, as the temporary folder of a test.

    Returns
    ====================================================================================================================
    list[str]
        The lines of the message, one for each fault.
    """

    with pytest.raises(AssertionError) as error:
        check(root)
    return str(error.value).splitlines()


def function_signature(function: ast.FunctionDef, source: str, method: bool) -> tuple[list[Parameter], str | None]:
    """Return the parameters of a function and its return annotation.

    Parameters
    ====================================================================================================================
    function : ast.FunctionDef
        The function, as ast reads it from source.
    source : str
        The source of its module.
    method : bool
        Whether the function lies in the body of a class.

    Returns
    ====================================================================================================================
    tuple[list[Parameter], str | None]
        The parameters in their order, without the first parameter of a method that is not static, and the return
        annotation as the source holds it, or None where it is missing or None.

    Implements DOCS01.
    """

    arguments = function.args
    positional = [*arguments.posonlyargs, *arguments.args]

    ## the defaults belong to the last positional parameters
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(arguments.defaults))
    defaults += arguments.defaults
    parameters = [Parameter(a.arg, text(a.annotation, source), text(d, source)) for a, d in zip(positional, defaults)]

    ## the first parameter of a method, as self, which no caller passes
    if method and "staticmethod" not in [last_name(decorator) for decorator in function.decorator_list]:
        parameters = parameters[1:]

    if arguments.vararg:
        parameters.append(Parameter(f"*{arguments.vararg.arg}", text(arguments.vararg.annotation, source), None))
    for a, d in zip(arguments.kwonlyargs, arguments.kw_defaults):
        parameters.append(Parameter(a.arg, text(a.annotation, source), text(d, source)))
    if arguments.kwarg:
        parameters.append(Parameter(f"**{arguments.kwarg.arg}", text(arguments.kwarg.annotation, source), None))

    returns = text(function.returns, source)
    return parameters, None if returns == "None" else returns


def last_name(expression: ast.expr) -> str:
    """Return the last name of a name, a dotted name, a call or a subscript.

    Parameters
    ====================================================================================================================
    expression : ast.expr
        A decorator, base or annotation, as dataclass(frozen = True), typing.NamedTuple or ClassVar[str].

    Returns
    ====================================================================================================================
    str
        The last name, as dataclass, NamedTuple or ClassVar.
    """

    if isinstance(expression, ast.Call):
        expression = expression.func
    if isinstance(expression, ast.Subscript):
        expression = expression.value
    return ast.unparse(expression).split(".")[-1]


def misnamed_parameters(objects: list[Documented]) -> list[str]:
    """Return a fault for each object whose entries do not name its parameters or fields in their order.

    Parameters
    ====================================================================================================================
    objects : list[Documented]
        The objects, as read_objects returns them.

    Returns
    ====================================================================================================================
    list[str]
        The faults as lines of text, such as "src/module.py::function documents b, a for the parameters a, b", and an
        empty list where every object documents its parameters.

    Implements DOCS03.
    """

    faults: list[str] = []
    for documented in objects:
        ## the names as lists, so that one entry "a, b" does not pass for the two parameters a and b
        documented_names = [entry.name for entry in documented.entries]
        names = [parameter.name for parameter in documented.parameters]
        if documented_names != names:
            listed = ", ".join(documented_names) or "nothing"
            faults.append(f"{documented.name} documents {listed} for the parameters {', '.join(names)}")
    return faults


def misplaced_returns(objects: list[Documented]) -> list[str]:
    """Return a fault for each object whose docstring has Returns without a return annotation, or lacks it with one.

    Parameters
    ====================================================================================================================
    objects : list[Documented]
        The objects, as read_objects returns them.

    Returns
    ====================================================================================================================
    list[str]
        The faults as lines of text, such as "src/module.py::function has Returns but no return annotation", and an
        empty list where Returns stands exactly where a return annotation other than None does.

    Implements DOCS06.
    """

    faults: list[str] = []
    for documented in objects:
        if documented.returned is not None and documented.returns is None:
            faults.append(f"{documented.name} has Returns but no return annotation")
        elif documented.returned is None and documented.returns is not None:
            faults.append(f"{documented.name} returns {documented.returns} but has no Returns")
    return faults


def mistaken_defaults(objects: list[Documented]) -> list[str]:
    """Return a fault for each entry whose default differs from that of its parameter or field.

    Parameters
    ====================================================================================================================
    objects : list[Documented]
        The objects, as read_objects returns them.

    Returns
    ====================================================================================================================
    list[str]
        The faults as lines of text, such as "src/module.py::function documents the default of a as '2', the code
        gives '1'", and an empty list where every default agrees.

    Implements DOCS05.
    """

    return [
        f"{documented.name} documents the default of {entry.name} as {entry.default!r}, the code gives "
        f"{parameter.default!r}"
        for documented in objects
        for entry in documented.entries
        for parameter in documented.parameters
        if entry.name == parameter.name and entry.default != parameter.default
    ]


def mistyped_parameters(objects: list[Documented]) -> list[str]:
    """Return a fault for each entry whose type differs from the annotation of its parameter or field.

    Parameters
    ====================================================================================================================
    objects : list[Documented]
        The objects, as read_objects returns them.

    Returns
    ====================================================================================================================
    list[str]
        The faults as lines of text, such as "src/module.py::function documents the type of a as 'float', the code
        gives 'int'", and an empty list where every type agrees.

    Implements DOCS04.
    """

    return [
        f"{documented.name} documents the type of {entry.name} as {entry.type!r}, the code gives {parameter.type!r}"
        for documented in objects
        for entry in documented.entries
        for parameter in documented.parameters
        ## a parameter without annotation fails, even where its entry gives no type either
        if entry.name == parameter.name and (parameter.type is None or entry.type != parameter.type)
    ]


def mistyped_returns(objects: list[Documented]) -> list[str]:
    """Return a fault for each Returns that holds other than one entry, or whose entry differs from the annotation.

    Parameters
    ====================================================================================================================
    objects : list[Documented]
        The objects, as read_objects returns them.

    Returns
    ====================================================================================================================
    list[str]
        The faults as lines of text, such as "src/module.py::function documents the return as ['float'], the code
        gives 'int'", and an empty list where every Returns agrees.

    Implements DOCS07.
    """

    return [
        f"{documented.name} documents the return as {documented.returned}, the code gives {documented.returns!r}"
        for documented in objects
        if documented.returned is not None and documented.returns is not None
        and documented.returned != [documented.returns]
    ]


def read_docstring(name: str, parameters: list[Parameter], returns: str | None, docstring: str | None) -> Documented:
    """Return an object with its signature and the entries of the sections Parameters and Returns of its docstring.

    Parameters
    ====================================================================================================================
    name : str
        The path of its module and its qualified name, as src/mhdpy/infrastructure/units.py::Units.factor.
    parameters : list[Parameter]
        The parameters of the function or the fields of the class, as the code gives them.
    returns : str | None
        The return annotation as the source holds it, or None where it is missing or None.
    docstring : str | None
        The docstring as ast.get_docstring gives it, or None where the object has none.

    Returns
    ====================================================================================================================
    Documented
        The object, with each entry of Parameters read as name : type (default = value), and a line in another form
        read as a name alone.

    Implements DOCS02.
    """

    sections = read_sections(docstring or "")
    entries: list[Parameter] = []
    for line in sections.get("Parameters", []):
        match = ENTRY.fullmatch(line)
        entries.append(Parameter(match[1], match[2], match[3]) if match else Parameter(line, None, None))
    return Documented(name, parameters, returns, entries, sections.get("Returns"))


def read_object(node: ast.stmt, prefix: str, source: str, method: bool) -> list[Documented]:
    """Return the object that a statement defines, with those in its body if it is a class.

    Parameters
    ====================================================================================================================
    node : ast.stmt
        A statement at the head of a module or in the body of a class, as ast reads it from source.
    prefix : str
        The path of the module and the qualified name of the class around it, as src/module.py::Units.
    source : str
        The source of its module.
    method : bool
        Whether the statement lies in the body of a class.

    Returns
    ====================================================================================================================
    list[Documented]
        The function or class that the statement defines, followed by the objects in the body of a class, and an
        empty list for a property and any other statement.

    Implements DOCS01.
    """

    if isinstance(node, ast.FunctionDef):
        ## a property, whose docstring keeps a summary alone
        if {"property", "cached_property"} & {last_name(decorator) for decorator in node.decorator_list}:
            return []
        parameters, returns = function_signature(node, source, method)
        return [read_docstring(prefix + node.name, parameters, returns, ast.get_docstring(node))]

    if isinstance(node, ast.ClassDef):
        objects = [read_docstring(prefix + node.name, class_signature(node, source), None, ast.get_docstring(node))]
        for child in node.body:
            objects.extend(read_object(child, f"{prefix}{node.name}.", source, method = True))
        return objects

    return []


def read_objects(root: Path) -> list[Documented]:
    """Return every object outside the tests in the modules below root/src and root/tests, in the order of their paths.

    Parameters
    ====================================================================================================================
    root : Path
        The root of the tree whose modules are read, as the checkout of mhdpy.

    Returns
    ====================================================================================================================
    list[Documented]
        One for each function or class at the head of a module or in the body of such a class, other than the
        tests, the classes of tests with all that they hold, and the properties, in the order of their lines.

    Implements DOCS01.
    """

    objects: list[Documented] = []
    for path in sorted({*(root / "src").rglob("*.py"), *(root / "tests").rglob("*.py")}):
        module = path.relative_to(root).as_posix()
        source = path.read_text()
        tests = module.startswith("tests/") and (path.name.startswith("test_") or path.name.endswith("_test.py"))

        for node in ast.parse(source, filename = path).body:
            ## the tests at the head of a test module, and the classes of tests with all that they hold
            if tests and isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                continue
            if tests and isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                continue
            objects.extend(read_object(node, f"{module}::", source, method = False))
    return objects


def read_sections(docstring: str) -> dict[str, list[str]]:
    """Return the entries of the sections Parameters and Returns of a docstring, by title.

    Parameters
    ====================================================================================================================
    docstring : str
        The docstring, as ast.get_docstring gives it.

    Returns
    ====================================================================================================================
    dict[str, list[str]]
        The entries of each section, its lines at the indentation of its title up to the first blank line, each
        without its indentation. A title counts only on a line of its own, followed by a line of = alone.

    Implements DOCS02.
    """

    sections: dict[str, list[str]] = {}
    lines = docstring.splitlines()
    for number, line in enumerate(lines[:-1]):
        if line.strip() in TITLES and RULE.fullmatch(lines[number + 1].strip()):
            indentation = len(line) - len(line.lstrip())
            entries: list[str] = []

            ## the lines up to the first blank line, of which the entries stand at the indentation of the title
            for below in lines[number + 2:]:
                if not below.strip():
                    break
                if len(below) - len(below.lstrip()) == indentation:
                    entries.append(below.strip())
            sections[line.strip()] = entries
    return sections


def text(node: ast.expr | None, source: str) -> str | None:
    """Return the source text of an annotation or default, or None where there is none.

    Parameters
    ====================================================================================================================
    node : ast.expr | None
        The annotation or default, as ast reads it from source, or None.
    source : str
        The source of its module.

    Returns
    ====================================================================================================================
    str | None
        The text as written, such as 1e5 or tuple[int, int], or None where node is None.
    """

    return None if node is None else ast.get_source_segment(source, node)

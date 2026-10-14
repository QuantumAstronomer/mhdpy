# Requirements

Every component of mhdpy is specified by its requirements before it is built (decision D02.1: test-first development). The requirements of a component are written down first, then turned into tests, and only then is the code written that fulfils them. This folder holds those requirements.

## Layout

The requirements are organised by the layers of the architecture ([architecture.md §3](../architecture.md)), one folder per layer and one document per component:

```text
docs/requirements/
├── L0-foundation/
├── L1-data-and-geometry/
├── L2-communication/
├── L3-execution/
├── L4-numerical-building-blocks/
├── L5-time-integration/
├── L6-simulation-and-driver/
└── L7-files-and-interface/
```

Physics modules sit across layers L1–L5. Their requirements live in a folder of their own, `modules/`, once the first module is specified.

## Requirement identifiers

Every requirement has an identifier of the form `UNI01`, without a separator:

- **three capital letters,** the first three of the component's name (`UNI` for units);
- **a two-digit number,** counting up within the component. A component that would outgrow 99 requirements should be split.

Identifiers are unique across the whole project, so that a test, a decision brief or another requirement can cite one without ambiguity. Two rules keep them so:

- **A prefix belongs to one component.** When the first three letters of a new component's name are already taken, it chooses three other letters from its name. Every prefix in use is listed in the register below.
- **An identifier is never reused.** A requirement that is dropped keeps its identifier and is marked *withdrawn*, with the reason; one that changes is rewritten in place, with the date of the change. References made earlier never change meaning silently.

## Requirement documents

Each component's document contains:

- **Purpose:** what the component is for, in a few sentences, and where it sits among the other components.
- **Sources:** the decision briefs (and sub-decisions) the requirements derive from.
- **Requirements:** numbered, each a single verifiable statement, with a short note on its reason or source where that is not obvious. A requirement states *what* must hold, not *how* it is achieved.
- **Open points:** questions still to be settled before the component is complete, if any.

A requirement is written so that a test can decide whether it holds. "Conversions are accurate" is not a requirement; "a round trip from code units to cgs and back reproduces the value to within 4 ulp" is.

## From requirements to tests

Every requirement is checked by at least one test, and every test names the requirements it checks in its docstring, for example:

```python
def test_round_trip() -> None:
    """Check that converting to cgs and back reproduces the value (UNI06)."""
```

The verification matrix of D02.9 is compiled from these references: which requirement is checked by which tests, and whether they pass.

## Register of prefixes

| Prefix | Component | Layer | Document |
|---|---|---|---|
| `PAR` | Parameters | L0 | [L0-foundation/parameters.md](L0-foundation/parameters.md) |
| `UNI` | Units | L0 | [L0-foundation/units.md](L0-foundation/units.md) |

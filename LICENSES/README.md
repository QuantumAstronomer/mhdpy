# Third-party licences

mhdpy itself is licensed under BSD-3-Clause (decision D01.3). This folder holds the licences of third-party works from which material is reused in mhdpy's code, comments or documentation. The copyright notice and licence text of every reused source are kept here, as their licences require.

| File | Source | Licence |
|---|---|---|
| [`athena.txt`](athena.txt) | Athena++ — Princeton University | BSD-3-Clause |
| [`pyro.txt`](pyro.txt) | Pyro — pyro development team | BSD-3-Clause |
| [`ulula.txt`](ulula.txt) | Ulula — Benedikt Diemer | MIT |

## Convention

Wherever material from one of these sources is copied or adapted, a comment names the source file and the licence, and points to the licence text here:

```python
## Adapted from Athena++, src/hydro/rsolvers/hydro/hllc.cpp
## (BSD-3-Clause, see LICENSES/athena.txt).
```

In documentation, the same information is given as a short note or footnote.

- **Code from the reference codes** (above) may be reused under this convention.
- **Figures** are not copied from papers or from the CompHydro book. Papers are copyrighted by their publishers, and the book's CC BY-NC-SA licence would carry over to any page containing its figures. Figures are redrawn instead, from mhdpy's own experiments, and the original source is cited.
- **Text and equations** from papers may be cited, and short passages quoted with attribution.

A new source is added to this folder, with its licence text and a row in the table above, before any of its material is used.

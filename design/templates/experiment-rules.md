# Rules of the experiments

Where the references leave a question of a brief open, an experiment supplies the evidence, with the smallest code that answers its question (§2.4). This file explains each part of the skeleton `experiment.md` and the reason for it, how experiments are named and laid out, how their code is written and run, and what of them is committed. Section signs refer to CLAUDE.md, and plain numbers to the parts of this file. In the skeleton, braces mark values to fill in, and italic lines describe the prose that replaces them.

## 1. Files and identifiers

An experiment belongs to one brief. It is identified by the identifier of the brief, the letter E and a number, as B7E1, after the pattern of the sub-decisions. The number is given when the plan is written and is never reused. The experiments of a brief lie in a folder of `design/experiments/` that bears the name of the brief, made with the first of them, and each lies in a folder of its own, named by the letter and number and by its subject in lower case, with hyphens and without articles or commas, as `design/experiments/B07-riemann-solvers/E1-cost-of-hllc/`. An experiment that a later brief draws on stays where it is and is cited there by its identifier.

The folder of an experiment holds five things.

- `README.md`, the record, begun from the skeleton. GitHub shows it below the files when the folder is browsed.
- `run.py`, which computes the results and saves them in `results/`.
- `plot.py`, which reads the saved results and draws the figures into `figures/`, so that a change of style does not require the computation to run again (§3.3).
- `results/`, the numbers on which the answer and the figures rest, with `environment.json`, the record of what produced them (3).
- `figures/`, the figures that `plot.py` draws.

A brief cites an experiment by a link whose text is its identifier, as [B7E1](../experiments/B07-riemann-solvers/E1-cost-of-hllc/README.md), and commit messages by the identifier alone.

## 2. The record

The head names, with links, the sub-decision that the experiment serves, and any other of the same brief. Its status reads "Planned." while the plan is written, "Agreed on {date}." once the author has agreed it, and "Run on {date}." once the results are in. Six parts follow, under headings.

**Answer.** Written last but placed first, as the decision of a brief, since it is what a reader of the experiment looks for. Until the run, it reads "Not yet run." It then answers the question in a few sentences, sets the result against the expectation where there is one, and states the limits of the result, such as the machine, the grid or the versions to which it is bound. It holds no recommendation, which stays in the brief (§2.4).

**Question.** The one question that the experiment answers and why the references leave it open. It names the measure on which the sub-decision turns, such as the time of a whole step rather than of its parts, and says what each possible value of that measure would mean for the sub-decision. An experiment none of whose answers would change the decision is not needed, and this part shows so before any code is written.

**Expectation.** What is expected and why, written before the run, so that the result can confirm or correct it. The part is left out where no expectation can be argued, so that none is invented.

**Method.** The smallest computation that answers the question: what is computed and measured, on which problem, grid and parameters. An experiment that times code runs it once to warm up, which leaves compilation out, then repeats it and reports the median with the minimum and maximum, so that both the typical speed and its spread show. Where it applies, the time is also given as cell updates per second, the rate that §1.3 tracks. An experiment that compares implementations first checks that they give the same result, so that no version is fast because it is wrong.

**Results.** The figures and numbers as measured, without interpretation, with the machine and versions from `results/environment.json`. A deviation from the plan, such as a grid made smaller because the first runs took too long, is stated here with its reason. A result that the plan did not foresee is reported apart, under a note that says so. The answer may name it as a limit, while the rule of the plan still decides.

**Rerun.** The commands that rerun the experiment in its folder, `uv run run.py` and `uv run plot.py`, and how long they take on the development machine.

The question, the expectation and the method form the plan. The plan comes to the author before any code is written, is agreed and is then kept unchanged, as in a registered report, while the results and the answer follow the run. The record therefore shows both what was expected and what was found.

## 3. The code

The scripts follow §3.2 in full, strict type checking included, since evidence must be right before anything else (§1.4). `run.py` begins with the directive `# pyright: strict`. `plot.py` begins with `# pyright: strict, reportUnknownMemberType=false`, as the type stubs of matplotlib leave the keyword arguments of its methods untyped, so that strict checking would flag every call, while every other check stays. Each script is checked against the environment that uv builds for it:

```
uvx pyright --pythonpath "$(uv python find --script run.py)" run.py
```

The code is the smallest that answers the question and is not an early version of mhdpy (§2.4). Nothing of it moves into mhdpy, and experiments do not import each other. Once mhdpy exists, an experiment may import it, installed from a commit that the experiment records. Random seeds are fixed, so that a rerun repeats the computation.

Below the directive, each script declares its Python version and packages in the inline metadata of PEP 723, and `uv run` builds the environment that it declares, with nothing to install beforehand. Like the directive, the lines begin with a single hash, as they speak to tools (§3.2).

```python
# pyright: strict
# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy>=2.1"]
# ///
```

`run.py` writes `results/environment.json` with the date, the Python version and whether its build is free-threaded, the versions of the packages, the machine with its processor, and the commit of the repository, marked where the working tree differs from it. Every result thus names what produced it. `plot.py` reads only the saved results, and its figures follow §3.3.

## 4. What is committed

The record, the scripts, the results on which the answer and the figures rest, and the figures are committed, so that any clone shows the evidence and can redraw it. The results are reduced to what the answer and the figures need, in text where possible, and stay below about 1 MB for an experiment. Larger raw output goes to `results/raw/`, which git ignores, and is regenerated by `run.py`.

## 5. The life of an experiment

An experiment is written in two stages: its plan, agreed before any code is written, and its results, after the run. An experiment whose plan was agreed but that proves unnecessary before it runs keeps its number, and its status reads "Withdrawn on {date}." with the reason. Once the brief that it serves is decided, the experiment is frozen with it, as part of its record. A later run that gives other results, on newer versions for instance, is a new experiment rather than a revision.

## 6. Sources

**[GK]** The two stages of the record follow the registered reports of [Chambers](#chambers-2013) (2013), whose question, hypotheses and method are reviewed before any data exist, and whose analyses beyond the plan are reported apart. The rules on the code follow the ten simple rules of [Sandve et al.](#sandve-et-al-2013) (2013): a script behind every result, no manual steps, recorded versions and seeds, and the data behind every figure kept. The environment of each script is declared after [PEP 723](#pep-723).

- <a id="chambers-2013"></a>Chambers, C. D., Registered reports: a new publishing initiative at Cortex, Cortex 49, 609–610 (2013), [doi:10.1016/j.cortex.2012.12.016](https://doi.org/10.1016/j.cortex.2012.12.016).
- <a id="pep-723"></a>PEP 723, Inline script metadata, Python Enhancement Proposals, [peps.python.org/pep-0723](https://peps.python.org/pep-0723/).
- <a id="sandve-et-al-2013"></a>Sandve, G. K., Nekrutenko, A., Taylor, J. and Hovig, E., Ten simple rules for reproducible computational research, PLoS Computational Biology 9, e1003285 (2013), [doi:10.1371/journal.pcbi.1003285](https://doi.org/10.1371/journal.pcbi.1003285).

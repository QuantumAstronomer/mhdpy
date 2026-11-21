"""The driver and the problems, stratum 5.

The code that turns the solver into a run: the main loop and the control of its step, problem setups and user
functions, outputs, restarts and analysis, and the problems that verify the whole scheme. The driver reads the
parameters, lets a problem setup build the initial state, and takes steps until the run ends, sharing the blocks of each
stage among a pool of threads, so that a run gives the same result on any number of threads.

The stratum rests on all four below it, and as the top stratum it provides to no stratum above, but its loop, hooks and
outputs must take in every extension without change to the framework. Its tests lie in tests/driver/. It closes the
first pass: the problems of the whole scheme must meet their known solutions and reference results, a restart must
reproduce an uninterrupted run bit for bit, and a run on six threads the serial run exactly.

Its requirements will lie in design/requirements/driver/, and §3.5 of design/overview.md sets out the stratum.
"""

# Contributing

Thanks for your interest in the project.

This is a research codebase with frozen evidence contracts, so contributions should distinguish **engineering changes** from **scientific changes**.

## Development setup

~~~bash
git clone https://github.com/Frysland-2024/AI4science.git
cd AI4science/xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q -m "not data_bound"
~~~

## Pull requests

Please state:

1. what is changing;
2. whether the change is engineering-only or changes a scientific factor;
3. which tests were run;
4. whether any tracked result/config/provenance artifact changes.

For scientific changes, explain which frozen assumptions or claims are affected.

## Research-integrity rules

Do not:

- change frozen test data after seeing results;
- silently replace selected checkpoints, seeds, or metrics;
- remove unfavorable results because they are inconvenient;
- commit private laboratory data or third-party data that cannot be redistributed;
- commit credentials, API keys, checkpoints, or large generated arrays.

If a scientific claim changes, update the relevant current-state / evidence document together with the code.

## Code style

The project prioritizes readable, explicit research code over framework-heavy abstraction. Preserve deterministic behavior and provenance checks where they exist.

## Third-party components

If code is copied, ported, or substantially adapted from another project, preserve its license notice and add it to THIRD_PARTY_NOTICES.md.

# Bootstrap Prompt for Codex

Paste the text below into Codex as the first task in the repository.

---

You are helping implement an AI4Science research project on robust 1D powder-XRD crystal-system/symmetry classification under physically motivated measurement perturbations.

Before editing anything, read these files in order:

1. `AGENTS.md`
2. `context/00_CURRENT_STATE.md`
3. `context/02_SIMXRD_XRD_RELIABILITY_SPEC.md`
4. `context/03_EXPERIMENT_PROTOCOL.md`
5. `context/04_PHYSICAL_VALIDITY.md`
6. `context/10_KNOWN_UNCERTAINTIES.md`
7. `context/11_TASK_QUEUE.md`

Then inspect the repository and return only:

1. a concise inventory of code/data/config assets actually present;
2. the current blockers or missing metadata;
3. the safest next P0 task;
4. a minimal implementation plan with tests;
5. any question that cannot be resolved without the user.

Do not invent dataset schema, label order, perturbation ranges, or real-XRD claims. Do not train a model yet unless the data schema and split key are verified.

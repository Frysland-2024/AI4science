# AI4science Repository Instructions

Before working on the XRD project, read:

1. `00_project_context/CURRENT_STATE.md`
2. `00_project_context/PROJECT_JOURNEY.md`
3. `xrd_robustness/CODEX_HANDOFF.md`
4. `xrd_robustness/README.md`

At the end of every meaningful task:

1. Update `00_project_context/CURRENT_STATE.md` with completed work, current blocker, experiment status, and next actions.
2. When a scientific decision or research direction changes, append the reasoning to `00_project_context/PROJECT_JOURNEY.md`.
3. Never erase historical research decisions just because the current plan changes.
4. Clearly distinguish:
   - scientific design
   - engineering implementation
   - completed evidence
   - assumptions
   - unresolved risks

5. Do not commit:
   - datasets
   - checkpoints
   - generated spectra
   - caches
   - API keys
   - credentials
   - large third-party repositories

6. Before handing work back, report:
   - files changed
   - tests executed
   - tests passed or failed
   - remaining blocker
   - exact next command

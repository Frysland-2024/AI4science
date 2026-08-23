# AI4science Repository Instructions

## Journal Indexing Skill

`check-journal-indexing` is optional. Use it only when a task specifically
requires verification of journal or paper coverage in SCIE, EI Compendex, or
CSCD; it is not a prerequisite for other repository tasks.

## Default GitHub Repository Policy

For all project-related questions, progress reviews, scientific decisions, code
inspection, experiment status checks, application narratives, and planning tasks,
the default and authoritative GitHub repository is:

```text
Frysland-2024/AI4science
```

Apply the following rules:

1. Read `Frysland-2024/AI4science` by default before answering any current
   project question. Do not rely only on chat memory or local documents.
2. Treat the current tracked files in `Frysland-2024/AI4science` as the authority
   for XRD, V9-T, application-planning, and project-state questions.
3. If the repository choice is ambiguous, remain on
   `Frysland-2024/AI4science` unless the user explicitly selects another project.

Before working on the XRD project, read:

1. `00_project_context/CURRENT_STATE.md`
2. `xrd_robustness/CODEX_HANDOFF.md`
3. `xrd_robustness/README.md`

At the end of every meaningful task:

1. Update `00_project_context/CURRENT_STATE.md` with completed work, current blocker, experiment status, and next actions.
2. When a scientific decision or research direction changes, record the current
   rationale in `00_project_context/CURRENT_STATE.md`.
3. Clearly distinguish:
   - scientific design
   - engineering implementation
   - completed results
   - assumptions
   - unresolved risks

4. Do not commit:
   - datasets
   - checkpoints
   - generated spectra
   - caches
   - API keys
   - credentials
   - large third-party repositories

5. Before handing work back, report:
   - files changed
   - tests executed
   - tests passed or failed
   - remaining blocker
   - exact next command

## Automatic GitHub Synchronization

After any task that actually changes source code, configuration, or project
documentation, complete the following workflow before handing work back:

1. Confirm the repository and worktree before staging:
   - run `git rev-parse --show-toplevel` and require the result to be
     `E:/AI4science`;
   - run `git status --short --branch`;
   - require the checked-out branch to be `main` and the synchronization target to
     be `origin/main`;
   - if there are unrelated, unexplained, or user-owned changes, stop and report
     them instead of altering or staging them.
2. Run the tests or verification checks relevant to the files changed. A documentation-only
   change may use targeted formatting, link, policy, and secret scans instead of the
   full model test suite. Any failed required check blocks commit and push.
3. If the current project state changed, update both:
   - `xrd_robustness/CODEX_HANDOFF.md`;
   - the corresponding current-state or decision record under
     `00_project_context/`.
   Record current scientific or research-direction reasoning in
   `00_project_context/CURRENT_STATE.md`.
4. Never stage or commit:
   - datasets, generated spectra, `data/`, or `outputs/` artifacts;
   - checkpoints, model weights, optimizer state, or caches;
   - literature PDFs, external source repositories, or virtual environments;
   - API keys, passwords, tokens, credentials, or any other secret.
5. Stage only explicit paths belonging to the current task. Do not use
   `git add .`, `git add -A`, or another unreviewed bulk-staging command.
6. Before committing, inspect `git diff --cached --name-status` and
   `git diff --cached`, and scan the staged content for secrets and prohibited
   artifact types. Stop if the staged scope is not exactly the intended scope.
7. Commit with a concise English message that accurately describes the completed
   work.
8. After committing, run `git status --short --branch` and require a clean
   worktree. Then run `git push origin main` and verify that local `HEAD` matches
   `refs/remotes/origin/main`.
9. Never force-push, rewrite history, delete old commits, or use
   `git reset --hard`.
10. If tests fail, a secret or prohibited artifact is detected, unexplained user
    changes exist, the worktree is not clean after commit, or the push fails, stop
    and report the exact blocker. Do not bypass, amend, reset, or force the result.
11. If the user explicitly says `暂不提交`, `不要提交`, `不要推送`, or otherwise
    opts out of publication for the current task, skip commit and/or push as
    requested and report the remaining local changes.

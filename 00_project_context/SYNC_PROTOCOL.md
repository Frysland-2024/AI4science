# AI4science Local–GitHub Synchronization Protocol

**Repository:** `Frysland-2024/AI4science`  
**Default branch:** `main`

## 1. What GitHub can and cannot prove

GitHub records only committed and pushed content. A remote reader can verify the repository state on `origin/main`, but cannot directly inspect the local filesystem at `E:/AI4science`.

Therefore, local and remote are considered fully synchronized only when all checks below pass on the local machine.

## 2. Canonical local sync check

Run from `E:/AI4science`:

```powershell
git fetch origin

git status --short --branch

git rev-parse HEAD
git rev-parse origin/main

git diff --quiet HEAD origin/main
if ($LASTEXITCODE -eq 0) {
    Write-Host "Committed content matches origin/main"
} else {
    Write-Host "Committed content differs from origin/main"
}
```

A fully synchronized tracked worktree should satisfy all of the following:

1. `git status --short --branch` shows `## main...origin/main` with no `[ahead N]` or `[behind N]`.
2. No additional modified, deleted, staged, or untracked files are listed.
3. `git rev-parse HEAD` and `git rev-parse origin/main` return the same SHA.
4. `git diff --quiet HEAD origin/main` returns success.

## 3. Check ignored local assets separately

Ignored files are intentionally outside Git synchronization. To inspect them:

```powershell
git status --ignored --short
```

Typical intentionally local assets include:

- virtual environments;
- datasets and generated spectra;
- checkpoints and run outputs;
- caches and temporary files;
- API keys and credentials;
- large third-party repositories;
- PDF text extraction caches.

The presence of ignored files does not mean the Git worktree is unsynchronized. It means those assets are local-only by design.

## 4. Safe update sequence before new work

```powershell
cd E:\AI4science

git status --short --branch
git pull --ff-only
```

If untracked local files would be overwritten, back them up before removing or renaming them. Do not use `git reset --hard` or `git clean -fd` unless the user explicitly approves data loss.

## 5. Safe commit sequence after meaningful work

Do not use `git add .` by default in this research workspace. Add only intended paths:

```powershell
git add AGENTS.md README.md 00_project_context xrd_robustness

git status --short
git diff --cached --stat

git commit -m "Describe the scientific or engineering change"
git push
```

Before pushing, confirm that datasets, checkpoints, secrets, caches, generated spectra, and large third-party assets are not staged.

## 6. Minimal evidence to share with a remote reviewer

When asking whether local and GitHub are synchronized, provide the output of:

```powershell
git fetch origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

This is sufficient to verify tracked-file synchronization. It does not expose ignored local files or secrets.

## 7. Project-state update responsibility

After a meaningful scientific or engineering change:

1. update `00_project_context/CURRENT_STATE.md`;
2. append the reasoning to `00_project_context/PROJECT_JOURNEY.md` when the research direction changes;
3. update experiment reports or registries when runs are executed;
4. commit and push the changes;
5. verify local `HEAD` equals `origin/main`.

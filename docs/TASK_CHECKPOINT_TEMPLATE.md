# TASK CHECKPOINT

> Purpose: persistent recovery state for long-running AI tasks. A new chat or execution environment must continue from this file and must not redo completed work.

## Task
- Task name:
- Task ID:
- Current phase:
- Updated at:

## Input baseline
- Repository:
- Branch:
- HEAD:
- Input files:
- File SHA / version:

## Completed
- [ ] Phase 1:
- [ ] Phase 2:
- [ ] Phase 3:

## Structured conclusions
| Object | Current conclusion | Key evidence | Status |
|---|---|---|---|
| | | | done / needs-review |

## Needs review
- Object:
  - Missing evidence:
  - Sources already checked:
  - Current provisional conclusion:
  - Next action:

## Generated artifacts
- File:
  - Path:
  - Status:
  - Mechanical validation:
  - Written back to Git:

## Remaining work
1.
2.
3.

## Next exact actions
1.
2.
3.

## Recovery rules
- Continue from this checkpoint;
- Do not redo completed work;
- A single uncertain object must not block the whole task;
- If rendered files are lost but structured conclusions remain, rebuild only the files;
- After a crash, read the current Git HEAD before writing;
- Do not restart full-scale research unless this checkpoint explicitly shows that the research phase was incomplete.

# Research Supervisor v1 — AI4science

**Implementation: observer and notifier, NOT an autonomous experiment or job-resume engine.**
Current scientific authority: AGENTS.md and docs/CURRENT_STATE.md. Existing GPU/Code bridge code is unchanged.

## What is monitored

- Future Research Bridge journals under the shared Git directory. First bootstrap snapshots and excludes existing issue-15, issue-23, and any other preexisting jobs. This avoids retroactive claims.
- New GPU runs use their own 30-second local heartbeat file. Other Codex tasks have start/end journals but no per-process heartbeat yet; after 10 minutes without updates their status is STALE_UNCERTAIN, never an automatic failure or restart.
- Directly launched Codex work only after an explicit --register-external command with verified PID + Windows process creation timestamp. A manually attached existing process requires its own heartbeat writer to avoid becoming STALE_UNCERTAIN. Do not retroactively assume Issue #19 was always monitored.

Statuses: RUNNING, REVIEW_PENDING, FAILED, BLOCKED, STOPPED, STALE_UNCERTAIN, NEEDS_REVIEW.

## Delivery and provenance

- Each status change is appended to local events.jsonl and queued in supervisor_v1/outbox. The public GitHub Issue gets only an opaque run ID, status and coarse reason. No raw logs, credentials, absolute paths, checkpoints or private spectra.
- A deterministic event marker is checked in the remote Issue before posting to prevent duplicates even when a previous post succeeded but acknowledgement failed.
- GitHub/network outages leave events in the local outbox, which is drained on a future check; this can delay messages. No frequent heartbeat comments.
- Existing GPU Bridge produces the sanitized result Draft PR. evidence.py checks presence and hashes of required JSON files locally. Scientific acceptance still requires inspecting baseline, seeds, splits, physics gates, provenance and negative results.
- A process exit code zero, PASS text or presence of metrics is not scientific certification. Completed records remain COMPLETED_UNREVIEWED / REVIEW_PENDING.

## Safe deployment on Windows

After PR is reviewed, merged, and main updated in E:\AI4science:

~~~powershell
cd E:\AI4science
python -m unittest discover -s research_bridge/tests -v
python -m research_bridge.supervisor --once --dry-run
python -m research_bridge.supervisor --bootstrap
python -m research_bridge.supervisor --once
powershell -ExecutionPolicy Bypass -File .\research_bridge\register_supervisor_task.ps1
Get-ScheduledTaskInfo -TaskName AI4science-Research-Supervisor
~~~

Schedule: every 10 minutes, at most one instance, up to 3 minutes per check; it does not keep the PC awake. It is a separate Windows task and does not stop or change AI4science-Codex-Bridge.

To uninstall (does not delete local logs):

~~~powershell
Unregister-ScheduledTask -TaskName AI4science-Research-Supervisor -Confirm:$false
~~~

To inspect only:

~~~powershell
python -m research_bridge.supervisor --once --dry-run
Get-ChildItem .git\research_bridge\supervisor_v1\outbox
~~~

## Explicit external Codex registration

For a NEW manually launched Codex task, identify its real Windows PID and Issue. Only then run:

~~~powershell
python -m research_bridge.supervisor --register-external --issue 29 --run-id example_new_job --pid 12345
~~~

This registers only process identity. It does NOT launch, stop or restart Codex. The process must provide heartbeat files under the private supervisor state folder if continuous progress monitoring is desired. Without a heartbeat the supervisor marks uncertainty after 10 minutes. Registration does not grant further permission or access to the worktree.

## Recovery policy

- Classify known error signatures without editing original logs.
- Failed/stopped/blocked scientific runs never retry themselves; frozen V9 is untouched.
- recovery.py verifies a would-be resume contract and checkpoint hash but deliberately always returns MANUAL_APPROVAL_REQUIRED even on valid inputs. Resume execution is not implemented.
- No automatic merge, code modification, GPU launch or new experimental protocol.
- Existing Issue #19 follow-up is not automatically enrolled or interrupted.

## Validation

Unit tests cover Windows PID creation lookup, stale alive/dead/reused process, missing report, synthetic report, duplicate comments, offline queue, dry-run purity, bootstrap baseline, bounded and fail-closed resume assessment.
Hourly ChatGPT GitHub checks can notice new results after they are committed or posted; this does not create a real-time push into the current chat.

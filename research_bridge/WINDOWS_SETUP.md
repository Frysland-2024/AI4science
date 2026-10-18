# Windows bridge setup

Run the setup from the intended AI4science checkout in an elevated PowerShell only if your local Task Scheduler policy requires it. This script registers the worker every 30 minutes, preserves `MultipleInstances IgnoreNew`, and sets `ExecutionTimeLimit` to zero (no fixed scheduler kill time).

```powershell
cd E:\AI4science
python -m research_bridge.worker --doctor
python -m unittest discover -s research_bridge/tests -v
python -m research_bridge.worker --setup-labels
.\research_bridge\register_windows_task.ps1
Get-ScheduledTask -TaskName AI4science-Codex-Bridge | Select-Object -ExpandProperty Settings
```

Re-register manually after deploying a bridge update that changes `register_windows_task.ps1`; installing code does not silently rewrite an existing scheduled task. The zero scheduler limit does not prevent Windows shutdown, sleep, sign-out policy, or hardware failure from ending the process.

## GPU Python selection

The GitHub Issue cannot select a Python executable. Set `AI4SCIENCE_GPU_PYTHON` in the worker's administrator-controlled environment to a reviewed interpreter if needed. Otherwise the worker tries `E:\AI4science\.venvs\xrd_test\Scripts\python.exe`, then the Python running the bridge. The worker never writes this absolute path into public results.

GPU runs keep `stdout.log`, `stderr.log`, and heartbeats under `.git\research_bridge\gpu_runs\<run_id>`. To request cancellation, create the `STOP` file in that run directory. The worker checks the marker periodically and terminates the process tree. The scheduled task uses `IgnoreNew`, so registering again does not start a second worker while one is active.

Completed and blocked runs publish only the documented artifact allowlist to `bridge-results/<run_id>` and create a Draft PR to `main`. A push failure is recorded locally and reported on the Issue. The PR is not auto-merged and does not certify scientific claims.

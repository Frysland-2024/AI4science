# Example GitHub Issue task

```markdown
### Bridge protocol
research-task-bridge/v1

### Action
codex_read_only

### Context scope
docs

### Dedupe key (optional)

### Request
Summarize the proposed AutoLab execution boundary and distinguish documented plans from implemented code. Cite repository paths. Do not run tests or experiments.
```

The issue template adds the `research-task` and `rtb:ready` labels. A request that needs GPU work, test-set use, a protocol change, or a research-direction change must use `requires_user_approval`; the v1 worker will hold it without executing it.

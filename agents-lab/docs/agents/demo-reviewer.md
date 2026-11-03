# Synthetic report reviewer

Use this role in a separate Codex session after the writer hands off a draft task path.

1. Read the draft task, generated draft, source task, evidence, and metric contract.
2. Run the independent review entry point documented in `README.md`. Inspect its findings and the resulting task status, then verify the final task's local artifact links.
3. Commit the `ready` or `blocked` task transition, then report the exact draft version and findings.

Review the writer's artifact without editing it. A `ready` draft awaits a person's decision; do not mark it Accepted or send it externally.

#!/usr/bin/env python3
"""Check the initialized project guidance without third-party dependencies."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "AGENTS.md",
    "CONTEXT.md",
    "STATUS.md",
    "README.md",
    "issues/README.md",
    "issues/ISSUE-001.md",
    "inputs/README.md",
)


def main() -> int:
    errors = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append("missing " + relative)

    for relative in ("AGENTS.md", "CONTEXT.md", "STATUS.md"):
        path = ROOT / relative
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            if "<!-- Fill" in content or "YYYY-MM-DD" in content:
                errors.append("initialization placeholder in " + relative)

    status = ROOT / "STATUS.md"
    if status.is_file():
        content = status.read_text(encoding="utf-8")
        if "## Next task" not in content:
            errors.append("STATUS.md lacks a next task section")
        else:
            next_task = content.split("## Next task", 1)[1].split("\n## ", 1)[0].strip()
            if not next_task:
                errors.append("STATUS.md lacks a next task description")
        if "Windows validation: deferred" not in content:
            errors.append("STATUS.md lacks the deferred Windows status")

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(ROOT),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if Path(result.stdout.strip()).resolve() != ROOT:
            errors.append("Git root differs from project root")
    except (OSError, subprocess.CalledProcessError):
        errors.append("project root is not a Git repository")

    if errors:
        for error in errors:
            print("codex-check: " + error, file=sys.stderr)
        print("codex-check: FAIL", file=sys.stderr)
        return 1

    print("codex-check: PASS (" + str(ROOT) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())

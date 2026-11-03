# Issue tracker: Local Markdown

New issues and specs for this repository live as Markdown files in `.scratch/`. The completed bootstrap issue, `issues/ISSUE-001.md`, remains the historical reference for the Mac input validator.

## Conventions

- Use one directory per feature: `.scratch/<feature-slug>/`.
- Put a feature spec at `.scratch/<feature-slug>/spec.md` when one exists.
- Put each implementation ticket in its own `.scratch/<feature-slug>/issues/<NN>-<slug>.md` file, numbered from `01` in dependency order.
- Record triage state with a `Status:` line near the top of each ticket. Use the strings in `triage-labels.md`.
- Record ticket lifecycle with `State: open` or `State: closed`. A numbered blocker is complete when its ticket is closed.
- Record one `Category:` line near the top of each ticket: `bug` or `enhancement`.
- Record blocking tickets by number and title. Record external prerequisites explicitly, without treating them as completed ticket edges.
- Append discussion under `## Comments` in the relevant ticket.

## Skill operations

- To publish a ticket, create its numbered file in the feature's `issues/` directory.
- To fetch a ticket, read the referenced file in full.
- To find executable work, scan for open `ready-for-agent` tickets whose numbered blockers are closed and whose external prerequisites are satisfied.

## Wayfinding operations

For `/wayfinder`, use `.scratch/<effort>/map.md` as the map and `.scratch/<effort>/issues/NN-<slug>.md` as child tickets. Child tickets use `Type:` (`research`, `prototype`, `grilling`, or `task`) and `Status:` (`claimed` or `resolved`). A child is on the frontier when it is open, unblocked, and unclaimed; select the lowest number. To claim it, set `Status: claimed`. To resolve it, add an `## Answer`, set `Status: resolved`, and add a short context pointer to the map's Decisions-so-far section.

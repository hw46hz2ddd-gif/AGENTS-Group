"""Small Markdown record format for one draft-and-review task."""


def task_text(fields, errors=None):
    lines = ["---"]
    lines.extend("{}: {}".format(key, value) for key, value in fields.items())
    lines.extend(["---", "", "# Draft review: {}".format(fields["id"]), "", "## Findings", ""])
    if errors:
        lines.extend("- {}".format(error.replace("\n", " ")) for error in errors)
    elif fields["status"] == "working":
        lines.append("- Awaiting independent draft review.")
    else:
        lines.append("- Draft checks passed; ready for human review, not accepted.")
    return "\n".join(lines) + "\n"

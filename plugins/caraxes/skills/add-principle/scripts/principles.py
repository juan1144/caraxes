"""Inspect and safely update the Caraxes principles directory."""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path


ID_PATTERN = re.compile(r"^P-(\d{3,})$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEADING_PATTERN = re.compile(r"^# (P-\d{3,}) — (.+?)\s*$")
SUMMARY_PATTERN = re.compile(r"^Summary: (.+?)\s*$")
RULE_PATTERN = re.compile(r"^Rule: (.+?)\s*$")
INDEX_ENTRY_PATTERN = re.compile(r"^- \*\*(P-\d{3,}) — (.+?):\*\* (.+?)\s*$")


class PrinciplesError(ValueError):
    """The principles directory cannot be safely inspected or changed."""


def principles_directory(workspace):
    path = Path(workspace).expanduser().resolve()
    if not path.is_absolute():
        raise PrinciplesError("Use an absolute workspace path.")
    directory = path / "principles"
    if not directory.is_dir() or directory.is_symlink():
        raise PrinciplesError(f"Principles directory is missing or invalid: {directory}")
    return directory


def parse_document(path):
    if path.is_symlink() or not path.is_file():
        raise PrinciplesError(f"Principle document is not an ordinary file: {path}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise PrinciplesError(f"Cannot read principle document: {path}") from exc
    if not lines:
        raise PrinciplesError(f"Principle document is empty: {path}")
    heading = HEADING_PATTERN.match(lines[0])
    if heading is None:
        raise PrinciplesError(f"Principle document must start with an ID heading: {path}")
    principle_id, title = heading.groups()
    summary = next((match.group(1) for line in lines if (match := SUMMARY_PATTERN.match(line))), None)
    rule = next((match.group(1) for line in lines if (match := RULE_PATTERN.match(line))), None)
    if summary is None or rule is None:
        raise PrinciplesError(f"Principle document needs Summary and Rule lines: {path}")
    if not ID_PATTERN.fullmatch(principle_id):
        raise PrinciplesError(f"Invalid principle ID in {path}: {principle_id}")
    return {"id": principle_id, "title": title, "summary": summary, "rule": rule,
            "path": path.name}


def inspect(workspace):
    directory = principles_directory(workspace)
    documents = []
    for path in sorted(directory.glob("*.md")):
        if path.name == "index.md":
            continue
        if not path.name.startswith("P-"):
            raise PrinciplesError(f"Unexpected Markdown file in principles directory: {path}")
        documents.append(parse_document(path))
    ids = [item["id"] for item in documents]
    if len(ids) != len(set(ids)):
        raise PrinciplesError("Duplicate principle IDs found.")
    index = directory / "index.md"
    if index.is_symlink() or (index.exists() and not index.is_file()):
        raise PrinciplesError(f"Index is not an ordinary file: {index}")
    if index.exists():
        try:
            entries = [INDEX_ENTRY_PATTERN.match(line).groups()
                       for line in index.read_text(encoding="utf-8").splitlines()
                       if line.startswith("- **")]
        except (OSError, UnicodeError) as exc:
            raise PrinciplesError(f"Cannot read principles index: {index}") from exc
        expected = [(item["id"], item["title"], item["summary"]) for item in documents]
        if entries != expected:
            raise PrinciplesError(f"Principles index is missing, malformed, or stale: {index}")
    return {"status": "ready", "principles_directory": str(directory),
            "index_path": str(index), "principles": documents,
            "document_count": len(documents)}


def next_id(documents):
    numbers = [int(item["id"][2:]) for item in documents]
    return f"P-{(max(numbers) + 1 if numbers else 1):03d}"


def write_atomic(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def render_index(documents):
    lines = ["# Active principles", "", "Read these summaries before planning or changing anything.", ""]
    for item in documents:
        lines.append(f"- **{item['id']} — {item['title']}:** {item['summary']}")
    return "\n".join(lines) + "\n"


def add(workspace, title, summary, rule, slug, principle_id=None):
    state = inspect(workspace)
    directory = Path(state["principles_directory"])
    principle_id = principle_id or next_id(state["principles"])
    if not ID_PATTERN.fullmatch(principle_id):
        raise PrinciplesError("Principle ID must use the P-001 format.")
    if not SLUG_PATTERN.fullmatch(slug):
        raise PrinciplesError("Slug must contain lowercase letters, numbers, and hyphens only.")
    if not title.strip() or not summary.strip() or not rule.strip():
        raise PrinciplesError("Title, summary, and rule are required.")
    existing_ids = {item["id"] for item in state["principles"]}
    if principle_id in existing_ids:
        raise PrinciplesError(f"Principle ID already exists: {principle_id}")
    filename = f"{principle_id}-{slug}.md"
    target = directory / filename
    if target.exists() or target.is_symlink():
        raise PrinciplesError(f"Refusing to overwrite existing path: {target}")
    content = (f"# {principle_id} — {title.strip()}\n\n"
               f"Summary: {summary.strip()}\n\n"
               f"Rule: {rule.strip()}\n")
    write_atomic(target, content)
    updated = inspect(workspace)
    write_atomic(directory / "index.md", render_index(updated["principles"]))
    return {"status": "created", "principle": parse_document(target),
            "index_path": str(directory / "index.md")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    inspect_command = commands.add_parser("inspect")
    inspect_command.add_argument("--workspace", required=True)
    add_command = commands.add_parser("add")
    add_command.add_argument("--workspace", required=True)
    add_command.add_argument("--title", required=True)
    add_command.add_argument("--summary", required=True)
    add_command.add_argument("--rule", required=True)
    add_command.add_argument("--slug", required=True)
    add_command.add_argument("--id")
    args = parser.parse_args()
    try:
        result = inspect(args.workspace) if args.operation == "inspect" else add(
            args.workspace, args.title, args.summary, args.rule, args.slug, args.id)
    except (PrinciplesError, OSError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

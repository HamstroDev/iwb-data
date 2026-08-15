#!/usr/bin/env python3
"""Print PR comment for a validation run."""

import json
import os
import re
import sys

MARKER = "<!-- iwb-validation -->"
SAFE_PATH_RE = re.compile(r"data/sites[A-Z]+\.json")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
SHA_RE = re.compile(r"[0-9a-f]{40}")


def inert(message):
    """Render a message as a code span nothing can escape from."""
    message = re.sub(r"\s+", " ", message.replace("`", "'")).strip()
    return f"`{message[:300]}`" if message else "(no message)"


def blob_url():
    repo = os.environ.get("PR_HEAD_REPO", "")
    sha = os.environ.get("PR_HEAD_SHA", "")
    if REPO_RE.fullmatch(repo) and SHA_RE.fullmatch(sha):
        return f"https://github.com/{repo}/blob/{sha}"
    return None


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        errors = json.load(f).get("errors", [])

    print(MARKER)
    if not errors:
        print("**Validation passed.**")
        return

    print("**Validation failed.**")
    print()
    blob = blob_url()
    for error in errors:
        path, line = error.get("path"), error.get("line") or 1
        message = inert(error.get("message", ""))
        if path and SAFE_PATH_RE.fullmatch(path):
            name = f"{path.removeprefix('data/')} line {line}"
            place = f"[{name}]({blob}/{path}#L{line})" if blob else name
            print(f"- {place}: {message}")
        else:
            print(f"- {message}")
    print(
        "If you can, please fix the errors and push a new commit. Otherwise, a maintainer will review and fix them. "
    )


if __name__ == "__main__":
    main()

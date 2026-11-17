"""The `hosted-runner-lint` command: judge the runner of every workflow job.

    hosted-runner-lint [FILE...]

With no FILE, it reads every tracked `.github/workflows/*.yml` and `*.yaml` of
the current directory's repository, from its root wherever it is run; named
FILEs are read relative to the current directory. Each file is parsed by mikefarah's `yq`
from PATH, with anchors and aliases expanded, so the document judged is the
one GitHub reads, not its text. It prints one line per finding and exits 1 on
any; it also exits 1, with the reason on stderr, when it could not judge, since
a lint that did not run must not read as clean.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from hosted_runner_lint.runners import Finding, judge

# Glob magic, so `*` stops at a `/`: GitHub reads workflows only from the
# directory itself, and a file under a subdirectory of it is not a workflow.
WORKFLOW_GLOBS = (
    ":(glob).github/workflows/*.yml",
    ":(glob).github/workflows/*.yaml",
)


class CouldNotRun(Exception):
    pass


def _run(argv: list[str], cwd: Path, what: str) -> bytes:
    try:
        return subprocess.run(argv, cwd=cwd, capture_output=True, check=True).stdout
    except FileNotFoundError as error:
        raise CouldNotRun(f"{argv[0]} is not on PATH") from error
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode(errors="replace").strip()
        raise CouldNotRun(f"{what} failed: {stderr}") from error


def repository_root(cwd: Path) -> Path:
    # Only git's terminating newline is removed: a path may end in whitespace,
    # and it is bytes in the filesystem's encoding, not necessarily UTF-8.
    out = _run(["git", "rev-parse", "--show-toplevel"], cwd, "git rev-parse")
    return Path(os.fsdecode(out.removesuffix(b"\n")))


def tracked_workflows(root: Path) -> list[str]:
    listed = _run(
        ["git", "ls-files", "-z", "--", *WORKFLOW_GLOBS], root, "git ls-files"
    )
    return [os.fsdecode(name) for name in listed.split(b"\0") if name]


def parse(root: Path, name: str) -> object:
    out = _run(
        ["yq", "--input-format=yaml", "--output-format=json", "explode(.)", name],
        root,
        f"parsing {name}",
    )
    try:
        return json.loads(out)
    except json.JSONDecodeError as error:
        raise CouldNotRun(f"parsing {name}: yq printed no JSON document") from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hosted-runner-lint",
        description="Check that every workflow job runs on a GitHub-hosted standard runner.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="workflow files to read instead of every tracked one",
    )
    args = parser.parse_args(argv)
    findings: list[Finding] = []
    try:
        if args.files:
            root, names = Path.cwd(), list(args.files)
        else:
            root = repository_root(Path.cwd())
            names = tracked_workflows(root)
        for name in names:
            findings.extend(judge(name, parse(root, name)))
    except CouldNotRun as error:
        print(f"ERROR: hosted-runner-lint could not run: {error}", file=sys.stderr)
        return 1
    for finding in findings:
        print(finding)
    return 1 if findings else 0

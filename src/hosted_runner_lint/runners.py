"""Judge one parsed workflow: does every job run on a GitHub-hosted standard
runner?

A standard runner is one GitHub provides free to a public repository: a label
in STANDARD, compared without regard to case, as GitHub compares labels. Everything else is refused: `self-hosted` and any custom label,
since a public repository's workflows run code from fork pull requests and a
self-hosted machine would run it; a runner `group`, which is how both
self-hosted and larger runners are chosen; and the `-large` and `-xlarge`
labels, which are billed per minute even for a public repository. A label
this cannot read is refused too, with the reason, rather than passed.

A label written as `${{ matrix.KEY }}` is read from a literal matrix: every
value the job's `strategy.matrix` lists for KEY, and every value its
`include` entries set, where KEY matches without regard to case, as GitHub's
contexts do. Any other expression is unreadable here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# GitHub's table of standard runners for public repositories, verbatim:
# https://docs.github.com/en/actions/reference/runners/github-hosted-runners
# A list rather than a pattern, because a pattern also accepts a label GitHub
# does not host, and a self-hosted runner can carry any label at all. A label
# GitHub adds is refused until it is added here.
STANDARD = frozenset(
    {
        "ubuntu-slim",
        "ubuntu-latest",
        "ubuntu-26.04",
        "ubuntu-24.04",
        "ubuntu-22.04",
        "ubuntu-26.04-arm",
        "ubuntu-24.04-arm",
        "ubuntu-22.04-arm",
        "windows-latest",
        "windows-2025",
        "windows-2025-vs2026",
        "windows-2022",
        "windows-11-arm",
        "windows-11-vs2026-arm",
        "macos-latest",
        "macos-26",
        "macos-15",
        "macos-26-intel",
        "macos-15-intel",
        "xcode-27",
    }
)
MATRIX_LABEL = re.compile(r"^\$\{\{\s*matrix\.([A-Za-z_][A-Za-z0-9_-]*)\s*\}\}$")


@dataclass(frozen=True)
class Finding:
    path: str
    job: str
    what: str

    def __str__(self) -> str:
        return f"{self.path}: job {self.job}: {self.what}"


def _same_key(key: str, mapping: Mapping[str, Any]) -> list[object]:
    return [value for name, value in mapping.items() if name.lower() == key.lower()]


def _matrix_values(job: Mapping[str, Any], key: str) -> list[object] | None:
    matrix = (job.get("strategy") or {}).get("matrix")
    if not isinstance(matrix, Mapping):
        return None
    values: list[object] = []
    for listed in _same_key(key, matrix):
        if not isinstance(listed, list):
            return None
        values.extend(listed)
    include = matrix.get("include") or []
    if not isinstance(include, list):
        return None
    for entry in include:
        if not isinstance(entry, Mapping):
            return None
        values.extend(_same_key(key, entry))
    return values or None


def _labels(job: Mapping[str, Any]) -> tuple[list[object], list[str]]:
    """The labels a job's runs-on names, and what about it could not be read."""
    runs_on = job.get("runs-on")
    if isinstance(runs_on, Mapping):
        problems = []
        if "group" in runs_on:
            problems.append("runs-on names a runner group")
        labels = runs_on.get("labels", [])
        return (labels if isinstance(labels, list) else [labels]), problems
    if isinstance(runs_on, list):
        return list(runs_on), []
    return [runs_on], []


def _judge_label(job: Mapping[str, Any], label: object) -> list[str]:
    if not isinstance(label, str):
        return [f"runs-on label {label!r} is not a string"]
    match = MATRIX_LABEL.match(label)
    if match:
        values = _matrix_values(job, match.group(1))
        if values is None:
            return [f"runs-on {label} cannot be read from a literal matrix"]
        return [p for value in values for p in _judge_label({}, value)]
    if "${{" in label:
        return [f"runs-on {label} is an expression this cannot read"]
    if label.lower() == "self-hosted":
        return ["runs-on self-hosted: a public repository runs fork code on it"]
    if label.lower() not in STANDARD:
        return [f"runs-on {label} is not a GitHub-hosted standard runner"]
    return []


def judge(path: str, workflow: object) -> list[Finding]:
    if not isinstance(workflow, Mapping):
        return [Finding(path, "-", "the file is not a workflow mapping")]
    jobs = workflow.get("jobs")
    if not isinstance(jobs, Mapping):
        return [Finding(path, "-", "the workflow has no jobs mapping")]
    findings: list[Finding] = []
    for name, job in jobs.items():
        if not isinstance(job, Mapping):
            findings.append(Finding(path, str(name), "the job is not a mapping"))
            continue
        if "uses" in job and "runs-on" not in job:
            # A reusable workflow's call: its jobs are judged where it lives.
            continue
        if "runs-on" not in job:
            findings.append(Finding(path, str(name), "the job has no runs-on"))
            continue
        labels, problems = _labels(job)
        for label in labels:
            problems.extend(_judge_label(job, label))
        findings.extend(Finding(path, str(name), p) for p in problems)
    return findings

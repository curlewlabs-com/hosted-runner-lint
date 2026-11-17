"""Tests for judging one parsed workflow's runners."""

from __future__ import annotations

import unittest
from collections.abc import Mapping

from hosted_runner_lint.runners import STANDARD, judge


def whats(workflow: object) -> list[str]:
    return [f.what for f in judge("w.yml", workflow)]


def one_job(job: Mapping[str, object]) -> dict[str, object]:
    return {"jobs": {"j": job}}


class StandardLabels(unittest.TestCase):
    def test_every_standard_label_passes_in_any_case(self) -> None:
        for label in sorted(STANDARD):
            for spelling in (label, label.upper()):
                with self.subTest(label=spelling):
                    self.assertEqual(whats(one_job({"runs-on": spelling})), [])

    def test_a_label_shaped_like_a_hosted_one_is_refused(self) -> None:
        # A self-hosted runner can carry any label, so one that only looks
        # like GitHub's would route a public repository's jobs to it.
        for label in ("ubuntu-99.99", "windows-9999", "macos-99", "macos-14"):
            with self.subTest(label=label):
                self.assertEqual(len(whats(one_job({"runs-on": label}))), 1)

    def test_self_hosted_is_refused_with_the_reason(self) -> None:
        # The risk the lint exists for: fork pull requests run on the machine.
        self.assertEqual(
            whats(one_job({"runs-on": ["self-hosted", "linux"]})),
            [
                "runs-on self-hosted: a public repository runs fork code on it",
                "runs-on linux is not a GitHub-hosted standard runner",
            ],
        )

    def test_a_custom_label_is_refused(self) -> None:
        self.assertEqual(
            whats(one_job({"runs-on": "build-mac"})),
            ["runs-on build-mac is not a GitHub-hosted standard runner"],
        )

    def test_a_larger_runner_is_refused(self) -> None:
        # Billed per minute even for a public repository.
        self.assertEqual(len(whats(one_job({"runs-on": "macos-15-xlarge"}))), 1)
        self.assertEqual(len(whats(one_job({"runs-on": "ubuntu-24.04-large"}))), 1)

    def test_a_runner_group_is_refused(self) -> None:
        self.assertEqual(
            whats(
                one_job({"runs-on": {"group": "builders", "labels": ["ubuntu-24.04"]}})
            ),
            ["runs-on names a runner group"],
        )


class Expressions(unittest.TestCase):
    def test_a_matrix_label_is_read_from_the_literal_matrix(self) -> None:
        job = {
            "runs-on": "${{ matrix.runner }}",
            "strategy": {
                "matrix": {
                    "runner": ["ubuntu-24.04"],
                    "include": [{"runner": "macos-15"}, {"runner": "self-hosted"}],
                }
            },
        }
        self.assertEqual(
            whats(one_job(job)),
            ["runs-on self-hosted: a public repository runs fork code on it"],
        )

    def test_a_matrix_key_matches_in_any_case(self) -> None:
        # GitHub's contexts ignore case, so `RUNNER` is the same variable as
        # `runner` and its configuration is scheduled too.
        job = {
            "runs-on": "${{ matrix.runner }}",
            "strategy": {
                "matrix": {
                    "include": [{"runner": "ubuntu-latest"}, {"RUNNER": "self-hosted"}]
                }
            },
        }
        self.assertEqual(len(whats(one_job(job))), 1)
        job["strategy"] = {"matrix": {"Runner": ["self-hosted"]}}
        self.assertEqual(len(whats(one_job(job))), 1)

    def test_a_matrix_built_by_an_expression_is_refused(self) -> None:
        # Its values are known only at run time, so a pass would be a guess.
        job = {
            "runs-on": "${{ matrix.runner }}",
            "strategy": {"matrix": "${{ fromJSON(needs.a.outputs.m) }}"},
        }
        self.assertEqual(len(whats(one_job(job))), 1)

    def test_a_matrix_key_with_no_values_is_refused(self) -> None:
        job = {"runs-on": "${{ matrix.os }}", "strategy": {"matrix": {"v": [1]}}}
        self.assertEqual(len(whats(one_job(job))), 1)

    def test_any_other_expression_is_refused(self) -> None:
        self.assertEqual(
            whats(one_job({"runs-on": "${{ inputs.runner }}"})),
            ["runs-on ${{ inputs.runner }} is an expression this cannot read"],
        )


class Shapes(unittest.TestCase):
    def test_a_reusable_workflow_call_is_judged_where_it_lives(self) -> None:
        self.assertEqual(whats(one_job({"uses": "o/r/.github/workflows/w.yml@x"})), [])

    def test_a_job_without_runs_on_is_refused(self) -> None:
        self.assertEqual(whats(one_job({"steps": []})), ["the job has no runs-on"])

    def test_a_file_that_is_not_a_workflow_is_refused(self) -> None:
        self.assertEqual(whats([1, 2]), ["the file is not a workflow mapping"])
        self.assertEqual(whats({"on": "push"}), ["the workflow has no jobs mapping"])

    def test_the_finding_names_file_and_job(self) -> None:
        (finding,) = judge("ci.yml", {"jobs": {"build": {"runs-on": "x"}}})
        self.assertEqual(
            str(finding),
            "ci.yml: job build: runs-on x is not a GitHub-hosted standard runner",
        )


if __name__ == "__main__":
    unittest.main()

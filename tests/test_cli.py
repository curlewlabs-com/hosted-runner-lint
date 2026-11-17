"""Tests for the `hosted-runner-lint` command: which files it reads, that it
judges the document GitHub sees, and that a lint that could not run never
exits clean. They need git and mikefarah's yq on PATH."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hosted_runner_lint.cli import main


def run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = main(argv)
    return status, out.getvalue(), err.getvalue()


class TheCommand(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        subprocess.run(["git", "init", "-q"], check=True)
        (self.root / ".github/workflows").mkdir(parents=True)

    def workflow(self, name: str, text: str, track: bool = True) -> None:
        (self.root / ".github/workflows" / name).write_text(text)
        if track:
            subprocess.run(["git", "add", f".github/workflows/{name}"], check=True)

    def test_tracked_workflows_are_judged(self) -> None:
        self.workflow("ok.yml", "on: push\njobs:\n  a:\n    runs-on: ubuntu-24.04\n")
        self.workflow("bad.yaml", "on: push\njobs:\n  b:\n    runs-on: self-hosted\n")
        self.workflow(
            "untracked.yml", "jobs:\n  c:\n    runs-on: self-hosted\n", track=False
        )
        status, out, _ = run([])
        self.assertEqual(status, 1)
        self.assertEqual(
            out,
            ".github/workflows/bad.yaml: job b: runs-on self-hosted: "
            "a public repository runs fork code on it\n",
        )

    def test_an_alias_is_judged_as_what_it_names(self) -> None:
        # A text scan would read `*runner` as the label; GitHub reads its anchor.
        self.workflow(
            "alias.yml",
            "on: push\njobs:\n  a:\n    runs-on: &runner self-hosted\n"
            "  b:\n    runs-on: *runner\n",
        )
        status, out, _ = run([])
        self.assertEqual(status, 1)
        self.assertEqual(out.count("runs-on self-hosted"), 2)

    def test_from_a_subdirectory_the_whole_repository_is_read(self) -> None:
        # Run from elsewhere in the tree, a listing relative to the current
        # directory would hold no workflow, and an empty run would pass.
        self.workflow("bad.yml", "on: push\njobs:\n  b:\n    runs-on: self-hosted\n")
        (self.root / "src").mkdir()
        os.chdir(self.root / "src")
        status, out, _ = run([])
        self.assertEqual(status, 1)
        self.assertTrue(out.startswith(".github/workflows/bad.yml: job b:"))

    def test_a_file_under_a_workflows_subdirectory_is_not_a_workflow(self) -> None:
        # GitHub reads workflows only from the directory itself, so a fixture
        # kept below it is not judged.
        (self.root / ".github/workflows/fixtures").mkdir()
        self.workflow("fixtures/example.yml", "jobs:\n  a:\n    runs-on: self-hosted\n")
        self.assertEqual(run([]), (0, "", ""))

    def test_a_clean_repository_exits_zero(self) -> None:
        self.workflow("ok.yml", "on: push\njobs:\n  a:\n    runs-on: ubuntu-24.04\n")
        self.assertEqual(run([]), (0, "", ""))

    def test_a_file_yq_cannot_parse_fails_rather_than_passing(self) -> None:
        self.workflow("broken.yml", "jobs: [unclosed\n")
        status, out, err = run([])
        self.assertEqual((status, out), (1, ""))
        self.assertIn("parsing .github/workflows/broken.yml failed", err)

    def test_without_yq_it_fails_rather_than_passing(self) -> None:
        self.workflow("ok.yml", "on: push\njobs:\n  a:\n    runs-on: ubuntu-24.04\n")
        only_git = self.root / "bin"
        only_git.mkdir()
        git = subprocess.run(
            ["git", "--exec-path"], capture_output=True, text=True, check=True
        )
        (only_git / "git").symlink_to(Path(git.stdout.strip()) / "git")
        with mock.patch.dict(os.environ, {"PATH": str(only_git)}):
            status, _, err = run([])
        self.assertEqual(status, 1)
        self.assertIn("yq is not on PATH", err)


if __name__ == "__main__":
    unittest.main()

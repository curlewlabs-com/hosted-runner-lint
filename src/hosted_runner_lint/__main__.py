"""`python3 -m hosted_runner_lint`, the command-line entry point; cli.py owns it."""

from hosted_runner_lint.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

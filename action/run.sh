#!/bin/sh
# The action's one step: run the package from the action's own checkout, which
# needs no install because it has no dependencies. -P keeps the directory it
# runs in off the import path, so a file of the repository being judged cannot
# stand in for a module of the lint.
set -eu
PYTHONPATH="$GITHUB_ACTION_PATH/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python3 -P -m hosted_runner_lint

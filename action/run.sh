#!/bin/sh
# The action's one step: run the package from the action's own checkout, which
# needs no install because it has no dependencies. The import path is the
# package alone, so no file of the repository being judged can stand in for a
# module of the lint or of the standard library: -P keeps the directory it runs
# in off the path, and PYTHONPATH is set rather than extended, since an
# inherited entry such as `.` would put that directory back.
set -eu
PYTHONPATH="$GITHUB_ACTION_PATH/src"
export PYTHONPATH
exec python3 -P -m hosted_runner_lint

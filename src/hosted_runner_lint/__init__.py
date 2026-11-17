"""Check that every workflow job runs on a GitHub-hosted standard runner. See the README.

The command is the interface (cli.py); runners.py is how a job is judged.
"""

import sys

# Checked here, before any other module of the package is imported, so an older
# interpreter gets this message rather than a syntax error from a newer form.
if sys.version_info < (3, 12):  # noqa: UP036 - the point is to run on older ones
    sys.exit("hosted-runner-lint needs Python 3.12 or newer")

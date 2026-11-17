# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
privately via
[GitHub's security advisory feature](https://github.com/curlewlabs-com/hosted-runner-lint/security/advisories/new).

Do not open a public issue for security vulnerabilities.

## Scope

The lint reads workflow files and runs `git ls-files` and `yq`. It never runs
what it reads. The security surface is:

- **The `git` and `yq` it runs.** These are the first on `PATH`, trusted the way
  `python3` is. Each is given a file name, never file contents as arguments.
- **The files it reads.** These are the repository's tracked workflow files, or
  the paths named on the command line.
- **A false clean.** A job the lint passes that can run on a self-hosted or
  larger runner is a defect in what the lint promises. Report it privately: for
  a public repository it is the exposure the lint exists to prevent.

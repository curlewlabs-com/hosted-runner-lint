# hosted-runner-lint

## What it is

A lint that fails on any GitHub Actions workflow job that does not run on a
GitHub-hosted standard runner:

```text
.github/workflows/ci.yml: job build: runs-on self-hosted: a public repository runs fork code on it
```

It is meant for public repositories, and for any repository whose workflows
should never reach a machine you own or a runner you pay for by the minute.

## Why it exists

A public repository's workflows run on pull requests from forks, and a pull
request from a fork can change what those workflows run. On a GitHub-hosted
runner that code runs on a fresh virtual machine GitHub throws away afterward.
On a self-hosted runner it runs on your machine, beside whatever else that
machine can reach. GitHub's own documentation recommends never using self-hosted
runners with public repositories.

The mistake is easy to make and hard to see in review. A workflow copied from a
private repository keeps its `runs-on: [self-hosted, linux]`; a matrix entry
adds one custom label among several standard ones; an alias points two jobs at
the same anchor. Fork-approval settings reduce the exposure but are one setting
away from none.

Larger runners (`-large`, `-xlarge`, and runner groups) are refused too: they
are billed per minute even for a public repository.

## How to use it

As a GitHub Action, after a checkout. Pin it by commit:

```yaml
- uses: actions/checkout@<sha> # vX.Y.Z
  with:
    persist-credentials: false
- uses: curlewlabs-com/hosted-runner-lint@<sha> # vX.Y.Z
```

As a command, from inside a repository, with `git` and
[mikefarah's yq](https://github.com/mikefarah/yq) on `PATH` (GitHub's Linux and
macOS runner images ship both):

```sh
pip install git+https://github.com/curlewlabs-com/hosted-runner-lint@v0.1.0
hosted-runner-lint                         # every tracked workflow
hosted-runner-lint .github/workflows/a.yml # just this one
```

It prints one line per finding and exits 1 on any. It also exits 1, with the
reason on stderr, when it could not run (no `git` or `yq`, a file `yq` cannot
parse), so a lint that did not run never reads as clean.

## What it accepts

A job passes when every label its `runs-on` names is one of the standard runner
labels GitHub lists for public repositories in
[its runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
compared without regard to case. The list is written out in
`src/hosted_runner_lint/runners.py` rather than matched by a pattern: a
self-hosted runner can carry any label, including one shaped like a hosted one,
so a label GitHub adds is refused until the list is updated.

A job that calls a reusable workflow (`uses:` with no `runs-on`) passes here;
its jobs are judged in the repository that holds it.

## What it reads, and what it refuses

- **The parsed document.** Each tracked `.github/workflows/*.yml` or `*.yaml`,
  in that directory itself as GitHub reads it, is parsed by `yq` with anchors
  and aliases expanded, so a label is judged as GitHub reads it, not as it is
  written.
- **A matrix label.** `runs-on: ${{ matrix.KEY }}` is judged by every value the
  job's literal `strategy.matrix` gives KEY, in its list and in its `include`
  entries, matching KEY without regard to case as GitHub does.
- **Refused, not guessed:** any other expression in `runs-on` (an input, a
  `fromJSON`, a label built from parts), a matrix built by an expression, and a
  matrix key with no values. Their values are known only when the workflow runs,
  so passing them would be a guess.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option. Releases published under the MIT license alone may also be used
under either license.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in this project by you, as defined in the Apache-2.0 license,
shall be dual licensed as above, without any additional terms or conditions.

# ci-workflows

Shared GitHub Actions CI for this account's repositories.

Before this repo existed, every repository carried its own hand-written
`ci.yml`. Across 36 workflow files there were 165 `uses:` lines, none pinned to a
commit, spread over several major versions of the same actions. One job in one
repository set a timeout. Two set `permissions:`. Five set a concurrency group.
None wrote a job summary, so reading a failure meant opening the run and
scrolling the raw log.

This repository holds one reusable workflow per language. Each repository keeps a
short caller workflow that says which stages to run. Changing how CI behaves
everywhere is now an edit to one file here instead of an edit to 36 files.

## What a caller looks like

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

permissions:
  contents: read

jobs:
  ci:
    uses: preston-bernstein/ci-workflows/.github/workflows/python.yml@v1
    with:
      lint: ruff check .
      test: pytest -m "not network"
```

The `@v1` reference is a moving tag on this repository. A change here reaches
every caller once `v1` is moved, and a bad commit on `main` does not.

## The workflows

| Workflow | For | Stages |
| --- | --- | --- |
| `python.yml` | Python | install, lint, format check, type check, tests |
| `node.yml` | Node and TypeScript | install, lint, type check, tests, build |
| `go.yml` | Go | build, vet, golangci-lint, tests |
| `shell.yml` | shell scripts | ShellCheck, plus any repo guard scripts |
| `actions-lint.yml` | any repo | actionlint, zizmor |

Every stage input defaults to empty or to the command the repositories already
ran. An empty input skips that stage, so a caller only names what it wants.

Beyond the stage commands, each workflow takes:

| Input | What it is for |
| --- | --- |
| `setup` | A command between install and the stages, such as a browser download |
| `checks` | Repo-specific guard commands, one per line, each with its own summary row |
| `fetch-depth` | `0` when a tool diffs against the base ref and needs full history |
| `env` | Extra environment variables for every stage, one `KEY=VALUE` per line |
| `timeout-minutes` | Overrides the default for a slow suite |
| `runs-on` | A different runner label |

The Python and Node workflows also accept an `ssh-private-key` secret, for a
repo whose install pulls a private sibling over SSH:

```yaml
    secrets:
      ssh-private-key: ${{ secrets.CREDENTIAL_CRYPTO_DEPLOY_KEY }}
```

## What each workflow does that the old ones did not

**Every stage runs, even after one fails.** Stages are marked
`continue-on-error` and a final step fails the job if any of them failed. One run
now reports the lint error *and* the test failure, instead of stopping at the
first and hiding the second until the next push.

**Failures are readable from the run's summary page.** Each job writes a table of
stages and results to `$GITHUB_STEP_SUMMARY`, and inlines the last 40 lines of
any failing stage's log underneath it. Full logs upload as an artifact.

Those logs are written to `$RUNNER_TEMP/ci-logs`, outside the checkout. Writing
them into the working tree meant a repo's own tree-wide checks could see them:
anno-1800-stamps validates that every tracked file is a zlib stream, and failed
on the workflow's own log files.

**Actions are pinned to a commit.** A tag like `v4` is a moving reference that
whoever controls the action can repoint. Every `uses:` here names a 40-character
commit SHA with the version in a trailing comment. Dependabot bumps them weekly,
so pinning does not mean going stale.

**Jobs have a timeout.** Without one, a hung step runs until GitHub's six-hour
limit. Every job here defaults to 10 or 15 minutes.

**Tokens are read-only.** Each workflow sets `permissions: contents: read`, and
checkouts set `persist-credentials: false` so the token is not left in
`.git/config` for later steps to pick up.

**The package manager and install command are detected, not assumed.** The Python
workflow looks for a `pyproject.toml` with dev extras, then a plain
`pyproject.toml`, then a `requirements.txt`. The Node workflow reads the lockfile
to choose pnpm or npm, and turns the dependency cache off when the lockfile it
would key on is missing, rather than failing on an unresolvable cache path. Both
print which branch they took, in the log and in the summary.

**ShellCheck comes from the runner image.** The previous setup used
`ludeeus/action-shellcheck`, which has had no release since January 2023, and one
repository referenced its `master` branch — a reference that can change under it
at any time. The runner already ships ShellCheck.

## Pinning policy

The workflow linter requires a commit SHA for third-party actions, and allows a
tag only for this account's own reusable workflows. Without that exception,
`@v1` in every caller counts as an unpinned reference, and satisfying the linter
would mean editing forty repos for each change here — the thing this repo exists
to avoid. A repo that ships its own `.github/zizmor.yml` keeps it.

## Changing these workflows

`main` is what the `self-check` job lints; `v1` is what callers use. After
merging a change to `main` and seeing it green, move the tag:

```sh
git tag -f v1 && git push -f origin v1
```

Callers pick up the change on their next run. To test a change before moving the
tag, point one caller at `@main` and push.

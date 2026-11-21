# ci-workflows

Reusable GitHub Actions workflows that run CI for all of this account's repositories.

Each repository keeps a short caller workflow that names the stages it wants. The shared logic lives here. A change to CI behavior is one edit in this repo, not one edit per repo.

## Callers pick stages with inputs

A caller uses one workflow from this repo and sets the stage commands:

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

`@v1` is a tag that moves. A change reaches callers only when `v1` moves, so a bad commit on `main` does not break them.

## Five workflows cover the common cases

| Workflow | For | Stages |
| --- | --- | --- |
| `python.yml` | Python | install, lint, format check, type check, tests |
| `node.yml` | Node and TypeScript | install, lint, format check, type check, tests, build |
| `go.yml` | Go | build, vet, golangci-lint, tests |
| `shell.yml` | shell scripts | ShellCheck, plus your own `checks` |
| `actions-lint.yml` | any repo | actionlint, zizmor (workflow security linter) |

An empty stage input skips that stage. Some defaults are not empty: `python.yml` runs `ruff check .` and `pytest -q`. Read the `inputs:` block at the top of each file for the full list.

`python.yml` and `node.yml` share these inputs:

| Input | Use |
| --- | --- |
| `setup` | A command between install and the stages, such as a browser download |
| `checks` | Repo guard commands, one per line. Each gets its own summary row |
| `non-blocking` | Stage keys that report a failure without failing the job |
| `timeout-minutes` | Overrides the default (15 minutes, or 10 for `shell.yml` and `actions-lint.yml`) |
| `runs-on` | A different runner label |
| `working-directory` | Run in a subdirectory |

`go.yml` takes `non-blocking`, `timeout-minutes`, `runs-on` and `working-directory`, but not `setup` or `checks`. `shell.yml` takes `checks`, `timeout-minutes`, `runs-on` and `working-directory`. `python.yml`, `node.yml` and `go.yml` also take `fetch-depth` and `env`. `python.yml` alone takes `lfs-include`, a comma-separated list of Git LFS paths to download.

`python.yml`, `node.yml` and `go.yml` accept an `ssh-private-key` secret. Use it when the install pulls a private repo over SSH:

```yaml
    secrets:
      ssh-private-key: ${{ secrets.CREDENTIAL_CRYPTO_DEPLOY_KEY }}
```

## Every stage runs, and failures are easy to read

1. Each stage runs even if an earlier one failed. A final step fails the job if any stage failed. One run reports the lint error and the test failure together.
2. Each job writes a table of stages and results to the run's summary page. Under it, the job inlines the last 40 lines of each failed stage's log. `actions-lint.yml` inlines 80.
3. Stage logs go to `$RUNNER_TEMP/ci-logs`, outside the checkout. Repo-wide checks in the caller then never see them.

## The workflows are locked down

- Third-party actions are pinned to a 40-character commit SHA, with the version in a trailing comment. Dependabot bumps the pins weekly, after a 7-day wait for new releases.
- Each workflow sets `permissions: contents: read`. Checkouts set `persist-credentials: false`.
- Every job has a timeout.
- `python.yml` picks the install command from `pyproject.toml` or `requirements.txt`. `node.yml` picks pnpm or npm from the lockfile. Both log which one they chose.
- `shell.yml` uses the ShellCheck that ships on the runner image.

## Adopt a check on code that fails it

Set `non-blocking: lint`. The stage still runs and shows its result in the summary, but it does not fail the job. Remove the line when the backlog is clean. The check then becomes a gate.

## zizmor allows this account's workflows by tag

`actions-lint.yml` demands a commit SHA for third-party actions. It allows a tag for workflows owned by `trusted-owner` (default `preston-bernstein`). Without this, every `@v1` caller would fail the lint. A repo that has its own `.github/zizmor.yml` keeps it.

`fail-on-zizmor: false` reports zizmor findings without failing the job.

## Change a workflow, then move the tag

The `self-check` workflow lints this repo on every push and pull request to `main`. Callers use `v1`, not `main`.

1. Merge the change to `main`.
2. Wait for `self-check` to pass.
3. Move the tag:

   ```sh
   git tag -f v1 && git push -f origin v1
   ```

To test first, point one caller at `@main` and push.

# Agent rules for ci-workflows

This repo holds reusable GitHub Actions workflows. Callers use them by tag, so a bad change reaches every repo.

## Commands

- Core gate: `bash scripts/core-validate.sh`
- Actions gate: `bash scripts/gha-validate.sh`
- Writing gate: `bash scripts/writing-validate.sh` (set `WRITING_ALL=1` to check every file)
- Install the pinned tools first: `bash scripts/install-gate-tools.sh`. Then put `~/.local/bin` on PATH.
- Hook: `git config core.hooksPath .githooks`. Never commit with `--no-verify`.

## Rules

- Reuse before you write. Search for an existing function or module first. Extend it instead of adding a near copy.
- Put variants in data and in generic code, not in copies. When two things differ only in a type or a value, write one function that takes the type or the value.
- Extract on the second real occurrence, not the first guess. Never merge code that looks alike but belongs to different domains.
- No boolean flag arguments. Two behaviors are two functions.
- Organize by domain (orders, billing, auth), not by kind (utils, helpers, managers). Dependencies point one way: edge to domain, never back.
- A function does one thing at one level of detail. Use guard clauses to return early. Keep it under 50 lines, under 10 branches, at most 4 parameters.
- Names say what a thing is or does. No `data`, `info`, `tmp`, `handle`, `process` as a whole name.
- Prefer composition and plain functions to inheritance. Keep side effects at the edges.
- Fail loudly: return or raise an error with context. Never swallow one. Comments say why, not what.
- Delete dead code and unused options. Concise means fewer concepts, not shorter names.
- A behavior change ships with a test that fails without it. Do not edit generated files; change the generator.
- Never edit a limit or a config to make a run pass. Fix the code. A waiver goes in `.core-allow` with a reason.

- Pin every `uses:` to a full 40-character commit SHA with the version in a trailing comment. No `@v4`, `@main`.
- Set `permissions: contents: read` at the top of every workflow and raise it per job only where needed.
- Never put `${{ github.event... }}`, `${{ github.head_ref }}` or `${{ inputs.x }}` inside `run:`. Pass it through `env:` and read `$VAR`.
- Do not use `pull_request_target`. If a workflow truly needs it, never check out the PR head, and add `# gha-allow: pull_request_target <reason>`.
- `actions/checkout` gets `persist-credentials: false`. Every job has `timeout-minutes`. No `secrets: inherit`.
- Authenticate to clouds and registries with OIDC, not stored long-lived secrets.
- Never edit the workflow checks, the zizmor config or branch protection to make a run pass. Fix the workflow.

- Use plain words and American spelling: "color", "behavior", "organize".
- Write steps as numbered imperatives. Put the condition first: "If the build fails, run X".
- A code comment says why, or what breaks if someone changes the line. It does not say what the next line does. Three sentences at most.
- No AI filler. The Vale styles in `scripts/styles` list the banned words and phrases.
- An error rule fails the gate. A warning prints and passes. A false positive gets `<!-- vale off -->` with a reason, or a line in `.writing-allow`.

## Traps

- `scripts/*` copies of the pack gates stay unchanged. Update them by copying from the pack.
- `.core-baseline.json` and `CORE_DUP_THRESHOLD` in `.core-config` only shrink.
- Tool versions live in `.github/tools/` (hash-locked) and `scripts/install-gate-tools.sh` (SHA-256). Bump them together.
- `self-check.yml` runs the gates once. Do not add them to another workflow.

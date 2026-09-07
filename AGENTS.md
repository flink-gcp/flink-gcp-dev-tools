# Development guide for coding agents

This repository owns shared workflow skills, a PR template, and a Hugo documentation module.
Read `docs/adr/0001-share-development-assets.md` before changing distribution or ownership boundaries.
Read `docs/inventory.md` before migrating a consumer.

- `just test` executes installation scenarios in disposable Git repositories.
- `just lint` checks workflows and Markdown.
- `just docs` builds the local Hugo module through the example site.
- `just docs-chroma` regenerates the syntax palettes.
- `just pin-actions` pins GitHub Actions references.

Use `mise x -- just <recipe>` outside an activated shell.
Run checks appropriate to the changed surfaces; this repository has no Maven build or cloud service tests.
Keep consumer-specific verification commands and compatibility policies in the consumer's guidance.
Keep personal agent configuration, credentials, and memories outside the shared files.
Use the skill-creator and english-tech-writing skills when available for their respective changes.

Use `gh` for GitHub operations and a dedicated worktree under `/tmp/worktrees/flink-gcp-dev-tools/` for each PR.
After the initial empty commit, every change goes through a Draft PR with filled WHAT and WHY sections from `.github/PULL_REQUEST_TEMPLATE.md`.
Before every branch push, use `$push-pr-branch` and inspect the explicit deletion list.
After Draft creation, use `$self-review`, `$self-review-round-two`, and `$independent-review` in that order.
Record review feedback inline with an empty review body and a comments array.
Only mark Ready after the required review flow and a successful current aggregate `CI passed` check.
The restored independent-review skill retains the recorded unavailable-reviewer exception; a running or uncollected review is incomplete.
The maintainer merges; clean up only the verified target when requested.

Write all tracked text and GitHub content in English.
Keep task-specific automation in temporary directories and never commit private memory or machine-specific configuration.

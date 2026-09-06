# Contributing

Install the versions in `mise.toml`, then use the repository justfile:

```sh
mise install
mise x -- just lint
mise x -- just test
mise x -- just docs
```

The tests execute the installation recipe in temporary Git repositories with a controlled GitHub CLI response.
The example site builds the local Hugo module with the pinned upstream theme and checks the rendered highlighting, stylesheet import, and theme control.
When changing theme behavior, also inspect the rendered site in both color schemes and at a narrow viewport.

Create each branch in a dedicated Git worktree and open a Draft PR using `.github/PULL_REQUEST_TEMPLATE.md`.
Use the four workflow skills in sequence: `push-pr-branch`, `self-review`, `self-review-round-two`, and `independent-review`.
Record each review inline on relevant changed lines.
Wait for the current `CI passed` check and the required review flow before marking the PR Ready; the maintainer merges it.
The shared independent-review skill retains the original exception for a reviewer that cannot run, with the reason recorded; an uncollected result does not qualify.

Keep shared instructions independent of consumer package names and build commands.
Test installation changes through `just test`; use synthetic temporary projects rather than modifying a developer's global agent configuration.
Run `just docs-chroma` to regenerate the two syntax palettes when deliberately changing their Hugo-generated output.
Use `just pin-actions` when adding or changing a GitHub Actions reference.

Write documentation, code comments, commits, and GitHub text in English.
Use Apache-2.0 headers with `The flink-gcp authors`, preserving third-party provenance.
Task-specific automation and review artifacts belong outside the repository.

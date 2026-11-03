# Contributing

Install the versions in `mise.toml`, then use the repository justfile:

```sh
mise install
mise x -- just lint
mise x -- just test
mise x -- just docs
```

Every test is a pytest suite run through uv, and `just lint` checks Markdown with rumdl and the installation script with shellcheck; the repository does not use Node.js.
The installation tests execute the recipe in temporary Git repositories with a controlled GitHub CLI response, including failed and interrupted replacements.
The script tests run the shared tools' suite with Python 3.14 and 3.11, including a check that each tool imports without site-packages.
The example site builds the local Hugo module with the pinned upstream theme and checks the rendered highlighting, stylesheet import, theme control, and the files the search module references.
The Hugo Book tests check the theme files and notices the example site publishes, and build temporary copies of the module and the site to check the excluded features and the notice guard.
No test executes the search module, so after changing `hugo/assets/search.js` also check in a browser that a query typed before the index loads shows results for the latest input once it arrives.
When changing theme behavior, also inspect the rendered site in both color schemes and at a narrow viewport.

Create each branch in a dedicated Git worktree and open a Draft PR using `.github/PULL_REQUEST_TEMPLATE.md`.
Use the four workflow skills in sequence: `push-pr-branch`, `self-review`, `self-review-round-two`, and `independent-review`.
Record each review inline on relevant changed lines.
Wait for the current `CI passed` check and the required review flow before marking the PR Ready; the maintainer merges it.
The shared independent-review skill retains the original exception for a reviewer that cannot run, with the reason recorded; an uncollected result does not qualify.

Keep shared instructions independent of consumer package names and build commands.
Test installation changes through `just test-install`; use synthetic temporary projects rather than modifying a developer's global agent configuration.
Add a shared tool to the `scripts` list in `install-dev-tools` together with its tests; the installation tests require the list to match the tracked top-level files in `scripts/`.
Run `just docs-chroma` to regenerate the two syntax palettes when deliberately changing their Hugo-generated output.
Use `just pin-actions` when adding or changing a GitHub Actions reference.

Write documentation, code comments, commits, and GitHub text in English.
Use Apache-2.0 headers with `The flink-gcp authors`, preserving third-party provenance.
Task-specific automation and review artifacts belong outside the repository.

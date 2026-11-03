# flink-gcp development tools

Shared workflow skills, repository tools, a pull request template, and documentation design assets for flink-gcp projects.
Consumers select a version explicitly and review updates in their own repositories.

| Component | Source | Consumer integration |
| --- | --- | --- |
| Push and review procedures | `skills/` | Tracked copies installed by a just recipe |
| Central Portal publication tool | `scripts/central-portal.py` | Tracked copy installed by a just recipe |
| Pull request template | `templates/PULL_REQUEST_TEMPLATE.md` | Copy into `.github/` |
| Hugo Book design | `hugo/` | Hugo module pinned through `go.mod` and `go.sum` |

The four skills cover pushing a PR branch, two distinct self-review rounds, and review by a different model or a human who authored none of the change.
Repository commands, compatibility policies, release coordinates, and service-specific tests remain with each consumer.
See the [sharing decision](docs/adr/0001-share-development-assets.md) and [source inventory](docs/inventory.md).

## Install workflow skills

The installation recipe requires Bash, Git, GitHub CLI (`gh`), tar, and just.
Use the supported versions of the agent applications in the consuming project.

Copy [`examples/dev-tools.just`](examples/dev-tools.just) into a consumer as `dev-tools.just`, and import it from that repository's justfile.
Set a full commit SHA from this repository in the tracked justfile:

```just
import 'dev-tools.just'

dev_tools_revision := "<full commit SHA>"

skills-sync: (install-skills dev_tools_revision)
```

Run `just skills-sync` at the consumer root and commit the installed `.agents/skills/` directories together with the revision pin.
The recipe selects only `push-pr-branch`, `self-review`, `self-review-round-two`, and `independent-review`.
It copies their supporting resources too and preserves unrelated skills.
Changing the revision and running the recipe produces the content diff to review in an update PR.
The same procedure can return to a previous revision.

A tag may identify the requested version, but resolve it before writing the pin:

```sh
gh api repos/flink-gcp/flink-gcp-dev-tools/commits/<tag> --jq .sha
```

Installation downloads the archive at that SHA; it does not select a newer release.
It checks that all four skills are present before replacing any of them and refuses to overwrite differing local edits or untracked resources in a managed directory.
Identical installed content is left alone, including on an immediate repeat before committing.
Download or archive-validation failures leave the installed skills in place.
After a successful setup, the tracked copies are available offline and in fresh Git worktrees.
No submodule or separately maintained shared checkout is required.

Keep repository-specific guidance in the consumer's `AGENTS.md` and references, outside these managed directories.
The consumer retains responsibility for its agent discovery paths; for the existing flink-gcp layout, `.claude/skills` points to `../.agents/skills`.
The shared repository itself uses relative symlinks to its canonical `skills/` tree.

## Install repository tools

The same `dev-tools.just` provides `install-scripts`, with the same requirements.
A consumer that installs both units uses one pin for both, so sync them together:

```just
dev-tools-sync: (install-skills dev_tools_revision) (install-scripts dev_tools_revision)
```

Run `just dev-tools-sync` at the consumer root and commit the installed skills, `scripts/central-portal.py`, and the revision pin together.
Running only one of the two recipes after changing the pin would leave the other unit at the previous revision with nothing to detect it.
The scripts recipe writes the file to its existing path, so the consumer's recipes and release workflow keep invoking it unchanged.
It applies the same SHA, validation, local-edit, and failure rules as the skills installation, and it leaves every other file under `scripts/` alone.
The recipe refuses to overwrite uncommitted edits, but a committed edit to an installed copy is replaced by the next sync, whose diff then reverts that edit.
This file was named `examples/skills.just` before it gained `install-scripts`; consumer guidance that names the old path refers to the same recipes.

The shared tools import only the Python standard library and support Python 3.11 and later.
Run them with the consumer's own interpreter; this repository's `pyproject.toml` and `uv.lock` serve only its tests and are not installed.
Keep the consumer's credentials, workflow steps, and tests of that wiring in the consumer.
Send behavior changes to this repository instead of editing the installed copy; the [ADR amendment](docs/adr/0001-share-development-assets.md#amendment-share-standard-library-repository-tools) records which tools are shared.

## Use the documentation design

The module preserves the existing flink-connector-gcp light/dark theme control, layout, and syntax palettes.
It imports Hugo Book v0.14.0 and supplies `BookTheme = "auto"`.
The shared search override waits for the index before querying it and searches the latest input when loading completes.
Consumers use this implementation through the module instead of keeping a local `assets/search.js`.
The consuming site enables class-based syntax highlighting explicitly, as shown below.
Use Hugo Extended 0.164.0 and Go 1.26, as recorded in `mise.toml`.

From a consumer's Hugo site, add the selected shared commit:

```sh
hugo mod get github.com/flink-gcp/flink-gcp-dev-tools/hugo@<full commit SHA>
```

Import it in the site's Hugo configuration:

```toml
[module]
  [[module.imports]]
    path = "github.com/flink-gcp/flink-gcp-dev-tools/hugo"

[markup.highlight]
  noClasses = false
```

Commit the resulting `go.mod` and `go.sum`.
Keep the highlighting setting in the consumer configuration; under Hugo's default merge rules, the module's `markup` configuration is not inherited.
The site keeps its own title, base URL, repository links, content, source-snippet mounts, Javadoc generation, and Pages deployment workflow.
Remove local copies of the shared theme files listed in the [inventory](docs/inventory.md) during migration; Hugo gives local files precedence over module files.
The [example site](examples/site/) demonstrates the import with a local replacement for development.
The module owns the two `docs/inject` partials; a consumer adding content at those same hooks must deliberately compose or override them.

## Development and provenance

See [CONTRIBUTING.md](CONTRIBUTING.md) for commands and the PR workflow.
The sources were extracted from the flink-gcp projects listed in the [inventory](docs/inventory.md).
This repository uses [Apache License 2.0](LICENSE).
Hugo Book remains a pinned dependency; the adapted `hugo/assets/search.js` preserves its upstream MIT notice.
Review that override against the pinned theme when updating Hugo Book.

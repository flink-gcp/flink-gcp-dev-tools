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

## Install workflow skills and repository tools

The installation recipe requires Bash, Git, GitHub CLI (`gh`), tar, and just.
Use the supported versions of the agent applications in the consuming project.

Copy [`examples/dev-tools.just`](examples/dev-tools.just) into a consumer as `dev-tools.just`, and import it from that repository's justfile.
Set a full commit SHA from this repository in the tracked justfile:

```just
import 'dev-tools.just'

dev_tools_revision := "<full commit SHA>"

dev-tools-sync: (install-dev-tools dev_tools_revision)
```

The recipe installs only the skills `push-pr-branch`, `self-review`, `self-review-round-two`, and `independent-review` under `.agents/skills/`, and the tool `scripts/central-portal.py`.
It copies the skills' supporting resources too, and it preserves unrelated skills and every other file under `scripts/`.
Run `just dev-tools-sync` at the consumer root and commit the installed copies together with the revision pin.
The tool keeps its existing path, so the consumer's recipes and release workflow keep invoking it unchanged.
Changing the revision and running the recipe produces the content diff to review in an update PR.
The same procedure can return to a previous revision.

A tag may identify the requested version, but resolve it before writing the pin:

```sh
gh api repos/flink-gcp/flink-gcp-dev-tools/commits/<tag> --jq .sha
```

Installation downloads the archive at that SHA once; it does not select a newer release.
It checks every selected skill and tool before replacing any of them, and it refuses to overwrite differing local edits or untracked files at a managed path.
A committed edit to an installed copy is not protected: the next sync replaces it, and its diff then reverts that edit.
Identical installed content is left alone, including on an immediate repeat before committing.
Download or archive-validation failures leave the installed copies in place.
If a replacement fails or the recipe is interrupted by SIGINT, SIGTERM, or SIGHUP, it restores every path it has already replaced, so the skills and the tool stay at one revision.
A SIGKILL or a crash cannot be handled, so it can leave some paths replaced and the rest unchanged.
Running the sync again skips each path already identical to the pinned revision and installs the rest.
If `git status` reports changes at a path the kill left mid-move, such as a tracked path now missing or a partial copy, that rerun refuses it as local changes and replaces nothing; discard that path, for example with `git restore` and `git clean`, and run the sync again.
The interrupted run leaves its `dev-tools.*` temporary directory under `TMPDIR`, or `/tmp` when that is unset, with the previous copy of any path it had moved aside in `previous/`.
If a restore itself fails, the recipe names each path it could not restore and where its previous copy remains.
After a successful setup, the tracked copies are available offline and in fresh Git worktrees.
No submodule or separately maintained shared checkout is required.

Keep repository-specific guidance in the consumer's `AGENTS.md` and references, outside these managed directories.
The consumer retains responsibility for its agent discovery paths; for the existing flink-gcp layout, `.claude/skills` points to `../.agents/skills`.
The shared repository itself uses relative symlinks to its canonical `skills/` tree.

### Migrate from the earlier recipes

This file was named `examples/skills.just` before it gained the tool; consumer guidance that names the old path refers to the same file.
Earlier versions provided `install-skills`, and later also `install-scripts`, instead of `install-dev-tools`.
When re-copying the file, make these changes in the same consumer PR:

- Replace the `skills-sync: (install-skills dev_tools_revision)` recipe with the `dev-tools-sync` recipe above, and rename `skills-sync` wherever the consumer's guidance names it.
- Update guidance that says the sync touches only `.agents/skills/`, because it now also manages `scripts/central-portal.py`.
  The first sync replaces a committed copy of that file that differs from the pinned revision, so review its diff for local fixes that have not landed here.
- Point a lint that extracts the installation script with `just --show` at `install-dev-tools`.

## Receive release updates

Each release tag `vX.Y.Z` here opens or updates a Draft PR named `Update flink-gcp-dev-tools to vX.Y.Z` in every consumer listed in the [`Update consumers`](.github/workflows/update-consumers.yaml) workflow, always for the latest release.
The PR comes from the `dev-tools/update` branch, authored by `flink-gcp-bot`.
It replaces `dev-tools.just` with the tagged commit's copy, moves `dev_tools_revision` to that commit and runs the sync as described above, and moves the Hugo module as described below, followed by `hugo mod tidy`.
Its description links the shared changes since the previous pin and lists the consumer's lines that still name the previous commit outside `/blob/` and `/tree/` permalinks.
The [ADR amendment](docs/adr/0001-share-development-assets.md#amendment-propose-each-release-to-the-consumers-from-a-bot) records how the bot behaves and how its PRs are reviewed, and the [inventory](docs/inventory.md#release-updates) lists what a consumer provides for it.

In a consumer, write guidance that does not repeat the pinned SHA, so an update needs no manual edit.
A release that requires migration may fail to prepare instead of opening a PR; its release notes then describe the migration.
The bot does not replace an update branch that carries a commit anyone else authored or amended, so finish or delete such a branch before the next release.
Updating a consumer by hand, at any commit from `main`, remains possible.

## Use the shared repository tools

The shared tools import only the Python standard library and support Python 3.11 and later.
Run them with the consumer's own interpreter; this repository's `pyproject.toml` and `uv.lock` serve only its tests and are not installed.
Keep the consumer's credentials, workflow steps, and tests of that wiring in the consumer.
Send behavior changes to this repository instead of editing the installed copy; the [ADR amendment](docs/adr/0001-share-development-assets.md#amendment-share-standard-library-repository-tools) records which tools are shared.

## Use the documentation design

The module preserves the existing flink-connector-gcp light/dark theme control, layout, and syntax palettes.
It imports Hugo Book v0.14.0, restricted to the files its notices cover, and supplies `BookTheme = "auto"`.
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
Use a `go.mod` `replace` like it does to try a local module checkout; with `HUGO_MODULE_REPLACEMENTS`, Hugo cannot resolve the module's own Hugo Book import and may rewrite the site's `go.mod` to the latest Hugo Book.
The module owns the two `docs/inject` partials; a consumer adding content at those same hooks must deliberately compose or override them.

## Publish the theme's notices

The module decides which Hugo Book files a site publishes and carries their notices, as [ADR-0002](docs/adr/0002-the-design-module-owns-the-theme-files-and-their-notices.md) records.
From Hugo Book's `static/` directory it publishes only the two favicons and the Fuse.js search module.
Hugo Book's KaTeX, Mermaid and asciinema-player features are excluded, so their shortcodes fail the build and their code blocks render as plain code.
Import Hugo Book only through this module: do not set `ignoreImports` on it, and do not import Hugo Book before it, because the first import of a module decides its mounts.

Add a hidden site licenses page that states the licence of the site's own sources and calls `{{% theme-notices %}}`, as the [example page](examples/site/content/docs/licenses.md) does.
Use the `%` delimiters; with `<` the build still succeeds, but the page shows the notices' Markdown as text.
The shortcode fails the build unless the site resolves the Hugo Book version its notices document, through this module's import, without a replacement, workspace or vendored copy.
A consumer that requires another Hugo Book version itself therefore needs a module update first.

## Development and provenance

See [CONTRIBUTING.md](CONTRIBUTING.md) for commands and the PR workflow.
The sources were extracted from the flink-gcp projects listed in the [inventory](docs/inventory.md).
This repository uses [Apache License 2.0](LICENSE).
Hugo Book remains a pinned dependency; the adapted `hugo/assets/search.js` preserves its upstream MIT notice.
Review that override and the notices against the new theme when updating Hugo Book, as ADR-0002 describes.

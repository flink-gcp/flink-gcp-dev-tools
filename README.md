# flink-gcp development tools

Shared workflow skills, a pull request template, and documentation design assets for flink-gcp projects.
Consumers select a version explicitly and review updates in their own repositories.

| Component | Source | Consumer integration |
| --- | --- | --- |
| Push and review procedures | `skills/` | Tracked copies installed by a just recipe |
| Pull request template | `templates/PULL_REQUEST_TEMPLATE.md` | Copy into `.github/` |
| Hugo Book design | `hugo/` | Hugo module pinned through `go.mod` and `go.sum` |

The four skills cover pushing a PR branch, two distinct self-review rounds, and review by a different model or a human who authored none of the change.
Repository commands, compatibility policies, release coordinates, and service-specific tests remain with each consumer.
See the [sharing decision](docs/adr/0001-share-development-assets.md) and [source inventory](docs/inventory.md).

## Install workflow skills

The installation recipe requires Bash, Git, GitHub CLI (`gh`), tar, and just.
Use the supported versions of the agent applications in the consuming project.

Copy [`examples/skills.just`](examples/skills.just) into a consumer as `dev-tools.just`, and import it from that repository's justfile.
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

## Use the documentation design

The module preserves the existing flink-connector-gcp light/dark theme control, layout, and syntax palettes.
It imports Hugo Book v0.14.0 and supplies `BookTheme = "auto"`.
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
Remove local copies of the six shared theme files during migration; Hugo gives local files precedence over module files.
The [example site](examples/site/) demonstrates the import with a local replacement for development.
The module owns the two `docs/inject` partials; a consumer adding content at those same hooks must deliberately compose or override them.

## Development and provenance

See [CONTRIBUTING.md](CONTRIBUTING.md) for commands and the PR workflow.
The sources were extracted from the flink-gcp projects listed in the [inventory](docs/inventory.md).
This repository uses [Apache License 2.0](LICENSE); the theme remains an external dependency with its own license.

# ADR-0001: Share development assets through explicit consumer updates

Status: Accepted

## Context

flink-connector-gcp and flink-datastream-protobuf share development procedures and documentation design.
The planned `flink-sql-launcher` Java application will need the same facilities.
The projects need one maintained source while retaining their own compatibility policies, build commands, and release cadence.
The maintainer excludes Git submodules and prefers a small just recipe for installing selected skills.

## Decision

Maintain canonical workflow skills, a PR template, and a Hugo design module in `flink-gcp/flink-gcp-dev-tools`.
Consumers explicitly select the shared version and review its changes through their normal PR workflow.
Keep the initial shared units limited to the sources identified in the inventory.

Install the four workflow skill directories as tracked copies at a full upstream commit SHA.
Keep the installation recipe small and visible in the consumer, with an explicit revision argument rather than automatic updates.
The consumer records the pin in its own justfile and commits the copied content, allowing offline use and direct review of skill changes.
Local repository guidance supplies repository identity, verification commands, supported versions and available tool bindings.
The shared skill text owns the workflow rules, including their detailed procedures and exceptions.

Distribute the visual design as a Hugo module because the existing connector site already uses Hugo modules for Hugo Book.
Each site retains its content, URL configuration, compiled examples, API documentation, and deployment workflow.
The module also owns the Hugo Book search readiness fix so consumers do not maintain separate copies of the upstream asset.
Copy the small PR template when initializing or deliberately updating a consumer.

Keep dotagents and the skills CLI as alternatives if broader agent configuration management becomes necessary.
Evaluate Copier when preserving project customizations across template updates becomes a concrete requirement.
The initial extraction requires none of those tools and introduces no Java runtime dependency.

## Adoption

Land the shared source first, then update each consumer to a commit available from the shared repository's main history.
The existing copies remain usable until that consumer's migration is reviewed and merged.
The protobuf documentation site can import this module when its Pages implementation is added.
Record consumer-specific differences before replacing its workflow guidance.

## Consequences

Shared changes reach consumers through explicit update PRs rather than immediately changing every project's workflow.
Tracked skill copies duplicate storage but remove a network prerequisite from ordinary agent use after cloning.
The recipe and pin are visible maintenance points; adding dependency resolution, broad configuration generation, or automatic policy merging would require reassessing the distribution choice.

## Correction: restore the original workflow semantics

The initial compact skills did not preserve the full connector workflow.
Restore the four procedures from connector commit `02c4bd594d2b774cc24b0c0194c1834dd5032120`, including decision conditions, examples, historical rationale and completion checklists.
Keep each procedure in its existing SKILL.md; this correction does not redesign or summarize it.
The inventory maps every original section and explains the portability substitutions.

The original unavailable-reviewer exception is part of the shared workflow: record the concrete reason when the round cannot run; that recorded exception may proceed to Ready once other required checks and self-reviews are complete.
The original missing-plugin skip reason remains valid; a launched but uncollected review is incomplete.
The two self-review rounds, inline records, current aggregate CI and maintainer merge remain required.
Align consumer entrypoints with these rules instead of distributing a compact skill plus a second locally maintained procedure.

## Amendment: share standard-library repository tools

Both consumers keep repository tools under `scripts/`, and several have counterparts in the other consumer ([#5](https://github.com/flink-gcp/flink-gcp-dev-tools/issues/5)).
The initial decision limited sharing to the skills, the PR template, and the Hugo module.
The [inventory](../inventory.md#repository-tools) compares each candidate and separates its common behavior from the consumer's bindings.

Share `scripts/central-portal.py`, the Central Portal staging-ID capture, publication, and drop tool.
Its code is identical in both consumers; only the provenance comments differ.
Its bindings are already outside it: each release workflow chooses the staging command and ID files and maps the credentials to the two environment variables the tool reads.
Both release workflows publish exactly two artifact lines, which matches the tool's two-ID `publish` command.

Install shared tools as tracked copies at a full upstream commit SHA, the same way as the workflow skills.
The installation recipe writes each selected file to the consumer's existing path, so the consumer's recipes, workflows, and tests keep calling it unchanged.
It refuses to overwrite an uncommitted edit or an untracked file at a managed path.
A committed local edit is replaced by the next sync and shows up in that update's diff, so a local fix does not survive unless it lands here.
Consumers sync the skills and the tools together from the one revision pin.
A behavior change to a shared tool lands here first and reaches each consumer in a reviewed update PR.

Shared tools import only the Python standard library and support Python 3.11 and later.
This repository tests them with Python 3.11 and with the newest Python a consumer pins.
Its `pyproject.toml` and `uv.lock` cover only this repository's tests; they are not distributed.
Each consumer keeps its own `pyproject.toml`, `uv.lock`, Python version, and test-only packages, and runs the installed copy with its usual interpreter.
The shared distribution therefore adds no dependency resolution to the consumers.
A shared tool that needs a third-party package would reopen this decision; inline script metadata run through `uv run --script` keeps such dependencies with the script and out of the consumer's lock, and should be weighed before packaging the tools.

This repository owns the behavioral tests of each shared tool.
Each consumer keeps the tests of its own bindings, such as release workflow ordering, the staging commands, and the credential mapping.
A consumer may keep its copy of a shared tool's behavioral tests until its migration PR removes or adapts them.

The other candidates stay with their consumers:

- `scripts/docs-site.py` shares its planning, assembly, and navigation structure, but the copies differ in version policy and source preparation.
  The protobuf copy publishes 0.x pre-releases as development milestones until its first stable release and adds link and source checks; the connector copy adapts the v1.0.0 homepage and sets the Maven version of each tagged source before building.
  Each also runs different validation recipes and passes different Hugo parameters.
  Sharing it now would require a configuration surface for those policies, and the Consequences above already name broad configuration generation as a reason to reassess the distribution choice.
  Reassess once both consumers use the same version kinds and a single consumer-defined build recipe.
- The connector's `scripts/rehearse-release.py` and the protobuf `scripts/release-artifacts.py` both rehearse Central bundles without uploading them, but they inspect different artifact sets with different rules and have no common implementation.
- The importlib loader in each `scripts/tests/conftest.py` is a few lines of test code; the connector's file also defines that repository's own fixtures.

## Amendment: propose each release to the consumers from a bot

Each update PR was written by hand, so small shared fixes did not reach the consumers ([#17](https://github.com/flink-gcp/flink-gcp-dev-tools/issues/17)).
The README correction in [#16](https://github.com/flink-gcp/flink-gcp-dev-tools/pull/16), for example, was judged not worth a PR in each consumer.

A release tag `vX.Y.Z` on a commit from `main` is the maintainer's decision to distribute that commit.
The `Update consumers` workflow then proposes the latest release to each consumer in its matrix, authenticated as the organization's `flink-gcp-bot` GitHub App.
For each consumer it sets `dev_tools_revision` to that release's full commit SHA, replaces `dev-tools.just` with that commit's `examples/dev-tools.just`, runs `just dev-tools-sync`, and moves the Hugo module in `docs/` to the same commit with `hugo mod get` and `hugo mod tidy`.
It commits the result to the branch `dev-tools/update` and opens or updates a Draft PR whose body fills the consumer's WHAT and WHY sections.
The body links the shared changes since the previous pin and lists the consumer's lines that still name the previous commit, because guidance that states the current pin needs a manual edit.
It leaves out a line that names the commit only in `/blob/` or `/tree/` permalinks, because a permalink cites a file as it read at that commit and stays true after the update.
Only a path, fragment, query, whitespace, the end of the line, or a closing bracket, quote or Markdown delimiter ends such a permalink; a link whose SHA is followed by anything else, such as the `-` of a branch named `<sha>-fix`, is still listed, so an unusual link costs the reader a line instead of hiding one.
A branch whose name continues the SHA with one of those closing characters is treated as a permalink, which no realistic link does.
Commits on `main` that are not worth an update wait for the next tag, so the bot never proposes an untagged commit.

The bot prepares the PR that a maintainer would otherwise write; it never marks the PR Ready or merges it.
Consumers therefore still select the shared version explicitly, because a pin moves only when a maintainer merges that reviewed PR.
The pin stays a full commit SHA, and the consumer's installation recipe is unchanged.
The amendment adds no dependency resolution, configuration generation, or policy merging to the consumers, so it does not trigger the reassessment named in the Consequences.

### Behavior of the update workflow

Every release run proposes the latest release: the highest `vX.Y.Z` tag on `main`, whichever tag or manual run started it.
Release runs go one at a time, so no run decides from a state that another run is changing.
GitHub replaces a pending run with the next one, which resolves the latest release when it starts, so a replaced or late run can neither hold back nor undo a newer release.
A run whose prepared update is for an older release than the latest, because a tag arrived in between, leaves the proposal to the run that tag started.

The workflow keeps one update branch and at most one open update PR per consumer.
It refuses a release that does not descend from the consumer's current pin, and it refuses to replace an update branch that carries a commit authored or committed by anyone other than the bot, whether or not a PR is open from it.
A newer release returns a Ready PR to Draft before it force-pushes the branch, because the new content has not been reviewed, and then retitles the PR.
It reads the PR's state again just before the push and just after it, so that a PR a maintainer marked Ready during the run also returns to Draft.
If that conversion after the push fails, the run fails, and the maintainer returns the PR to Draft by hand: a rerun cannot tell that Ready from one a maintainer set after reviewing the new content.
A rerun for the release that the PR already proposes pushes nothing and edits the PR's text only if it differs, which repairs a run that pushed but failed to edit.
PRs from forks are ignored even when their branch has the same name.
The push leases on the branch head that the run read, so it fails instead of replacing a branch that changed in the meantime.

A change that requires consumer migration can fail the update, for example when the copied recipe no longer provides what the consumer's `dev-tools-sync` calls; the maintainer then migrates that consumer by hand.
On a pull request that changes what reaches the consumers, the workflow prepares the update against the PR head as a dry run.
The dry run reads only the consumer's pin, so the consumers' own update branches cannot fail it.
It writes the PR body and the start of the patch to the job summary, and uploads the whole patch as the job's artifact.

### Review of the bot's PRs

The shared diff in a bot PR has already passed both self-review rounds and the independent review in this repository.
The consumer review asks a different question: what the update changes for that repository, and whether the PR description is true there.
A bot PR that contains only the workflow's commit therefore needs `self-review-round-two` and the consumer's current aggregate CI before Ready; round one and the independent review are not repeated.
A maintainer commit on the update branch, such as a migration or an edit to guidance that names the pin, returns the PR to the full review flow, because that commit has not been reviewed anywhere.
Each consumer records this rule in its own guidance.

### Permissions and trust

`flink-gcp-bot` is installed on each consumer with contents and pull-requests write.
This repository keeps the App ID in the `BOT_APP_ID` variable and its private key in the `BOT_APP_PRIVATE_KEY` secret.
The workflow mints a token for one consumer at a time, with only those two permissions.
The workflow also names the App's bot user and its numeric user ID, which attribute the bot's commits; recreating the App changes both.

The update runs the consumer's `dev-tools-sync` recipe from the consumer's default branch, which that consumer's own review already governs.
That recipe runs in a separate prepare job with this repository's read-only `GITHUB_TOKEN` and no secrets.
The propose job, which holds the App token, runs on a fresh runner where no consumer code has run: it decides again from GitHub's state, applies the prepared patch, checks again that it changes only the managed paths and names the tagged commit in both pins, and pushes.
A compromised consumer branch can therefore shape the proposed patch and PR text within those checks, which its maintainers review, but cannot obtain the token.

A pull request opened with an App token, unlike one opened with `GITHUB_TOKEN`, starts the consumer's `pull_request` workflows, so the bot's PR runs the consumer's required checks.

### Versions and tags

Releases start at `v0.1.0`, because two consumers already use this repository while its interfaces still change.
While on 0.x, a change that requires consumer migration, such as a recipe name, the pin format, or the Hugo module's mounts, bumps the minor version.
Every other change, such as a documentation fix or skill wording, bumps the patch version.
Consider `v1.0.0` once the update workflow has proposed releases to the consumers and those interfaces have settled.
Staying on 0.x until then also avoids the `/v2` module path that Go would require for a semantic `hugo/` tag at major version 2 or later.

Only `vX.Y.Z` tags are created.
Go recognizes only `hugo/`-prefixed tags as versions of the module in `hugo/`, so the consumers keep the commit pseudo-version in `docs/go.mod`, which needs no second tag.
Consumers pin full SHAs, so the version tells readers about compatibility and does not change resolution.
Each tag comes with a GitHub release and generated notes.

The consumer list is the workflow's matrix, and the [inventory](../inventory.md#release-updates) lists what a consumer provides to join it.

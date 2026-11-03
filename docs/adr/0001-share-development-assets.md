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
The `install-scripts` recipe writes each selected file to the consumer's existing path, so the consumer's recipes, workflows, and tests keep calling it unchanged.
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

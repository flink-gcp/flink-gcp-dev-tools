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

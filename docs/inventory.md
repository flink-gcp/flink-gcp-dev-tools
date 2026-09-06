# Shared asset inventory

The initial extraction used flink-connector-gcp commit `90a35b9322b703247e2d501a18ec16f676f68bd8` and flink-datastream-protobuf merge commit `1fa0b876d935aca36b77d8f79e3371e6e47693e8`.
The Codex metadata was added from the later connector commit listed in the inventory below.
The source repositories use Apache-2.0 with `The flink-gcp authors` as the project copyright holder.

| Shared source | Origin | Consumer responsibility |
| --- | --- | --- |
| Four `skills/*/SKILL.md` procedures | Connector `.agents/skills/` at `02c4bd594d2b774cc24b0c0194c1834dd5032120` | Repository identity, verification commands, supported versions and available reviewer tools |
| Four `skills/*/agents/openai.yaml` metadata files | Connector `.agents/skills/` at `43d6980cdb25d641155b909a63dcfb15591eb14e` | Preserve the shared names and invocation prompts when synchronizing |
| `templates/PULL_REQUEST_TEMPLATE.md` | Identical WHAT/WHY template in both projects | Fill both sections and include relevant validation |
| `hugo/assets/_custom.scss` | Connector `docs/assets/` | Keep the supported `BookTheme` and highlighting configuration |
| `hugo/assets/_chroma-light.scss` and `_chroma-dark.scss` | Connector Hugo-generated palettes | Regenerate in the shared source with `just docs-chroma` |
| `hugo/assets/theme-toggle.js` | Connector `docs/assets/` | Integrate with the module's theme control |
| Two `hugo/layouts/_partials/docs/inject/` partials | Connector documentation layout | Deliberate composition if a site overrides these hooks |

The skill directories include Codex UI metadata so synchronization preserves the connector's required display names and invocation prompts.
The initial shared skills copied the compact procedures extracted for the protobuf library.
That extraction omitted operational detail from the connector's original skills and changed the default unavailable-reviewer policy.
The restoration uses the connector version named above, retaining its procedures, decision conditions, exceptions, concrete examples and historical evidence inside the four SKILL.md files.
Consumer-specific commands are bindings in the consumer's existing guidance; they do not replace shared workflow rules.
Both projects retain the distinct review rounds, a different authoring/review model for the independent round, inline records, and current CI requirements.

The planned `flink-sql-launcher` is another prospective consumer of these workflow skills and documentation assets.
Its SQL configuration model, command modes, packaging, and integration tests remain in that project.

The following components remain with their consumers:

- Maven parent usage, dependencies, API compatibility policy, packaging, and publication configuration.
- Connector-specific skills, module guidance, cloud test settings, and optional MCP configuration.
- Hugo content, source-snippet shortcodes and validators, versioned-site assembly, Javadoc generation, and Pages deployment.
- Tool pins needed by a particular repository's commands and workflow jobs.
- Repository identity, credentials, personal agent settings, and private memory.

The source theme assets retain their behavior; comments omit measurements tied to the original site's content and clarify visibility and loading behavior.
Hugo Book remains a pinned module dependency; its implementation is not copied into this repository.

## Restoration coverage

The source for every row below is the connector commit named in the procedure inventory.
Each original section remains in the same named skill and under the same heading.
There is no new summary layer or separate reference file carrying omitted procedure text.
The original skill names, selection descriptions, examples and completion checklists remain; the Apache-2.0 metadata and existing Codex UI metadata are retained.
A source-link preface distinguishes historical connector observations from current consumer instructions.
Review records use the user's required inline format with an empty review body and the review API comments array; historical incident descriptions retain their original meaning.
The approval step in the original flow diagrams does not request authorization again when the user has already supplied it.

| Skill | Original section retained | Adaptation within that section |
| --- | --- | --- |
| `push-pr-branch` | What goes wrong | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `push-pr-branch` | The procedure | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `push-pr-branch` | The gate, before every push | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `push-pr-branch` | Conflict-only refresh fast path | Full verification and uncovered compatibility-version checks use the consumer commands; the original `just verify-flink 1.20.4` example, every proof condition and comparison remain. |
| `push-pr-branch` | The fourth check, once the pull request exists | Issue templates and the GraphQL query use the current owner/repository; original connector incidents remain attributed examples. |
| `push-pr-branch` | Recovery, when the gate fails | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `push-pr-branch` | Why this is a skill and not a checker | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review` | What to review | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review` | The three lenses, kept apart | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review` | Verify before acting | Dependency inspection uses the consumer toolchain; the original Maven command remains an explicit example. |
| `self-review` | Act on it | Verification and mutation-batch applicability use the consumer check policy; the complete connector command list remains as the source example. |
| `self-review` | Record it | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review` | Done when | Checklist retained; mutation-batch applicability uses the consumer check policy, and other items retain their original conditions. |
| `self-review-round-two` | Step 1: extract the claims | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review-round-two` | Step 2: the outward lenses | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review-round-two` | Step 3: pay the deferred measurements | Supported versions come from the consumer compatibility policy; both connector Flink minors remain the original example. |
| `self-review-round-two` | Step 4: sweep the prose the diff did not touch | Rendered backing sources use the consumer location; the connector validation module remains the original example. |
| `self-review-round-two` | Scope | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review-round-two` | Record it | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `self-review-round-two` | Done when | Checklist retained; mutation-batch applicability uses the consumer check policy, and other items retain their original conditions. |
| `independent-review` | Prerequisite | The plugin is the original optional command adapter and its recorded skip reason remains; the author/reviewer pairing determines the independent route when the round runs. |
| `independent-review` | Run it | Original plugin commands and their failure explanations remain conditional on that adapter; other routes owe the same isolation and result-collection evidence. |
| `independent-review` | What its findings are, and are not | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `independent-review` | No small-change carve-out | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `independent-review` | When no second model is available | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `independent-review` | Record it | Procedure and conditions retained; source links and the shared inline-record convention apply where referenced. |
| `independent-review` | Done when | Plugin flags are conditional on that adapter; the identity, isolation, collection and review-loop requirements remain. |

The introductions and pre-section instructions are retained as well: review ordering, frozen base/head selection, separate lenses, and the source explanations of why each round exists.
Relative connector ADR references resolve to the original files at the frozen source commit, and numerical historical issue/PR references identify the connector repository.
These links preserve attribution; they do not require another checkout to execute the skills.
Commands that operate on a consumer repository resolve its identity and guide locally.

The unavailable-reviewer exception is restored: record why the round could not run, and the PR may still become Ready after its other required checks and self-reviews complete.
The original prerequisite's recorded skip reason for an unavailable plugin remains valid.
A running or uncollected review is incomplete and does not qualify.
An available reviewer who authored part of the change is not independent; the original alternative-model/human rule still applies.
Consumer updates must document this same default rather than keeping a connector-only override.

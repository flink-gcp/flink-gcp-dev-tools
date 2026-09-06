# Shared asset inventory

The initial extraction used flink-connector-gcp commit `90a35b9322b703247e2d501a18ec16f676f68bd8` and flink-datastream-protobuf merge commit `1fa0b876d935aca36b77d8f79e3371e6e47693e8`.
The Codex metadata was added from the later connector commit listed in the inventory below.
The source repositories use Apache-2.0 with `The flink-gcp authors` as the project copyright holder.

| Shared source | Origin | Consumer responsibility |
| --- | --- | --- |
| Four `skills/*/SKILL.md` procedures | Protobuf `.agents/skills/` | Verification commands, issue routing, and additional repository rules |
| Four `skills/*/agents/openai.yaml` metadata files | Connector `.agents/skills/` at `43d6980cdb25d641155b909a63dcfb15591eb14e` | Preserve the shared names and invocation prompts when synchronizing |
| `templates/PULL_REQUEST_TEMPLATE.md` | Identical WHAT/WHY template in both projects | Fill both sections and include relevant validation |
| `hugo/assets/_custom.scss` | Connector `docs/assets/` | Keep the supported `BookTheme` and highlighting configuration |
| `hugo/assets/_chroma-light.scss` and `_chroma-dark.scss` | Connector Hugo-generated palettes | Regenerate in the shared source with `just docs-chroma` |
| `hugo/assets/theme-toggle.js` | Connector `docs/assets/` | Integrate with the module's theme control |
| Two `hugo/layouts/_partials/docs/inject/` partials | Connector documentation layout | Deliberate composition if a site overrides these hooks |

The skill directories include Codex UI metadata so synchronization preserves the connector's required display names and invocation prompts.
The initial shared skills retain the compact procedures already extracted for the protobuf library.
The connector's longer skills also contain historical evidence and repository-specific commands; its migration must preserve applicable policy and route historical explanations to that repository's existing ADRs and references.
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

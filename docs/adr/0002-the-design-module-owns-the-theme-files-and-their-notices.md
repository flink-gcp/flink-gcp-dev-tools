# ADR-0002: The design module owns the theme files it publishes and their notices

Status: Accepted

## Context

Hugo Book reaches every consuming site through the `hugo` module, which imported it with its default mounts.
Those mounts publish the whole of Hugo Book's `static/` directory, including the KaTeX, Mermaid and asciinema-player bundles.
flink-connector-gcp ([#1985](https://github.com/flink-gcp/flink-connector-gcp/pull/1985), ADR-0164) and flink-datastream-protobuf ([#191](https://github.com/flink-gcp/flink-datastream-protobuf/pull/191), ADR-0002) each fixed this in their own site.
Each site ignores this module's imports, imports Hugo Book itself with restricted mounts, and adds a hidden site licenses page whose `hugo-book-version` shortcode guards the documented version.
The two guards differ only in the guide their error message names, the two pages apart from front matter only in "the connectors" versus "this library", and the two import blocks only in a comment's wording.
A Hugo Book change in this repository therefore required both copies of the notices and the guard to change, in two consumer pull requests ([#6](https://github.com/flink-gcp/flink-gcp-dev-tools/issues/6)).

## Decision

The module imports Hugo Book with the consumers' restricted mounts.
It mounts Hugo Book's `assets/`, `layouts/` and `i18n/`, and from `static/` only `favicon.png`, `favicon.svg` and `fuse.min.mjs`; `favicon.svg` is the web app manifest's icon.
It excludes the KaTeX, Mermaid and asciinema-player shortcodes and code-block hooks, so such a shortcode fails the build and such a code block renders as plain code.
No consuming page used those features, and their bundles carry no notice of their own: KaTeX's fonts are under the SIL Open Font License 1.1, and the Mermaid and asciinema-player bundles compile in third-party dependencies.

The module's `theme-notices` shortcode renders the notices for what those mounts publish: Hugo Book, modern-normalize, Material Symbols, Fuse.js and one copy of the Apache License 2.0.
The license texts are verbatim copies in `hugo/assets/dev-tools/notices/`.
A consuming site calls the shortcode as `{{% theme-notices %}}` from its own hidden site licenses page, which keeps the page title and the licence statement for the site's own sources.

The shortcode names the one Hugo Book version its notices document and fails the build when the site resolves another version.
It also fails on a `go.mod` replace, `HUGO_MODULE_REPLACEMENTS`, a workspace or a vendored copy, because a substitute cannot establish which notices apply.
It fails, too, when another module owns the Hugo Book import: the first import of a module decides its mounts, so a site importing Hugo Book before this module publishes the whole theme.
A consumer that requires a different Hugo Book version itself therefore fails the build until this module documents that version.

The notices cover what the site distributes directly: the theme and the components it ships as their own files or compiled styles, each checked against its own license.
They do not follow those components further, so code compiled inside one, output that a tool generates, and values a component borrows stay off the page.
Examples are the Lodash helpers inside Fuse.js, the Chroma styles Hugo generates the code palettes from, the scripts the JDK's javadoc bundles with a consumer's API reference, and the Nord colours in Hugo Book's dark theme; that trail has no natural end.

`tests/site/test_site_hugo_book.py` holds the restrictions, the notices and the guard against the example site and temporary copies of it, so consumers need not duplicate those tests.

## Updating Hugo Book

Compare Hugo Book's `assets/`, `layouts/`, `i18n/` and published static files between the two tags.
Update each affected notice from the upstream license at the new version, including the texts in `hugo/assets/dev-tools/notices/`, and only then change the version the shortcode names together with the `hugo/go.mod` pin.
Check that the new tag adds no static file or feature that the mounts would publish without a notice.
A third-party file that the module adds itself needs a notice too, which no check catches.

## Alternatives declined

- **Keep the import and notices in each consumer.** Declined: every Hugo Book update would need two identical consumer changes, and a consumer that missed one would publish files without their notices.
- **Publish the KaTeX, Mermaid and asciinema-player bundles with every notice they owe.** Declined for the reason the consumers recorded: the dependency versions compiled into each bundle are recoverable only from that project's lockfile at the bundled release, and the inventory would be re-derived on every theme update for features no page uses.
- **Ship the whole site licenses page from the module.** Declined: the page's licence statement for the site's own sources and its link to the consumer's license differ by site, and a content mount would fix the page's path in every consumer.

## Consequences

A consumer adopts this by updating its pin, removing `ignoreImports` and its own Hugo Book import, removing its `hugo-book-version` shortcode, and replacing the notice sections of its site licenses page with the shortcode.
Until then, its existing copies keep working: `ignoreImports` drops this module's Hugo Book import and its restricted mounts, and the shared shortcode and notice assets use names the consumers do not.
A Hugo Book update becomes one change in this repository, which consumers receive through their normal pin updates.

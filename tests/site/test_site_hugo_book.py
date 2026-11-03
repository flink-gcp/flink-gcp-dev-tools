# Copyright 2026 The flink-gcp authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The Hugo Book files a site publishes and the notices that cover them.

The first tests read the example site that `just docs` has built; the rest build a temporary copy
of the module and the example site, so that a probe page or a changed pin cannot affect the
checked-in sources.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest

from site_output import BASE_URL, EXAMPLE, OUTPUT, ROOT, built

MODULE = "github.com/flink-gcp/flink-gcp-dev-tools/hugo"
HUGO_BOOK = "github.com/alex-shpak/hugo-book"
# The version hugo/go.mod requires, in either form: a `require` line or a `require ( … )` block.
REQUIRED = next(iter(re.findall(
    r"^\s*(?:require\s+)?github\.com/alex-shpak/hugo-book\s+(v\S+)",
    (ROOT / "hugo" / "go.mod").read_text(),
    re.M,
)), None)


def hugo(*args, env=None):
    return subprocess.run(
        ["hugo", *args], capture_output=True, text=True, env={**os.environ, **(env or {})}
    )


def log(result):
    return result.stdout + result.stderr


def modules():
    """`hugo config mounts` prints one JSON object per module, not separated by commas."""
    result = hugo("config", "mounts", "--source", str(EXAMPLE))
    assert result.returncode == 0, result.stderr
    return json.loads("[" + re.sub(r"}\s*{", "},{", result.stdout) + "]")


def hugo_book_module():
    found = [entry for entry in modules() if entry["path"] == HUGO_BOOK]
    assert found, f"{HUGO_BOOK} is not among the example site's modules"
    return found[0]


def hugo_book_dir():
    return Path(hugo_book_module()["dir"])


def files(directory):
    return [path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()]


def text(html):
    plain = re.sub(r"<[^>]+>", "", html)
    for entity, character in [
        ("&lt;", "<"), ("&gt;", ">"), ("&#34;", '"'), ("&quot;", '"'),
        ("&#39;", "'"), ("&rsquo;", "'"), ("&amp;", "&"),
    ]:
        plain = plain.replace(entity, character)
    return plain


def words(value):
    return " ".join(value.split())


class Site:
    """A temporary copy of the module and the example site, built into its own directory."""

    def __init__(self, directory):
        self.dir = directory
        self.site = directory / "examples" / "site"
        self.public = directory / "public"
        shutil.copytree(ROOT / "hugo", directory / "hugo")
        shutil.copytree(EXAMPLE, self.site, ignore=lambda parent, names: [
            name for name in names
            if Path(parent) == EXAMPLE and name in ("public", "resources", ".hugo_build.lock")
        ])

    def build(self, env=None):
        return hugo("--source", str(self.site), "--destination", str(self.public),
                    "--panicOnWarning", env=env)

    def probe(self, body):
        (self.site / "content" / "docs" / "probe.md").write_text(f"---\ntitle: Probe\n---\n{body}\n")


@pytest.fixture
def site(tmp_path):
    return Site(tmp_path)


def test_the_module_imports_hugo_book_with_only_the_assets_layouts_i18n_and_static_mounts():
    theme = hugo_book_module()
    assert theme["owner"] == MODULE, theme
    assert [mount["source"] for mount in theme["mounts"]] == ["assets", "layouts", "i18n", "static"]


def test_the_site_publishes_only_the_favicons_and_the_search_module_from_hugo_book_static_files():
    published = set(files(OUTPUT))
    theme = files(hugo_book_dir() / "static")
    assert sorted(name for name in theme if name in published) == [
        "favicon.png", "favicon.svg", "fuse.min.mjs",
    ]
    assert any(name.startswith("katex/") for name in theme), "the pinned theme no longer ships KaTeX"


def test_every_local_file_and_anchor_a_built_page_or_the_manifest_names_exists():
    references = [
        (name, text(url))
        for name in files(OUTPUT) if name.endswith(".html")
        for url in re.findall(r'\b(?:href|src)="([^"]+)"', (OUTPUT / name).read_text())
    ]
    manifest = json.loads((OUTPUT / "manifest.json").read_text())
    references += [("manifest.json", icon["src"]) for icon in manifest["icons"]]
    checked = 0
    for referrer, url in references:
        # Resolve relative, root-relative and absolute URLs alike against the referring file.
        target = urljoin(BASE_URL + referrer, url)
        if not target.startswith(BASE_URL):
            continue
        parts = urlsplit(target)
        page = built(parts.path, referrer)
        if parts.fragment:
            assert f'id="{parts.fragment}"' in page.read_text(), f"{referrer} links to the missing anchor {url}"
        checked += 1
    assert checked


def test_the_site_licenses_carry_the_notices_for_the_resolved_hugo_book_files():
    assert REQUIRED, "hugo/go.mod requires no Hugo Book version"
    theme = hugo_book_dir()
    html = (OUTPUT / "docs" / "licenses" / "index.html").read_text()
    assert f"The site's theme is Hugo Book {REQUIRED}," in text(html), text(html)

    sections = []
    for section in html.split('<h2 id="')[1:]:
        title, body = re.match(r'^[^"]+">([\s\S]*?)</h2>([\s\S]*)$', section).groups()
        code = re.search(r"<pre\b[^>]*><code\b[^>]*>([\s\S]*?)</code></pre>", body)
        sections.append({
            "title": re.sub(r"#$", "", text(title)).strip(),
            "body": text(body),
            "code": text(code[1]) if code else None,
        })
    license = (theme / "LICENSE").read_text()
    mit = words(license[license.index("Permission is hereby granted"):])
    normalize = re.search(r"modern-normalize (v\S+) \| MIT License", (theme / "assets" / "normalize.css").read_text())
    fuse = re.search(r"Fuse\.js (v\S+)[\s\S]*?Copyright \(c\) (\d+ [^(]+?) \(",
                     (theme / "static" / "fuse.min.mjs").read_text())
    assert normalize and fuse, "the theme no longer names its modern-normalize or Fuse.js version"

    assert [section["title"] for section in sections] == [
        "Hugo Book", f"modern-normalize {normalize[1]}", "Material Symbols", f"Fuse.js {fuse[1]}",
        "Apache License, Version 2.0",
    ]
    hugo_book, modern_normalize, symbols, fuse_notice, apache = sections
    assert hugo_book["code"].strip() == license.strip()
    code = modern_normalize["code"]
    assert code.startswith("MIT License\n\nCopyright (c) Sindre Sorhus <sindresorhus@gmail.com>"), code
    assert words(code[code.index("Permission"):]) == mit
    assert "Material Symbols, distributed under the Apache License, Version 2.0" in symbols["body"], symbols["body"]
    assert (f"Fuse.js is Copyright (c) {fuse[2]} and is distributed under the Apache License"
            in fuse_notice["body"]), fuse_notice["body"]
    assert apache["code"].strip() == (ROOT / "LICENSE").read_text().strip()


@pytest.mark.parametrize("shortcode", ["katex", "mermaid", "asciinema"])
def test_an_excluded_shortcode_fails_the_build(site, shortcode):
    site.probe(f"{{{{< {shortcode} >}}}}")
    result = site.build()
    assert result.returncode != 0, log(result)
    assert f'template for shortcode "{shortcode}" not found' in log(result), log(result)


@pytest.mark.parametrize("language, source, bundle", [
    pytest.param("mermaid", "graph TD; A-->B", "mermaid.min.js", id="mermaid"),
    pytest.param("katex", "x^2 + y^2", "katex/", id="katex"),
])
def test_a_code_block_of_an_excluded_feature_renders_as_code_without_its_bundle(site, language, source, bundle):
    site.probe(f"```{language}\n{source}\n```")
    result = site.build()
    assert result.returncode == 0, log(result)
    page = (site.public / "docs" / "probe" / "index.html").read_text()
    code = re.search(r'<pre\b[^>]*><code class="language-([^"]+)" data-lang="[^"]+">([\s\S]*?)</code></pre>', page)
    assert code and (code[1], text(code[2])) == (language, source), "the block is not plain code"
    assert bundle not in page, f"the page links {bundle}"


def test_the_guard_rejects_notices_that_document_another_hugo_book_version(site):
    shortcode = site.dir / "hugo" / "layouts" / "_shortcodes" / "theme-notices.html"
    source = shortcode.read_text()
    documented = f'$hugoBook := "{REQUIRED}"'
    assert documented in source, f"theme-notices does not document the {REQUIRED} that hugo/go.mod requires"
    shortcode.write_text(source.replace(documented, '$hugoBook := "v0.0.0"'))
    result = site.build()
    assert result.returncode != 0, log(result)
    assert f'the theme notices document Hugo Book "v0.0.0", but the site resolves "{REQUIRED}"' in log(result), log(result)


def test_the_guard_rejects_a_site_that_imports_hugo_book_before_the_module(site):
    config = site.site / "hugo.toml"
    source = config.read_text()
    assert "[module]\n" in source, "the example site's hugo.toml has no [module] table to prepend an import to"
    config.write_text(source.replace(
        "[module]\n", f'[module]\n  [[module.imports]]\n    path = "{HUGO_BOOK}"\n', 1))
    result = site.build()
    assert result.returncode != 0, log(result)
    assert re.search(r'Hugo Book is imported by "[^"]+" rather than', log(result)), log(result)


def test_the_guard_rejects_a_go_mod_replacement_of_hugo_book(site):
    with (site.site / "go.mod").open("a") as go_mod:
        go_mod.write(f"\nreplace {HUGO_BOOK} => {hugo_book_dir()}\n")
    result = site.build()
    assert result.returncode != 0, log(result)
    assert "Hugo Book is replaced by" in log(result), log(result)


def test_the_guard_rejects_a_hugo_module_replacements_replacement_of_hugo_book(site):
    result = site.build(env={"HUGO_MODULE_REPLACEMENTS": f"{HUGO_BOOK} -> {hugo_book_dir()}"})
    assert result.returncode != 0, log(result)
    assert "Hugo Book does not resolve to a module version" in log(result), log(result)


def test_the_guard_rejects_a_vendored_hugo_book(site):
    vendor = hugo("mod", "vendor", "--source", str(site.site))
    assert vendor.returncode == 0, log(vendor)
    result = site.build()
    assert result.returncode != 0, log(result)
    assert "Hugo Book is vendored" in log(result), log(result)

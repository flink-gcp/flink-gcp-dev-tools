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

"""Check what the built search module references; nothing here executes JavaScript.

These checks cannot show the module's runtime order, such as searching the latest input once the
index arrives, so a change to hugo/assets/search.js needs a manual check in a browser.
"""

import base64
import hashlib
import html
import json
import re

from site_output import HTML, PREFIX, built


def attributes(tag: str) -> dict[str, str]:
    """The tag's double-quoted attributes, decoded as a browser would read them."""
    # Hugo escapes attribute values, so a "+" in a base64 digest appears in the page as "&#43;".
    return {name: html.unescape(value) for name, value in re.findall(r'(\w+)="([^"]*)"', tag)}


def search_module():
    tags = re.findall(r"<script\b[^>]*\bsrc=\"[^\"]*search[^\"/]*\.js\"[^>]*>", HTML)
    assert len(tags) == 1, tags
    found = attributes(tags[0])
    assert found.get("type") == "module", tags[0]
    return built(found["src"]), found.get("integrity")


def test_attribute_values_are_read_with_character_references_decoded():
    # Whether the built module's digest contains a "+", which Hugo escapes, depends on the site's
    # content, so the integrity test alone would cover the escaped form only by chance.
    # Hugo leaves "/" as it is, but a template change could escape it like any other character.
    tag = '<script integrity="sha256-t7tGBj7&#43;IMPCjU&#43;58oYz&#x2F;IrrvaRU&#47;JlHmQqe7CM17V8=">'
    assert attributes(tag) == {"integrity": "sha256-t7tGBj7+IMPCjU+58oYz/IrrvaRU/JlHmQqe7CM17V8="}


def test_the_page_loads_the_search_module_it_built_with_a_matching_integrity_hash():
    script, integrity = search_module()
    digest = base64.b64encode(hashlib.sha256(script.read_bytes()).digest()).decode()
    assert integrity == f"sha256-{digest}"


def test_the_search_module_imports_fuse_under_the_consumer_url_prefix():
    source = search_module()[0].read_text()
    imports = re.findall(r"""\bimport\s*\w+\s*from\s*["']([^"']+)["']""", source)
    assert imports == [f"{PREFIX}fuse.min.mjs"]
    # The module imports Fuse as the default export, which a non-module build would not provide.
    assert re.search(r"\bexport\s*\{[^}]*\bas default\b", built(imports[0]).read_text())


def test_the_search_module_fetches_an_index_of_pages_under_the_consumer_url_prefix():
    source = search_module()[0].read_text()
    urls = re.findall(r"""["'](/[^"']*search-data[^"']*\.json)["']""", source)
    assert len(urls) == 1, urls
    pages = json.loads(built(urls[0]).read_text())
    assert pages
    for page in pages:
        assert page["href"].startswith(PREFIX), page
        assert page["title"], page
        # The module searches both fields; see indexConfig.keys in hugo/assets/search.js.
        assert "content" in page, page

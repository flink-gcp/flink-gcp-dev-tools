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

import re

from site_output import HTML, built


def test_rendered_code_uses_css_classes_so_the_shared_palettes_can_follow_the_theme():
    assert re.search(r'<pre\b[^>]*\bclass="chroma"', HTML)
    assert not re.search(r"<pre\b[^>]*\bstyle=", HTML)


def test_the_built_page_loads_the_shared_stylesheet_under_the_consumer_url_prefix():
    match = re.search(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"', HTML)
    assert match, HTML
    css = built(match[1]).read_text()
    assert re.search(r"\.book-theme-toggle", css)
    assert re.search(r"""data-theme[=\s"']+light""", css)
    assert re.search(r"""data-theme[=\s"']+dark""", css)


def test_the_built_page_contains_one_theme_control_and_initializes_it_in_the_head():
    assert len(re.findall(r'<button\b[^>]*class="book-theme-toggle"', HTML)) == 1
    head = HTML[HTML.index("<head>"):HTML.index("</head>")]
    assert re.search(r"book\.theme", head)

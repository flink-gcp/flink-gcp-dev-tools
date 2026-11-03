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

"""The example site's build output, which `just docs` writes before running these tests."""

from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "site"
OUTPUT = EXAMPLE / "public"
HTML = (OUTPUT / "index.html").read_text()
# The example site's baseURL, whose path stands in for a consumer's URL prefix.
BASE_URL = "https://example.invalid/library/"
PREFIX = urlsplit(BASE_URL).path


def built(url: str, referrer: str = "the test") -> Path:
    """The published file for a URL under PREFIX; a URL ending in a slash names its index.html."""
    assert url.startswith(PREFIX), url
    path = OUTPUT / url.removeprefix(PREFIX)
    if url.endswith("/"):
        path = path / "index.html"
    assert path.is_file(), f"{referrer} names {url}, which the site does not publish"
    return path

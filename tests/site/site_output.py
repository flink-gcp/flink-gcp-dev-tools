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

OUTPUT = Path(__file__).resolve().parents[2] / "examples" / "site" / "public"
HTML = (OUTPUT / "index.html").read_text()
# The example site's baseURL path, which stands in for a consumer's URL prefix.
PREFIX = "/library/"


def built(url: str) -> Path:
    assert url.startswith(PREFIX), url
    path = OUTPUT / url.removeprefix(PREFIX)
    assert path.is_file(), url
    return path

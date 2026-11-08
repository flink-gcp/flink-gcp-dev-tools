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

set shell := ["bash", "-euo", "pipefail", "-c"]

# Keep test runs from writing bytecode beside the shared tools and the tests.
export PYTHONDONTWRITEBYTECODE := "1"
# The newest Python a consumer pins; mise.toml also provides the lowest supported one.
newest_python := "3.14"

default:
    @just --list

test: test-install test-scripts test-workflow

# The installation tests exercise the recipe under Bash, so one Python is enough to drive them.
test-install:
    uv run --locked --python {{ newest_python }} pytest tests/install

# The workflow script is Bash, so one Python is enough to drive its tests with a fake GitHub CLI, just and Hugo.
test-workflow:
    uv run --locked --python {{ newest_python }} pytest tests/workflow

# Consumers run the shared tools with their own Python, so test the newest one they pin and the lowest supported.
# The second run uses a temporary environment so that it does not rebuild .venv for another Python.
test-scripts:
    uv run --locked --python {{ newest_python }} pytest scripts/tests
    uv run --locked --isolated --python 3.11 pytest scripts/tests

# The Hugo Book tests build temporary copies of the site, so they need the pinned Hugo and Go too.
docs:
    cd examples/site && mise x hugo-extended go -- hugo --environment production --panicOnWarning --cleanDestinationDir
    mise x hugo-extended go -- uv run --locked --python {{ newest_python }} pytest tests/site

docs-chroma:
    cd hugo && mise x hugo-extended -- hugo gen chromastyles --style=github > assets/_chroma-light.scss
    cd hugo && mise x hugo-extended -- hugo gen chromastyles --style=github-dark > assets/_chroma-dark.scss

# Check the installation script the way a consumer's lint extracts it from the recipe.
lint:
    mise x actionlint shellcheck -- actionlint
    just --justfile examples/dev-tools.just --show install-dev-tools | sed -n '/^[[:space:]]*#!/,$p' | sed 's/^    //' | mise x shellcheck -- shellcheck -
    mise x shellcheck -- shellcheck .github/scripts/*.sh
    mise x rumdl -- rumdl check .

pin-actions:
    mise x pinact -- pinact run

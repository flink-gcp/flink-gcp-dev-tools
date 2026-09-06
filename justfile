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

default:
    @just --list

test:
    node --test tests/*.test.mjs

docs:
    cd examples/site && mise x hugo-extended go -- hugo --environment production --panicOnWarning
    node --test tests/site/*.test.mjs

docs-chroma:
    cd hugo && mise x hugo-extended -- hugo gen chromastyles --style=github > assets/_chroma-light.scss
    cd hugo && mise x hugo-extended -- hugo gen chromastyles --style=github-dark > assets/_chroma-dark.scss

lint:
    mise x actionlint shellcheck -- actionlint
    mise x npm:markdownlint-cli2 -- markdownlint-cli2

pin-actions:
    mise x pinact -- pinact run

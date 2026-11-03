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

"""Import every shared Python tool without site-packages, where the test-only packages live.

Consumers install these files into their own environments, so the tools may not depend on
any package that this repository's test environment happens to provide.
"""

import ast
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
TOOLS = sorted(SCRIPTS.glob("*.py"))
LOAD = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("tool", sys.argv[1])
spec.loader.exec_module(importlib.util.module_from_spec(spec))
"""


def test_finds_the_tools():
    assert TOOLS


@pytest.mark.parametrize("tool", TOOLS, ids=lambda tool: tool.name)
def test_tools_import_only_the_standard_library(tool):
    # -I ignores PYTHONDONTWRITEBYTECODE, so -B keeps the import from writing bytecode.
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", LOAD, str(tool)],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("tool", TOOLS, ids=lambda tool: tool.name)
def test_tools_name_only_standard_library_modules(tool):
    # Loading the module misses imports inside functions or under the __main__ guard.
    names = set()
    for node in ast.walk(ast.parse(tool.read_text(), str(tool))):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            names.add(node.module.split(".")[0])
    assert names
    assert names <= sys.stdlib_module_names | {"__future__"}

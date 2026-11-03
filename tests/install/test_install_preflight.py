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

"""Scenarios that the installation handles the same way for each unit."""

import os
from pathlib import Path
import shutil

import pytest

from install_fixture import OTHER_REVISION, Consumer, tarball_request, write_executable

# For each unit, one managed item as the recipe names it, and one file in it relative to the consumer and to the archive.
UNITS = {
    "skills": (".agents/skills/self-review", Path(".agents/skills/self-review/SKILL.md"),
               Path("skills/self-review/SKILL.md")),
    "scripts": ("scripts/central-portal.py", Path("scripts/central-portal.py"), Path("scripts/central-portal.py")),
}

FAKE_GIT = """\
#!/usr/bin/env python3
import os, subprocess, sys
if sys.argv[1:2] == [{subcommand!r}] and sys.argv[-1] == {item!r}:
    sys.exit({status})
env = dict(os.environ, PATH=os.environ["FIXTURE_BASE_PATH"])
sys.exit(subprocess.run(["git", *sys.argv[1:]], env=env).returncode)
"""


def failing_git(consumer, subcommand, status):
    """Install a Git that fails one subcommand for the unit's item and returns the environment it needs."""
    write_executable(consumer.bin / "git", FAKE_GIT.format(subcommand=subcommand, status=status, item=consumer.item))
    return {"FIXTURE_BASE_PATH": os.environ["PATH"]}


@pytest.fixture(params=UNITS)
def consumer(request, tmp_path):
    consumer = Consumer(tmp_path)
    consumer.item, managed, shared = UNITS[request.param]
    consumer.managed = consumer.project / managed
    consumer.shared = consumer.source / shared
    return consumer


# A branch or tag moves, and an abbreviated or padded SHA is not the pinned commit the consumer reviewed.
@pytest.mark.parametrize("ref", ["main", "v1.0.0", "a" * 7, "a" * 39, "a" * 41, "a" * 40 + "\n"],
                         ids=["branch", "tag", "short-sha", "one-short", "one-long", "trailing-newline"])
def test_rejects_anything_but_a_full_commit_sha_before_accessing_github(consumer, ref):
    result = consumer.install(ref)
    assert result.returncode != 0
    assert "full commit SHA" in result.stderr
    assert not consumer.request.exists()


def test_rejects_installation_from_a_subdirectory_before_downloading(consumer):
    subdirectory = consumer.project / "docs"
    subdirectory.mkdir()
    result = consumer.install(cwd=subdirectory)
    assert result.returncode != 0
    assert "repository root" in result.stderr
    assert not consumer.request.exists()
    assert not any(subdirectory.iterdir())


def test_rejects_installation_outside_a_git_checkout_before_downloading(consumer):
    shutil.rmtree(consumer.project / ".git")
    consumer.managed.parent.mkdir(parents=True)
    consumer.managed.write_text("Existing local copy.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert not consumer.request.exists()
    assert consumer.managed.read_text() == "Existing local copy.\n"


# The fixture runs every installation with the system Bash.
def test_repeating_installation_with_system_bash_before_committing_is_idempotent(consumer):
    assert consumer.install().returncode == 0
    result = consumer.install()
    assert result.returncode == 0, result.stderr
    assert "Installed workflow skills and shared tools" in result.stdout
    assert "unbound variable" not in result.stderr


def test_a_failed_download_preserves_installed_files(consumer):
    assert consumer.install().returncode == 0
    before = consumer.managed.read_bytes()
    assert consumer.install(env={"FIXTURE_DOWNLOAD_FAIL": "1"}).returncode != 0
    assert consumer.managed.read_bytes() == before


def test_a_failed_git_status_preserves_the_installed_file(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    before = consumer.managed.read_bytes()
    consumer.shared.write_text("Upstream change.\n")
    consumer.pack()
    result = consumer.install(OTHER_REVISION, env=failing_git(consumer, "status", 1))
    assert result.returncode != 0
    # The download proves that the earlier Git calls succeeded and the status check failed.
    assert consumer.requests()[-1] == tarball_request(OTHER_REVISION)
    assert consumer.managed.read_bytes() == before


# git diff exits with 1 for a difference, so any other failure must stop instead of replacing the file.
def test_a_failed_comparison_preserves_the_installed_file(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    before = consumer.managed.read_bytes()
    consumer.shared.write_text("Upstream change.\n")
    consumer.pack()
    result = consumer.install(OTHER_REVISION, env=failing_git(consumer, "diff", 2))
    assert result.returncode == 2
    assert consumer.requests()[-1] == tarball_request(OTHER_REVISION)
    assert consumer.managed.read_bytes() == before

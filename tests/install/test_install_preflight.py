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

"""Scenarios that both installation recipes handle the same way."""

import json
import os
from pathlib import Path
import shutil

import pytest

from install_fixture import OTHER_REVISION, Consumer, tarball_request, write_executable

# Each recipe, one file it manages relative to the consumer and to the archive, and its success message.
UNITS = {
    "install-skills": (Path(".agents/skills/self-review/SKILL.md"), Path("skills/self-review/SKILL.md"),
                       "Installed workflow skills"),
    "install-scripts": (Path("scripts/central-portal.py"), Path("scripts/central-portal.py"),
                        "Installed shared scripts"),
}

FAKE_GIT = """\
#!/usr/bin/env python3
import os, subprocess, sys
if sys.argv[1:2] == ["status"]:
    sys.exit(1)
env = dict(os.environ, PATH=os.environ["FIXTURE_BASE_PATH"])
sys.exit(subprocess.run(["git", *sys.argv[1:]], env=env).returncode)
"""


@pytest.fixture(params=UNITS)
def consumer(request, tmp_path):
    consumer = Consumer(tmp_path, request.param)
    managed, shared, consumer.installed_message = UNITS[request.param]
    consumer.managed = consumer.project / managed
    consumer.shared = consumer.source / shared
    return consumer


def test_rejects_a_moving_ref_before_accessing_github(consumer):
    result = consumer.install("main")
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


def test_repeating_installation_with_system_bash_before_committing_is_idempotent(consumer):
    (consumer.bin / "bash").symlink_to("/bin/bash")
    assert consumer.install().returncode == 0
    result = consumer.install()
    assert result.returncode == 0, result.stderr
    assert consumer.installed_message in result.stdout
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
    write_executable(consumer.bin / "git", FAKE_GIT)
    result = consumer.install(OTHER_REVISION, env={"FIXTURE_BASE_PATH": os.environ["PATH"]})
    assert result.returncode != 0
    # The download proves that the earlier Git calls succeeded and the status check failed.
    assert json.loads(consumer.request.read_text()) == tarball_request(OTHER_REVISION)
    assert consumer.managed.read_bytes() == before

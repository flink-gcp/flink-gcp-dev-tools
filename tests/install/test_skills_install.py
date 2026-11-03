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

import json
import shutil

import pytest

from install_fixture import OTHER_REVISION, REVISION, Consumer, executable, tarball_request

SKILLS = ["push-pr-branch", "self-review", "self-review-round-two", "independent-review"]


@pytest.fixture
def consumer(tmp_path):
    return Consumer(tmp_path, "install-skills")


def installed(consumer, *parts):
    return consumer.project.joinpath(".agents", "skills", *parts)


def shared(consumer, *parts):
    return consumer.source.joinpath("skills", *parts)


def test_installs_the_selected_revision_including_resources_and_preserves_unrelated_skills(consumer):
    resource = shared(consumer, "self-review", "references", "example.md")
    resource.parent.mkdir()
    resource.write_text("A shared resource.\n")
    unrelated = installed(consumer, "local", "SKILL.md")
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("Local guidance.\n")
    consumer.pack()
    result = consumer.install()
    assert result.returncode == 0, result.stderr
    assert json.loads(consumer.request.read_text()) == tarball_request()
    for skill in SKILLS:
        assert installed(consumer, skill, "SKILL.md").read_bytes() == shared(consumer, skill, "SKILL.md").read_bytes()
    assert installed(consumer, "self-review", "references", "example.md").read_text() == "A shared resource.\n"
    assert unrelated.read_text() == "Local guidance.\n"


def test_validates_all_requested_skills_before_replacing_any_installed_skill(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    before = installed(consumer, "push-pr-branch", "SKILL.md").read_bytes()
    shared(consumer, "push-pr-branch", "SKILL.md").write_text("Changed source.\n")
    shutil.rmtree(shared(consumer, "independent-review"))
    consumer.pack()
    result = consumer.install(OTHER_REVISION)
    assert result.returncode != 0
    assert "Invalid skill directory" in result.stderr
    assert installed(consumer, "push-pr-branch", "SKILL.md").read_bytes() == before


def test_preserves_tracked_edits_inside_a_managed_skill(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    edited = installed(consumer, "self-review", "SKILL.md")
    edited.write_text("Local changes.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert edited.read_text() == "Local changes.\n"


def test_preserves_untracked_resources_inside_a_managed_skill(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    resource = installed(consumer, "push-pr-branch", "local.md")
    resource.write_text("Local resource.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert resource.read_text() == "Local resource.\n"


def test_installs_a_resource_update_that_only_changes_the_executable_bit(consumer):
    resource = shared(consumer, "self-review", "example.sh")
    resource.write_text("#!/bin/sh\nexit 0\n")
    resource.chmod(0o644)
    consumer.pack()
    assert consumer.install().returncode == 0
    consumer.commit()
    resource.chmod(0o755)
    consumer.pack()
    result = consumer.install(OTHER_REVISION)
    assert result.returncode == 0, result.stderr
    assert executable(installed(consumer, "self-review", "example.sh"))


def test_upgrades_remove_obsolete_resources_and_a_prior_pin_restores_them(consumer):
    resource = shared(consumer, "self-review", "old.md")
    resource.write_text("Old version.\n")
    consumer.pack()
    assert consumer.install().returncode == 0
    consumer.commit()
    resource.unlink()
    consumer.pack()
    assert consumer.install(OTHER_REVISION).returncode == 0
    assert not installed(consumer, "self-review", "old.md").exists()
    consumer.commit()
    resource.write_text("Old version.\n")
    consumer.pack()
    result = consumer.install(REVISION)
    assert result.returncode == 0, result.stderr
    assert installed(consumer, "self-review", "old.md").read_text() == "Old version.\n"

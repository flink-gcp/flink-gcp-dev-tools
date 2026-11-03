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
import re
import shutil
import subprocess

import pytest

from install_fixture import OTHER_REVISION, REVISION, ROOT, Consumer, executable, tarball_request

SKILLS = ["push-pr-branch", "self-review", "self-review-round-two", "independent-review"]


@pytest.fixture
def consumer(tmp_path):
    return Consumer(tmp_path, "install-skills")


def installed(consumer, *parts):
    return consumer.project.joinpath(".agents", "skills", *parts)


def shared(consumer, *parts):
    return consumer.source.joinpath("skills", *parts)


def test_the_recipe_installs_every_shared_skill_and_nothing_else():
    recipe = (ROOT / "examples" / "dev-tools.just").read_text()
    lists = re.findall(r"^ {4}skills=\(([^)]*)\)$", recipe, re.MULTILINE)
    assert len(lists) == 1, "examples/dev-tools.just must keep the install-skills list on one skills=(...) line"
    # Every tracked skills/<name>/SKILL.md is a shared skill.
    tracked = subprocess.run(["git", "ls-files", "--", ":(glob)skills/*/SKILL.md"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    shared_skills = sorted(path.split("/")[1] for path in tracked)
    assert sorted(lists[0].split()) == shared_skills
    assert sorted(SKILLS) == shared_skills, "SKILLS must list every installed skill"


@pytest.mark.parametrize(("link", "target"), [(".agents", "elsewhere"), (".agents/skills", "../elsewhere")])
def test_rejects_a_symlinked_project_skill_directory_before_downloading(consumer, link, target):
    elsewhere = consumer.project / "elsewhere"
    elsewhere.mkdir()
    path = consumer.project / link
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)
    result = consumer.install()
    assert result.returncode != 0
    assert "must not be a symlink" in result.stderr
    assert not consumer.request.exists()
    assert not any(elsewhere.iterdir())


def test_rejects_a_symlinked_skill_in_the_archive(consumer):
    shutil.rmtree(shared(consumer, "self-review"))
    shared(consumer, "self-review").symlink_to("push-pr-branch")
    consumer.pack()
    result = consumer.install()
    assert result.returncode != 0
    assert "Invalid skill directory" in result.stderr
    assert not installed(consumer).exists()


def test_rejects_a_symlinked_managed_skill_directory(consumer):
    outside = consumer.project / "elsewhere" / "self-review"
    shutil.copytree(shared(consumer, "self-review"), outside)
    (outside / "SKILL.md").write_text("Outside the managed path.\n")
    installed(consumer).mkdir(parents=True)
    installed(consumer, "self-review").symlink_to("../../elsewhere/self-review")
    consumer.commit()
    result = consumer.install()
    assert result.returncode != 0
    assert "Invalid skill directory" in result.stderr
    assert installed(consumer, "self-review").is_symlink()
    assert (outside / "SKILL.md").read_text() == "Outside the managed path.\n"


def test_preserves_an_ignored_consumer_file_inside_a_managed_skill(consumer):
    (consumer.project / ".gitignore").write_text(".agents/skills/push-pr-branch/local.md\n")
    assert consumer.install().returncode == 0
    consumer.commit()
    ignored = installed(consumer, "push-pr-branch", "local.md")
    ignored.write_text("Ignored local notes.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert ignored.read_text() == "Ignored local notes.\n"


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

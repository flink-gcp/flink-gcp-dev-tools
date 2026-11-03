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
import subprocess

import pytest

from install_fixture import OTHER_REVISION, ROOT, Consumer, executable, tarball_request


@pytest.fixture
def consumer(tmp_path):
    return Consumer(tmp_path, "install-scripts")


def installed(consumer, name="central-portal.py"):
    return consumer.project / "scripts" / name


def shared(consumer, name="central-portal.py"):
    return consumer.source / "scripts" / name


def test_the_recipe_installs_every_shared_tool_and_nothing_else():
    recipe = (ROOT / "examples" / "dev-tools.just").read_text()
    lists = re.findall(r"^ {4}scripts=\(([^)]*)\)$", recipe, re.MULTILINE)
    assert len(lists) == 1, "examples/dev-tools.just must keep the install-scripts list on one scripts=(...) line"
    # Every tracked top-level file under scripts/ is a shared tool; tests live in scripts/tests/.
    tracked = subprocess.run(["git", "ls-files", "--", ":(glob)scripts/*"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    assert sorted(lists[0].split()) == sorted(path.removeprefix("scripts/") for path in tracked)


def test_preserves_an_ignored_consumer_file_at_a_managed_path(consumer):
    (consumer.project / ".gitignore").write_text("scripts/central-portal.py\n")
    consumer.commit()
    (consumer.project / "scripts").mkdir()
    installed(consumer).write_text("# Ignored consumer copy.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert installed(consumer).read_text() == "# Ignored consumer copy.\n"


def test_rejects_a_directory_at_a_managed_path(consumer):
    kept = installed(consumer) / "kept.txt"
    kept.parent.mkdir(parents=True)
    kept.write_text("Committed directory content.\n")
    consumer.commit()
    result = consumer.install()
    assert result.returncode != 0
    assert "Invalid script" in result.stderr
    assert kept.read_text() == "Committed directory content.\n"


def test_rejects_a_symlinked_script_in_the_archive(consumer):
    shared(consumer).unlink()
    shared(consumer).symlink_to("/etc/hosts")
    consumer.pack()
    result = consumer.install()
    assert result.returncode != 0
    assert "Invalid script" in result.stderr
    assert not installed(consumer).exists()


def test_installs_the_selected_revision_as_an_executable_and_preserves_consumer_files(consumer):
    local = installed(consumer, "local-tool.py")
    local_test = consumer.project / "scripts" / "tests" / "test_central_portal.py"
    local_test.parent.mkdir(parents=True)
    local.write_text('print("local")\n')
    local_test.write_text("# Consumer workflow tests.\n")
    result = consumer.install()
    assert result.returncode == 0, result.stderr
    assert "Installed shared scripts" in result.stdout
    assert json.loads(consumer.request.read_text()) == tarball_request()
    assert installed(consumer).read_bytes() == (ROOT / "scripts" / "central-portal.py").read_bytes()
    assert executable(installed(consumer))
    assert local.read_text() == 'print("local")\n'
    assert local_test.read_text() == "# Consumer workflow tests.\n"
    assert not (consumer.project / "scripts" / "tests" / "conftest.py").exists()


def test_replaces_a_committed_consumer_copy_with_the_pinned_shared_version(consumer):
    (consumer.project / "scripts").mkdir()
    installed(consumer).write_text("# The consumer copy before migration.\n")
    installed(consumer).chmod(0o644)
    consumer.commit()
    result = consumer.install()
    assert result.returncode == 0, result.stderr
    assert installed(consumer).read_bytes() == shared(consumer).read_bytes()


# With one listed tool this cannot show that validation precedes every replacement.
# When a second tool is added, remove the last listed one here after changing an earlier one.
def test_a_revision_without_a_selected_script_replaces_nothing(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    before = installed(consumer).read_bytes()
    shared(consumer).unlink()
    consumer.pack()
    result = consumer.install(OTHER_REVISION)
    assert result.returncode != 0
    assert "Invalid script" in result.stderr
    assert installed(consumer).read_bytes() == before


def test_preserves_tracked_edits_to_a_managed_script(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    installed(consumer).write_text("# Local changes.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert installed(consumer).read_text() == "# Local changes.\n"


def test_preserves_an_untracked_consumer_file_at_a_managed_path(consumer):
    (consumer.project / "scripts").mkdir()
    installed(consumer).write_text("# Uncommitted consumer copy.\n")
    result = consumer.install()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert installed(consumer).read_text() == "# Uncommitted consumer copy.\n"


def test_rejects_a_symlinked_scripts_directory_or_managed_script(consumer):
    (consumer.project / "elsewhere").mkdir()
    (consumer.project / "scripts").symlink_to("elsewhere")
    result = consumer.install()
    assert result.returncode != 0
    assert "must not be a symlink" in result.stderr
    assert not consumer.request.exists()
    (consumer.project / "scripts").unlink()
    (consumer.project / "scripts").mkdir()
    target = consumer.project / "elsewhere" / "target.py"
    target.write_text("# Outside the managed path.\n")
    installed(consumer).symlink_to("../elsewhere/target.py")
    result = consumer.install()
    assert result.returncode != 0
    assert "Invalid script" in result.stderr
    assert target.read_text() == "# Outside the managed path.\n"


def test_installs_an_update_that_only_changes_the_executable_bit(consumer):
    shared(consumer).chmod(0o644)
    consumer.pack()
    assert consumer.install().returncode == 0
    consumer.commit()
    assert not executable(installed(consumer))
    shared(consumer).chmod(0o755)
    consumer.pack()
    result = consumer.install(OTHER_REVISION)
    assert result.returncode == 0, result.stderr
    assert executable(installed(consumer))

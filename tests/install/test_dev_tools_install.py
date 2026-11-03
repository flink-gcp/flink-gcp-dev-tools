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

"""Scenarios that span both units: one download, checks before any replacement, and rollback."""

import os

import pytest

from install_fixture import OTHER_REVISION, ROOT, Consumer, tarball_request, write_executable

# Logs every move as "<origin> <managed path> <status>". It fails the moves listed in FIXTURE_MV_FAIL, copies and
# then fails those in FIXTURE_MV_COPY_FAIL as a move across file systems can, and after completing a move listed in
# FIXTURE_MV_SIGNAL it sends SIGTERM to the recipe's shell.
# The origin is "source" for a move from the extracted archive, "previous" for a restore, and
# "project" for moving an installed copy aside.
FAKE_MV = """\
#!/usr/bin/env python3
import os, shutil, signal, subprocess, sys
from pathlib import Path
source, target = sys.argv[-2], sys.argv[-1]
# The recipe stages <staging>/source/<unit>/<item> and <staging>/previous/<index>; managed paths are relative.
if Path(source).is_absolute() and Path(source).parent.parent.name == "source":
    origin = "source"
elif Path(source).is_absolute() and Path(source).parent.name == "previous":
    origin = "previous"
else:
    origin = "project"
# Moving an installed copy aside goes from the managed path; every other move goes to it.
path = source if origin == "project" else target
move = f"{origin}:{path}"
env = dict(os.environ, PATH=os.environ["FIXTURE_BASE_PATH"])
if move in os.environ.get("FIXTURE_MV_FAIL", "").split(","):
    status = 1
elif move in os.environ.get("FIXTURE_MV_COPY_FAIL", "").split(","):
    (shutil.copytree if os.path.isdir(source) else shutil.copy2)(source, target)
    status = 1
else:
    status = subprocess.run(["mv", *sys.argv[1:]], env=env).returncode
with open(os.environ["FIXTURE_MV_LOG"], "a") as log:
    log.write(f"{origin} {path} {status}\\n")
if move in os.environ.get("FIXTURE_MV_SIGNAL", "").split(","):
    os.kill(os.getppid(), signal.SIGTERM)
sys.exit(status)
"""

# Fails "rm" for the paths listed in FIXTURE_RM_FAIL, as a directory the user cannot delete would.
FAKE_RM = """\
#!/usr/bin/env python3
import os, subprocess, sys
if sys.argv[-1] in os.environ.get("FIXTURE_RM_FAIL", "").split(","):
    sys.exit(1)
env = dict(os.environ, PATH=os.environ["FIXTURE_BASE_PATH"])
sys.exit(subprocess.run(["rm", *sys.argv[1:]], env=env).returncode)
"""

SKILL = ".agents/skills/self-review"
SCRIPT = "scripts/central-portal.py"


@pytest.fixture
def consumer(tmp_path):
    return Consumer(tmp_path)


def installed_skill(consumer):
    return consumer.project / SKILL / "SKILL.md"


def installed_script(consumer):
    return consumer.project / SCRIPT


def shared_skill(consumer):
    return consumer.source / "skills" / "self-review" / "SKILL.md"


def shared_script(consumer):
    return consumer.source / "scripts" / "central-portal.py"


def change_both_units(consumer):
    shared_skill(consumer).write_text("Upstream change.\n")
    shared_script(consumer).write_text("# Upstream change.\n")
    consumer.pack()


def install_logging_moves(consumer, fail=(), interrupt=(), removals=(), copy_fail=()):
    """Install OTHER_REVISION through the logging fake mv and return the result and the logged moves."""
    write_executable(consumer.bin / "mv", FAKE_MV)
    write_executable(consumer.bin / "rm", FAKE_RM)
    log = consumer.project.parent / "mv.log"
    log.touch()
    result = consumer.install(OTHER_REVISION, env={
        "FIXTURE_BASE_PATH": os.environ["PATH"], "FIXTURE_MV_LOG": str(log),
        "FIXTURE_MV_FAIL": ",".join(fail), "FIXTURE_MV_SIGNAL": ",".join(interrupt),
        "FIXTURE_RM_FAIL": ",".join(removals), "FIXTURE_MV_COPY_FAIL": ",".join(copy_fail)})
    return result, log.read_text().splitlines()


def test_installs_every_unit_from_one_download(consumer):
    result = consumer.install()
    assert result.returncode == 0, result.stderr
    assert consumer.requests() == [tarball_request()]
    assert installed_skill(consumer).read_bytes() == (ROOT / "skills" / "self-review" / "SKILL.md").read_bytes()
    assert installed_script(consumer).read_bytes() == (ROOT / "scripts" / "central-portal.py").read_bytes()
    assert "Installed workflow skills and shared tools" in result.stdout
    assert not any(consumer.tmp.iterdir())


def test_an_invalid_later_unit_replaces_nothing_in_an_earlier_unit(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    before = installed_skill(consumer).read_bytes()
    shared_skill(consumer).write_text("Upstream change.\n")
    shared_script(consumer).unlink()
    consumer.pack()
    result, moves = install_logging_moves(consumer)
    assert result.returncode != 0
    assert "Invalid script" in result.stderr
    # Nothing moved, so the skill was never replaced and then restored.
    assert moves == []
    assert installed_skill(consumer).read_bytes() == before


def test_local_changes_in_a_later_unit_replace_nothing_in_an_earlier_unit(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    before = installed_skill(consumer).read_bytes()
    installed_script(consumer).write_text("# Local changes.\n")
    shared_skill(consumer).write_text("Upstream change.\n")
    consumer.pack()
    result, moves = install_logging_moves(consumer)
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert moves == []
    assert installed_skill(consumer).read_bytes() == before
    assert installed_script(consumer).read_text() == "# Local changes.\n"


@pytest.mark.parametrize("interrupted", [False, True], ids=["failure", "interruption"])
@pytest.mark.parametrize("previously_installed", [True, False], ids=["update", "first-install"])
def test_a_failed_replacement_in_a_later_unit_restores_the_earlier_unit(consumer, previously_installed, interrupted):
    if previously_installed:
        assert consumer.install().returncode == 0
        consumer.commit()
    skill_before = installed_skill(consumer).read_bytes() if previously_installed else None
    script_before = installed_script(consumer).read_bytes() if previously_installed else None
    change_both_units(consumer)
    # The interruption arrives after the script move succeeds, so only the signal can stop the installation.
    if interrupted:
        result, moves = install_logging_moves(consumer, interrupt=[f"source:{SCRIPT}"])
        last = f"source {SCRIPT} 0"
    else:
        result, moves = install_logging_moves(consumer, fail=[f"source:{SCRIPT}"])
        last = f"source {SCRIPT} 1"
    assert result.returncode != 0
    assert "Installed" not in result.stdout
    # The skill was installed before the script move, so the final state proves the rollback.
    assert moves.index(f"source {SKILL} 0") < moves.index(last)
    if previously_installed:
        assert installed_skill(consumer).read_bytes() == skill_before
        assert installed_script(consumer).read_bytes() == script_before
    else:
        assert not any((consumer.project / ".agents" / "skills").iterdir())
        assert not installed_script(consumer).exists()
    assert not any(consumer.tmp.iterdir())


def test_an_interruption_after_moving_a_copy_aside_restores_it(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    skill_before = installed_skill(consumer).read_bytes()
    change_both_units(consumer)
    result, moves = install_logging_moves(consumer, interrupt=[f"project:{SKILL}"])
    assert result.returncode != 0
    assert moves[0] == f"project {SKILL} 0"
    assert installed_skill(consumer).read_bytes() == skill_before
    assert not any(consumer.tmp.iterdir())


@pytest.mark.parametrize(("fail", "removals", "expected"), [
    ([f"source:{SCRIPT}", f"previous:{SKILL}"], [], f"previous {SKILL} 1"),
    ([f"source:{SCRIPT}"], [SKILL], None),
], ids=["move", "removal"])
def test_a_failed_restore_keeps_the_previous_copy_and_says_where(consumer, fail, removals, expected):
    assert consumer.install().returncode == 0
    consumer.commit()
    skill_before = installed_skill(consumer).read_bytes()
    change_both_units(consumer)
    result, moves = install_logging_moves(consumer, fail=fail, removals=removals)
    assert result.returncode != 0
    if expected:
        assert expected in moves
    else:
        # The new copy could not be removed, so restoring into it would nest the previous copy inside.
        assert not any(move.startswith(f"previous {SKILL} ") for move in moves)
        assert installed_skill(consumer).read_text() == "Upstream change.\n"
    assert "could not be restored" in result.stderr
    (staging,) = consumer.tmp.iterdir()
    (previous,) = (staging / "previous").iterdir()
    assert f"The previous copy of {SKILL} remains at {previous}." in result.stderr
    assert (previous / "SKILL.md").read_bytes() == skill_before


@pytest.mark.parametrize(("fail", "removals"), [
    ([f"source:{SCRIPT}", f"previous:{SCRIPT}"], []),
    ([f"source:{SCRIPT}"], [SCRIPT]),
], ids=["move", "removal"])
def test_a_failed_restore_of_a_later_item_still_restores_the_earlier_ones(consumer, fail, removals):
    assert consumer.install().returncode == 0
    consumer.commit()
    skill_before = installed_skill(consumer).read_bytes()
    script_before = installed_script(consumer).read_bytes()
    change_both_units(consumer)
    # The script is restored first, so its failure must not stop the skill's restore.
    result, moves = install_logging_moves(consumer, fail=fail, removals=removals)
    assert result.returncode != 0
    assert f"previous {SKILL} 0" in moves
    assert installed_skill(consumer).read_bytes() == skill_before
    assert "could not be restored" in result.stderr
    (staging,) = consumer.tmp.iterdir()
    assert [path.read_bytes() for path in (staging / "previous").iterdir() if path.is_file()] == [script_before]


def test_a_failed_move_aside_leaves_that_copy_in_place(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    script_before = installed_script(consumer).read_bytes()
    skill_before = installed_skill(consumer).read_bytes()
    change_both_units(consumer)
    result, moves = install_logging_moves(consumer, fail=[f"project:{SCRIPT}"])
    assert result.returncode != 0
    assert f"project {SCRIPT} 1" in moves
    assert installed_script(consumer).read_bytes() == script_before
    assert installed_skill(consumer).read_bytes() == skill_before
    assert not any(consumer.tmp.iterdir())


def test_a_move_aside_that_fails_after_copying_keeps_both_copies(consumer):
    assert consumer.install().returncode == 0
    consumer.commit()
    script_before = installed_script(consumer).read_bytes()
    skill_before = installed_skill(consumer).read_bytes()
    change_both_units(consumer)
    result, moves = install_logging_moves(consumer, copy_fail=[f"project:{SCRIPT}"])
    assert result.returncode != 0
    assert f"project {SCRIPT} 1" in moves
    # Neither copy is known to be complete, so the recipe keeps both and restores the skill as usual.
    assert f"Could not restore {SCRIPT}: it was interrupted while being moved aside." in result.stderr
    assert installed_script(consumer).read_bytes() == script_before
    assert installed_skill(consumer).read_bytes() == skill_before
    (staging,) = consumer.tmp.iterdir()
    assert f"The previous copy of {SCRIPT} remains at {staging / 'previous'}/" in result.stderr

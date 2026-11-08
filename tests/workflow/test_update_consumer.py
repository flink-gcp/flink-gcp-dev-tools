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

"""The Update consumers steps against disposable repositories, with a controlled GitHub CLI, just and Hugo."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "update-consumer.sh"
CONSUMER = "flink-gcp/consumer"
BRANCH = "dev-tools/update"
BOT_EMAIL = "317469580+flink-gcp-bot[bot]@users.noreply.github.com"
SHARED_URL = "https://github.com/flink-gcp/flink-gcp-dev-tools"

# Answers each call with the first response whose "match" strings all occur in the joined arguments,
# and logs every call; an unanswered call fails as an unreachable API would.
FAKE_GH = """\
#!/usr/bin/env python3
import json, os, sys
call = " ".join(sys.argv[1:])
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
with open(os.environ["FAKE_GH_RESPONSES"]) as responses:
    for response in json.load(responses):
        if all(part in call for part in response["match"]):
            sys.stdout.write(response.get("stdout", ""))
            sys.exit(response.get("exit", 0))
sys.stderr.write(f"unexpected gh call: {call}\\n")
sys.exit(1)
"""

# Installs one skill naming the pinned revision, padded with FAKE_JUST_LINES lines of FAKE_JUST_WIDTH characters,
# and FAKE_JUST_EXTRA as a path the update must not touch.
FAKE_JUST = """\
#!/usr/bin/env python3
import os, pathlib, re, sys
assert sys.argv[1:] == ["dev-tools-sync"], sys.argv
pin = re.search(r'^dev_tools_revision := "([0-9a-f]{40})"$', pathlib.Path("justfile").read_text(), re.M).group(1)
skill = pathlib.Path(".agents/skills/self-review/SKILL.md")
skill.parent.mkdir(parents=True, exist_ok=True)
width = int(os.environ.get("FAKE_JUST_WIDTH", "4"))
skill.write_text(f"revision {pin}\\n" + ("l" * width + "\\n") * int(os.environ.get("FAKE_JUST_LINES", "0")))
if os.environ.get("FAKE_JUST_EXTRA"):
    pathlib.Path(os.environ["FAKE_JUST_EXTRA"]).write_text("unexpected\\n")
"""

# Rewrites the module requirement as `hugo mod get` would, with the commit's pseudo-version.
FAKE_HUGO = """\
#!/usr/bin/env python3
import pathlib, sys
if sys.argv[1:3] == ["mod", "get"]:
    sha = sys.argv[3].rsplit("@", 1)[1]
    pathlib.Path("go.mod").write_text(f"require module v0.0.0-20260101000000-{sha[:12]}\\n")
"""


# Keeps the developer's Git configuration, such as tag signing, out of the fixture repositories and the steps.
GIT_ENV = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def commit(cwd: Path, message: str, files: dict[str, str]) -> str:
    for name, text in files.items():
        path = cwd / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(cwd, "add", "-A")
    git(cwd, "commit", "--quiet", "--allow-empty", "-m", message)
    return git(cwd, "rev-parse", "HEAD")


def init(path: Path, *args: str) -> None:
    path.mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch=main", *args)
    if not args:
        git(path, "config", "user.name", "Fixture")
        git(path, "config", "user.email", "fixture@example.invalid")
        git(path, "config", "commit.gpgsign", "false")


def justfile(pin: str) -> str:
    return f"import 'dev-tools.just'\n\ndev_tools_revision := \"{pin}\"\n\ndev-tools-sync: (install-dev-tools dev_tools_revision)\n"


class Workflow:
    """This repository with a release history, a consumer with its origin, and the Actions step files."""

    def __init__(self, temp: Path):
        self.temp = temp
        self.dev_tools = temp / "dev-tools"
        self.origin = temp / "origin.git"
        self.consumer = self.dev_tools / "consumer"
        self.runner = temp / "runner"
        self.bin = temp / "bin"
        self.env: dict[str, str] = {}
        for directory in (self.runner, self.bin):
            directory.mkdir()

        init(self.dev_tools)
        self.pinned = commit(self.dev_tools, "Pinned", {"examples/dev-tools.just": "# recipe 1\n"})
        self.release = commit(self.dev_tools, "Release", {"examples/dev-tools.just": "# recipe 2\n"})
        git(self.dev_tools, "tag", "v0.1.0")
        # A commit on main that is not released yet; tag_later releases it as v0.2.0.
        self.later = commit(self.dev_tools, "Later", {"examples/dev-tools.just": "# recipe 3\n"})
        git(self.dev_tools, "update-ref", "refs/remotes/origin/main", self.later)
        # A newer-looking release tag off main, which consumers must never receive.
        git(self.dev_tools, "checkout", "--quiet", "-b", "side", self.pinned)
        commit(self.dev_tools, "Side", {})
        git(self.dev_tools, "tag", "v0.9.0")
        git(self.dev_tools, "checkout", "--quiet", "main")

        init(self.origin, "--bare")
        init(self.consumer)
        commit(self.consumer, "Consumer", {
            "justfile": justfile(self.pinned),
            "dev-tools.just": "# recipe 1\n",
            "docs/go.mod": f"require module v0.0.0-20260101000000-{self.pinned[:12]}\n",
            "docs/development.md": f"The site uses commit {self.pinned}.\n",
            ".github/PULL_REQUEST_TEMPLATE.md": "## WHAT\n<!-- what -->\n\n## WHY\n<!-- why -->\n",
        })
        git(self.consumer, "remote", "add", "origin", str(self.origin))
        git(self.consumer, "push", "--quiet", "origin", "main")

        for name, script in (("gh", FAKE_GH), ("just", FAKE_JUST), ("hugo", FAKE_HUGO)):
            (self.bin / name).write_text(script)
            (self.bin / name).chmod(0o755)
        self.gh_log = temp / "gh.log"
        self.gh_responses = temp / "gh.json"
        self.respond([])

    def respond(self, responses: list[dict]) -> None:
        """Sets the GitHub CLI's answers; the default branch is always main."""
        self.gh_responses.write_text(json.dumps(
            [*responses, {"match": ["repo view"], "stdout": "main\n"}]))

    def gh_calls(self) -> list[list[str]]:
        if not self.gh_log.exists():
            return []
        return [json.loads(line) for line in self.gh_log.read_text().splitlines()]

    def step(self, command: str, **env: str) -> tuple[subprocess.CompletedProcess, dict[str, str]]:
        """Runs one step as Actions would: with the variables earlier steps exported, and fresh outputs."""
        files = {name: self.runner / name.lower() for name in ("GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY")}
        files["GITHUB_OUTPUT"].write_text("")
        process = subprocess.run(
            [str(SCRIPT), command], cwd=self.dev_tools, capture_output=True, text=True,
            env={
                **os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                **{name: str(path) for name, path in files.items()},
                "RUNNER_TEMP": str(self.runner), "FAKE_GH_LOG": str(self.gh_log),
                "FAKE_GH_RESPONSES": str(self.gh_responses), "CONSUMER": CONSUMER, "BRANCH": BRANCH,
                "BOT_LOGIN": "flink-gcp-bot[bot]", "BOT_EMAIL": BOT_EMAIL, "SHARED_URL": SHARED_URL,
                "GH_TOKEN": "token", **GIT_ENV,
                **self.env, **env,
            })
        if files["GITHUB_ENV"].exists():
            for line in files["GITHUB_ENV"].read_text().splitlines():
                name, value = line.split("=", 1)
                self.env[name] = value
        outputs = dict(line.split("=", 1) for line in files["GITHUB_OUTPUT"].read_text().splitlines())
        return process, outputs

    def tag_later(self) -> None:
        git(self.dev_tools, "tag", "v0.2.0", self.later)

    def release_step(self, tag: str = "v0.1.0") -> None:
        """Resolves as a run started by `tag` would; tagging v0.2.0 makes it the latest release."""
        if tag == "v0.2.0":
            self.tag_later()
        process, _ = self.step("resolve", EVENT="push", TAG=tag)
        assert process.returncode == 0, process.stdout + process.stderr

    def open_pr(self, pin: str, *, emails: tuple[str, ...] = (BOT_EMAIL,), draft: bool = True,
                title: str = "Update flink-gcp-dev-tools to v0.1.0", body: str = "") -> str:
        """Pushes an update branch pinning `pin` and answers the GitHub CLI as if PR #7 were open from it."""
        git(self.consumer, "checkout", "--quiet", "-b", "update")
        head = commit(self.consumer, "Update", {"justfile": justfile(pin)})
        git(self.consumer, "push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}")
        git(self.consumer, "checkout", "--quiet", "main")
        self.respond([
            {"match": ["api", "compare/main..."],
             "stdout": "".join(f"{email}\n" for email in emails)},
            {"match": ["pr list"], "stdout": f"7 {head}\n"},
            {"match": ["api", f"contents/justfile?ref={head}"], "stdout": justfile(pin)},
            {"match": ["pr view", "isDraft"], "stdout": f"{str(draft).lower()}\n"},
            {"match": ["pr view"], "stdout": f"{title}\n{body}\n"},
            {"match": ["pr edit"]},
            {"match": ["pr ready"]},
        ])
        return head


@pytest.fixture
def workflow(tmp_path):
    return Workflow(tmp_path)


def error(process: subprocess.CompletedProcess) -> str:
    assert process.returncode != 0
    return process.stdout


class TestResolve:
    def test_a_release_tag_resolves_to_its_commit(self, workflow):
        process, _ = workflow.step("resolve", EVENT="push", TAG="v0.1.0")
        assert process.returncode == 0, process.stdout
        assert workflow.env == {"TARGET": workflow.release, "LABEL": "v0.1.0", "DRY_RUN": "false"}

    @pytest.mark.parametrize("event, tag", [("push", "v0.1.0"), ("workflow_dispatch", "")])
    def test_every_release_run_proposes_the_latest_release_on_main(self, workflow, event, tag):
        workflow.tag_later()
        # Neither a pre-release, nor a tag off main (v0.9.0), nor the lexically greatest v0.2.0 may win.
        git(workflow.dev_tools, "tag", "v0.11.0-rc.1", workflow.later)
        git(workflow.dev_tools, "tag", "v0.10.0", workflow.later)
        process, _ = workflow.step("resolve", EVENT=event, TAG=tag)
        assert process.returncode == 0, process.stdout
        assert (workflow.env["TARGET"], workflow.env["LABEL"]) == (workflow.later, "v0.10.0")
        assert ("rather than v0.1.0" in process.stdout) == bool(tag)

    def test_refuses_when_main_has_no_release(self, workflow):
        git(workflow.dev_tools, "tag", "--delete", "v0.1.0")
        process, _ = workflow.step("resolve", EVENT="workflow_dispatch", TAG="")
        assert "main has no release tag" in error(process)
        assert workflow.env == {}

    def test_a_pull_request_is_a_dry_run_of_its_head(self, workflow):
        process, _ = workflow.step("resolve", EVENT="pull_request", HEAD_SHA=workflow.later)
        assert process.returncode == 0, process.stdout
        assert workflow.env == {"TARGET": workflow.later, "LABEL": workflow.later[:12], "DRY_RUN": "true"}



class TestState:
    def test_proposes_when_no_branch_or_pr_exists(self, workflow):
        workflow.release_step()
        workflow.respond([{"match": ["pr list"], "stdout": ""}])
        process, outputs = workflow.step("state")
        assert process.returncode == 0, process.stdout + process.stderr
        assert outputs == {"action": "propose"}
        assert workflow.env["PREVIOUS"] == workflow.pinned
        assert workflow.env["TITLE"] == "Update flink-gcp-dev-tools to v0.1.0"
        assert (workflow.env["BASE"], workflow.env["LEASE"], workflow.env["PR_NUMBER"]) == ("main", "", "")
        # Only PRs from the consumer's own branch count, not a fork's branch with the same name.
        [pr_list] = [call for call in workflow.gh_calls() if call[:2] == ["pr", "list"]]
        assert "select(.isCrossRepository | not)" in pr_list[pr_list.index("--jq") + 1]

    def test_skips_a_consumer_that_already_pins_the_release(self, workflow):
        workflow.release_step()
        commit(workflow.consumer, "Pin", {"justfile": justfile(workflow.release)})
        process, outputs = workflow.step("state")
        assert outputs == {"action": "skip"}
        assert "already pins v0.1.0" in process.stdout
        assert workflow.gh_calls() == []

    def test_refuses_a_release_that_does_not_descend_from_the_pin(self, workflow):
        workflow.release_step()
        commit(workflow.consumer, "Pin", {"justfile": justfile(workflow.later)})
        process, outputs = workflow.step("state")
        assert f"v0.1.0 does not descend from the current pin {workflow.later}" in error(process)
        assert outputs == {}

    def test_skips_when_the_open_pr_proposes_a_later_release(self, workflow):
        workflow.release_step()
        workflow.open_pr(workflow.later)
        process, outputs = workflow.step("state")
        assert outputs == {"action": "skip"}
        assert "already proposes a release after v0.1.0" in process.stdout

    def test_a_rerun_only_refreshes_the_pr_text(self, workflow):
        workflow.release_step()
        head = workflow.open_pr(workflow.release)
        process, outputs = workflow.step("state")
        assert outputs == {"action": "describe"}, process.stdout
        assert (workflow.env["LEASE"], workflow.env["PR_NUMBER"]) == (head, "7")

    def test_proposes_a_later_release_into_the_open_pr(self, workflow):
        workflow.release_step("v0.2.0")
        head = workflow.open_pr(workflow.release)
        process, outputs = workflow.step("state")
        assert outputs == {"action": "propose"}, process.stdout
        assert (workflow.env["LEASE"], workflow.env["PR_NUMBER"]) == (head, "7")

    def test_refuses_a_branch_with_commits_by_others(self, workflow):
        workflow.release_step("v0.2.0")
        workflow.open_pr(workflow.release, emails=(BOT_EMAIL, "maintainer@example.invalid"))
        process, outputs = workflow.step("state")
        assert "has commits by others" in error(process)
        assert outputs == {}

    def test_checks_the_committer_of_each_branch_commit_as_well_as_its_author(self, workflow):
        workflow.release_step("v0.2.0")
        workflow.open_pr(workflow.release)
        workflow.step("state")
        [compare] = [call for call in workflow.gh_calls() if "compare/" in " ".join(call)]
        assert compare[compare.index("--jq") + 1] == ".commits[].commit | .author.email, .committer.email"

    def test_refuses_a_branch_with_commits_by_others_without_a_pr(self, workflow):
        workflow.release_step()
        workflow.open_pr(workflow.release, emails=("maintainer@example.invalid",))
        workflow.respond([{"match": ["api", "compare/main..."], "stdout": "maintainer@example.invalid\n"}])
        assert "has commits by others" in error(workflow.step("state")[0])

    @pytest.mark.parametrize("failing", [["api", "compare/main..."], ["pr list"]])
    def test_a_failed_github_call_fails_the_step(self, workflow, failing):
        workflow.release_step("v0.2.0")
        workflow.open_pr(workflow.release)
        responses = json.loads(workflow.gh_responses.read_text())
        workflow.gh_responses.write_text(json.dumps([{"match": failing, "exit": 1}, *responses]))
        process, outputs = workflow.step("state")
        assert process.returncode != 0
        assert outputs == {}

    def test_a_dry_run_reads_only_the_pin(self, workflow):
        process, _ = workflow.step("resolve", EVENT="pull_request", HEAD_SHA=workflow.later)
        process, outputs = workflow.step("state")
        assert outputs == {"action": "propose"}, process.stdout
        assert workflow.gh_calls() == []

    def test_refuses_a_consumer_without_a_tracked_recipe_copy(self, workflow):
        workflow.release_step()
        git(workflow.consumer, "rm", "--quiet", "dev-tools.just")
        assert "must track dev-tools.just" in error(workflow.step("state")[0])

    def test_refuses_a_justfile_without_exactly_one_pin(self, workflow):
        workflow.release_step()
        (workflow.consumer / "justfile").write_text(justfile(workflow.pinned) * 2)
        assert "exactly one line" in error(workflow.step("state")[0])


class TestPrepare:
    def prepare(self, workflow, **env: str) -> subprocess.CompletedProcess:
        workflow.release_step()
        workflow.respond([{"match": ["pr list"], "stdout": ""}])
        process, _ = workflow.step("state")
        assert process.returncode == 0, process.stdout + process.stderr
        process, _ = workflow.step("apply", **env)
        return process

    def test_writes_both_pins_the_recipe_and_the_synchronized_copies_as_a_patch(self, workflow):
        process = self.prepare(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        staged = git(workflow.consumer, "diff", "--cached", "--name-only").splitlines()
        assert staged == [".agents/skills/self-review/SKILL.md", "dev-tools.just", "docs/go.mod", "justfile"]
        assert f'dev_tools_revision := "{workflow.release}"' in (workflow.consumer / "justfile").read_text()
        assert (workflow.consumer / "dev-tools.just").read_text() == "# recipe 2\n"
        assert workflow.release[:12] in (workflow.consumer / "docs/go.mod").read_text()
        assert "dev-tools.just" in (workflow.runner / "update" / "update.patch").read_text()

    def test_refuses_a_change_outside_the_managed_paths(self, workflow):
        process = self.prepare(workflow, FAKE_JUST_EXTRA="README.md")
        assert "The update changes unexpected paths: README.md" in error(process)
        assert not (workflow.runner / "update" / "update.patch").exists()

    def test_describes_the_update_in_the_consumer_template(self, workflow):
        assert self.prepare(workflow).returncode == 0
        process, _ = workflow.step("describe")
        assert process.returncode == 0, process.stdout + process.stderr
        body = (workflow.runner / "update" / "body.md").read_text()
        assert body.startswith("## WHAT\n\nUpdate the shared development tools from flink-gcp-dev-tools "
                               f"`{workflow.pinned[:12]}` to [`v0.1.0`]({SHARED_URL}/releases/tag/v0.1.0)")
        assert f"{SHARED_URL}/compare/{workflow.pinned}...{workflow.release}" in body
        # The guidance that repeats the pin is listed; the justfile no longer names it.
        assert "These lines still name the previous commit" in body
        assert "- `docs/development.md:1`" in body
        assert "justfile" not in body.split("previous commit")[1].split("## WHY")[0]
        assert "\n## WHY\n\nflink-gcp-dev-tools released v0.1.0" in body
        summary = (workflow.runner / "github_step_summary").read_text()
        assert "### flink-gcp/consumer: Update flink-gcp-dev-tools to v0.1.0" in summary
        # The summary shows the patch itself, not only its file names.
        assert "````diff\ndiff --git a/" in summary and "+# recipe 2" in summary
        assert "continues in this job's artifact" not in summary

    def test_the_summary_points_to_the_artifact_for_a_long_patch(self, workflow):
        assert self.prepare(workflow, FAKE_JUST_LINES="1200").returncode == 0
        process, _ = workflow.step("describe")
        assert process.returncode == 0, process.stdout + process.stderr
        summary = (workflow.runner / "github_step_summary").read_text()
        assert "continues in this job's artifact, update-consumer." in summary
        assert summary.count("\n+llll") < 1000

    def test_the_summary_stays_under_githubs_size_limit_for_long_lines(self, workflow):
        assert self.prepare(workflow, FAKE_JUST_LINES="600", FAKE_JUST_WIDTH="2048").returncode == 0
        process, _ = workflow.step("describe")
        assert process.returncode == 0, process.stdout + process.stderr
        summary = (workflow.runner / "github_step_summary").read_text()
        assert len(summary.encode()) < 1024 * 1024
        assert "continues in this job's artifact" in summary and summary.rstrip().endswith("</details>")

    def test_refuses_a_template_without_the_sections_it_fills(self, workflow):
        assert self.prepare(workflow).returncode == 0
        (workflow.consumer / ".github/PULL_REQUEST_TEMPLATE.md").write_text("## Summary\n")
        assert "no longer has the WHAT and WHY sections" in error(workflow.step("describe")[0])


class TestPush:
    def prepared(self, workflow, *, tag: str = "v0.1.0") -> None:
        """Prepares in one checkout and resets it to a fresh clone, as the propose job's checkout is."""
        workflow.release_step(tag)
        process, outputs = workflow.step("state")
        assert outputs.get("action") in ("propose", "describe"), process.stdout + process.stderr
        for command in ("apply", "describe"):
            process, _ = workflow.step(command)
            assert process.returncode == 0, process.stdout + process.stderr
        git(workflow.consumer, "reset", "--quiet", "--hard", "HEAD")
        git(workflow.consumer, "clean", "--quiet", "-fdx")
        self.action = outputs["action"]

    def push(self, workflow) -> subprocess.CompletedProcess:
        process, _ = workflow.step("push", ACTION=self.action)
        return process

    def test_pushes_the_bot_commit_and_opens_a_draft_pr(self, workflow):
        workflow.respond([{"match": ["pr list"], "stdout": ""}, {"match": ["pr create"]}])
        self.prepared(workflow)
        process = self.push(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        pushed = git(workflow.origin, "log", "-1", "--format=%ae%n%s%n%P", BRANCH).splitlines()
        assert pushed == [BOT_EMAIL, "Update flink-gcp-dev-tools to v0.1.0", git(workflow.origin, "rev-parse", "main")]
        assert git(workflow.origin, "diff", "--name-only", "main", BRANCH).splitlines() == [
            ".agents/skills/self-review/SKILL.md", "dev-tools.just", "docs/go.mod", "justfile"]
        [create] = [call for call in workflow.gh_calls() if call[:2] == ["pr", "create"]]
        assert create[2:] == ["-R", CONSUMER, "--draft", "--base", "main", "--head", BRANCH,
                              "--title", "Update flink-gcp-dev-tools to v0.1.0", "--body-file",
                              str(workflow.runner / "update" / "body.md")]

    def test_a_later_release_replaces_the_pr_content_and_returns_it_to_draft(self, workflow):
        workflow.open_pr(workflow.release, draft=False)
        self.prepared(workflow, tag="v0.2.0")
        assert self.action == "propose"
        process = self.push(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        assert f'"{workflow.later}"' in git(workflow.origin, "show", f"{BRANCH}:justfile")
        commands = [call[:2] for call in workflow.gh_calls() if call[0] == "pr"]
        # The PR returns to Draft before the push and is checked again after it, then gets the new text.
        assert commands[-6:] == [["pr", "view"], ["pr", "ready"], ["pr", "view"], ["pr", "ready"],
                                 ["pr", "view"], ["pr", "edit"]]

    def test_returns_to_draft_a_pr_marked_ready_after_the_state_was_read(self, workflow):
        workflow.open_pr(workflow.release, draft=True)
        self.prepared(workflow, tag="v0.2.0")
        responses = json.loads(workflow.gh_responses.read_text())
        workflow.gh_responses.write_text(json.dumps([{"match": ["pr view", "isDraft"], "stdout": "false\n"},
                                                     *responses]))
        process = self.push(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        assert ["pr", "ready"] in [call[:2] for call in workflow.gh_calls()]

    def test_leaves_a_draft_pr_as_it_is(self, workflow):
        workflow.open_pr(workflow.release, draft=True)
        self.prepared(workflow, tag="v0.2.0")
        assert self.push(workflow).returncode == 0
        assert ["pr", "ready"] not in [call[:2] for call in workflow.gh_calls()]

    def test_a_failed_draft_conversion_pushes_nothing(self, workflow):
        head = workflow.open_pr(workflow.release, draft=False)
        self.prepared(workflow, tag="v0.2.0")
        responses = json.loads(workflow.gh_responses.read_text())
        workflow.gh_responses.write_text(json.dumps([{"match": ["pr ready"], "exit": 1}, *responses]))
        assert self.push(workflow).returncode != 0
        # A rerun would only describe a pushed update, so the conversion must come before the push.
        assert git(workflow.origin, "rev-parse", BRANCH) == head

    def test_leaves_an_update_prepared_for_an_older_release_to_the_newer_run(self, workflow):
        workflow.respond([{"match": ["pr list"], "stdout": ""}])
        self.prepared(workflow)
        # v0.2.0 is tagged after the prepare job resolved v0.1.0.
        workflow.release_step("v0.2.0")
        process = self.push(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        assert "not for the latest release, v0.2.0" in process.stdout
        assert git(workflow.origin, "branch", "--list", BRANCH) == ""
        assert not [call for call in workflow.gh_calls() if call[:2] == ["pr", "create"]]

    def test_a_rerun_leaves_an_up_to_date_pr_unchanged(self, workflow):
        head = workflow.open_pr(workflow.release)
        self.prepared(workflow)
        body = (workflow.runner / "update" / "body.md").read_text()
        # The PR already carries this text, as after a run that pushed and edited it.
        responses = json.loads(workflow.gh_responses.read_text())
        for response in responses:
            if response["match"] == ["pr view"]:
                response["stdout"] = f"Update flink-gcp-dev-tools to v0.1.0\n{body}"
        workflow.gh_responses.write_text(json.dumps(responses))
        process = self.push(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        assert git(workflow.origin, "rev-parse", BRANCH) == head
        assert [call[:2] for call in workflow.gh_calls() if call[0] == "pr"][-1] == ["pr", "view"]

    def test_a_rerun_restores_the_text_of_a_pr_whose_edit_failed(self, workflow):
        head = workflow.open_pr(workflow.release, title="Update flink-gcp-dev-tools to v0.0.9")
        self.prepared(workflow)
        assert self.action == "describe"
        process = self.push(workflow)
        assert process.returncode == 0, process.stdout + process.stderr
        assert git(workflow.origin, "rev-parse", BRANCH) == head
        assert [call[:2] for call in workflow.gh_calls() if call[0] == "pr"][-2:] == [["pr", "view"], ["pr", "edit"]]

    def test_a_rerun_does_not_restore_text_over_a_branch_that_moved(self, workflow):
        workflow.open_pr(workflow.release, title="Update flink-gcp-dev-tools to v0.0.9")
        self.prepared(workflow)
        assert self.action == "describe"
        # A newer release's run replaces the branch after this run decided.
        git(workflow.consumer, "push", "--quiet", "--force", "origin", f"main:refs/heads/{BRANCH}")
        assert "moved after this run read it" in error(self.push(workflow))
        assert ["pr", "edit"] not in [call[:2] for call in workflow.gh_calls()]

    def test_the_lease_refuses_a_branch_that_moved_after_the_check(self, workflow):
        workflow.respond([{"match": ["pr list"], "stdout": ""}])
        self.prepared(workflow)
        git(workflow.consumer, "push", "--quiet", "origin", f"main:refs/heads/{BRANCH}")
        process = self.push(workflow)
        assert process.returncode != 0
        assert not [call for call in workflow.gh_calls() if call[:2] == ["pr", "create"]]

    def test_rechecks_the_paths_of_the_prepared_patch(self, workflow):
        workflow.respond([{"match": ["pr list"], "stdout": ""}])
        self.prepared(workflow)
        patch = workflow.runner / "update" / "update.patch"
        # A tampered patch that also writes outside the managed paths.
        patch.write_text(patch.read_text() + "diff --git a/README.md b/README.md\nnew file mode 100644\n"
                         "--- /dev/null\n+++ b/README.md\n@@ -0,0 +1 @@\n+tampered\n")
        process = self.push(workflow)
        assert "unexpected paths" in error(process)
        assert git(workflow.origin, "branch", "--list", BRANCH) == ""

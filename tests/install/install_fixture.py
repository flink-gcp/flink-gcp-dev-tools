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

"""A disposable consumer checkout and a controlled GitHub CLI that serves this checkout's sources."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40
OTHER_REVISION = "b" * 40

FAKE_GH = """\
#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FIXTURE_REQUEST"], "a") as request:
    request.write(json.dumps(sys.argv[1:]) + "\\n")
if os.environ.get("FIXTURE_DOWNLOAD_FAIL") == "1":
    sys.exit(1)
with open(os.environ["FIXTURE_ARCHIVE"], "rb") as archive:
    sys.stdout.buffer.write(archive.read())
"""


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def write_executable(path: Path, script: str) -> None:
    path.write_text(script)
    path.chmod(0o755)


def executable(path: Path) -> bool:
    return path.stat().st_mode & 0o111 != 0


def tarball_request(sha: str = REVISION) -> list[str]:
    return ["api", f"repos/flink-gcp/flink-gcp-dev-tools/tarball/{sha}"]


class Consumer:
    def __init__(self, temp: Path):
        self.project = temp / "project"
        self.source = temp / "archive" / "source"
        self.bin = temp / "bin"
        self.archive = temp / "source.tar.gz"
        self.request = temp / "request.json"
        # The recipe stages in TMPDIR, so tests can inspect what it leaves there and nothing leaks.
        self.tmp = temp / "tmp"
        for directory in (self.project, self.source, self.bin, self.tmp):
            directory.mkdir(parents=True)
        for directory in ("skills", "scripts"):
            shutil.copytree(ROOT / directory, self.source / directory, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        git(self.project, "init", "--quiet")
        git(self.project, "config", "user.name", "Fixture")
        git(self.project, "config", "user.email", "fixture@example.invalid")
        git(self.project, "config", "commit.gpgsign", "false")
        git(self.project, "config", "core.hooksPath", str(temp / "hooks"))
        git(self.project, "commit", "--quiet", "--allow-empty", "-m", "Initial fixture")
        write_executable(self.bin / "gh", FAKE_GH)
        # Run the recipe with the system Bash, which is 3.2 on macOS, rather than a newer one on PATH.
        (self.bin / "bash").symlink_to("/bin/bash")
        self.env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                    "FIXTURE_ARCHIVE": str(self.archive), "FIXTURE_REQUEST": str(self.request),
                    "TMPDIR": str(self.tmp)}
        self.pack()

    def pack(self) -> None:
        subprocess.run(["tar", "-czf", str(self.archive), "-C", str(self.source.parent), "source"],
                       check=True)

    def install(self, sha: str = REVISION, env: dict[str, str] | None = None,
                cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["just", "--justfile", str(ROOT / "examples" / "dev-tools.just"),
             "--working-directory", str(cwd or self.project), "install-dev-tools", sha],
            env={**self.env, **(env or {})}, stdin=subprocess.DEVNULL, capture_output=True,
            text=True)

    def requests(self) -> list[list[str]]:
        """Return every GitHub CLI call so far, oldest first."""
        return [json.loads(line) for line in self.request.read_text().splitlines()]

    def commit(self) -> None:
        git(self.project, "add", ".")
        git(self.project, "commit", "--quiet", "-m", "Record installed files")

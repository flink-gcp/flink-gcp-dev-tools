// Copyright 2026 The flink-gcp authors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const skills = ['push-pr-branch', 'self-review', 'self-review-round-two', 'independent-review'];
const revision = 'a'.repeat(40);

function fixture(t) {
  const temp = mkdtempSync(join(tmpdir(), 'dev-tools-install-'));
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  const project = join(temp, 'project');
  const source = join(temp, 'archive', 'source');
  const bin = join(temp, 'bin');
  for (const dir of [project, source, bin]) mkdirSync(dir, { recursive: true });
  cpSync(join(root, 'skills'), join(source, 'skills'), { recursive: true });
  execFileSync('git', ['init', '--quiet'], { cwd: project });
  execFileSync('git', ['config', 'user.name', 'Fixture'], { cwd: project });
  execFileSync('git', ['config', 'user.email', 'fixture@example.invalid'], { cwd: project });
  execFileSync('git', ['config', 'commit.gpgsign', 'false'], { cwd: project });
  execFileSync('git', ['config', 'core.hooksPath', join(temp, 'hooks')], { cwd: project });
  execFileSync('git', ['commit', '--quiet', '--allow-empty', '-m', 'Initial fixture'], { cwd: project });
  const archive = join(temp, 'source.tar.gz');
  const request = join(temp, 'request.json');
  writeFileSync(join(bin, 'gh'), `#!/usr/bin/env node
const fs = require('node:fs');
fs.writeFileSync(process.env.FIXTURE_REQUEST, JSON.stringify(process.argv.slice(2)));
if (process.env.FIXTURE_DOWNLOAD_FAIL === '1') process.exit(1);
process.stdout.write(fs.readFileSync(process.env.FIXTURE_ARCHIVE));
`, { mode: 0o755 });
  const env = { ...process.env, PATH: `${bin}:${process.env.PATH}`, FIXTURE_ARCHIVE: archive, FIXTURE_REQUEST: request };
  const pack = () => execFileSync('tar', ['-czf', archive, '-C', dirname(source), 'source']);
  const install = (sha = revision, extraEnv = {}) => spawnSync('just', [
    '--justfile', join(root, 'examples', 'skills.just'), '--working-directory', project, 'install-skills', sha,
  ], { env: { ...env, ...extraEnv }, encoding: 'utf8' });
  const commit = () => {
    execFileSync('git', ['add', '.'], { cwd: project });
    execFileSync('git', ['commit', '--quiet', '-m', 'Record installed skills'], { cwd: project });
  };
  pack();
  return { project, source, bin, request, pack, install, commit };
}

test('installs the selected revision, including skill resources, and preserves unrelated skills', (t) => {
  const f = fixture(t);
  const resource = join(f.source, 'skills', 'self-review', 'references', 'example.md');
  mkdirSync(dirname(resource));
  writeFileSync(resource, 'A shared resource.\n');
  const unrelated = join(f.project, '.agents', 'skills', 'local', 'SKILL.md');
  mkdirSync(dirname(unrelated), { recursive: true });
  writeFileSync(unrelated, 'Local guidance.\n');
  f.pack();
  const result = f.install();
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(readFileSync(f.request)), ['api', `repos/flink-gcp/flink-gcp-dev-tools/tarball/${revision}`]);
  for (const skill of skills) {
    assert.deepEqual(readFileSync(join(f.project, '.agents', 'skills', skill, 'SKILL.md')), readFileSync(join(f.source, 'skills', skill, 'SKILL.md')));
  }
  assert.equal(readFileSync(join(f.project, '.agents', 'skills', 'self-review', 'references', 'example.md'), 'utf8'), 'A shared resource.\n');
  assert.equal(readFileSync(unrelated, 'utf8'), 'Local guidance.\n');
});

test('repeating installation with system Bash before committing is idempotent', (t) => {
  const f = fixture(t);
  symlinkSync('/bin/bash', join(f.bin, 'bash'));
  assert.equal(f.install().status, 0);
  const result = f.install();
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Installed workflow skills/);
  assert.doesNotMatch(result.stderr, /unbound variable/);
});

test('rejects a moving ref before accessing GitHub', (t) => {
  const f = fixture(t);
  const result = f.install('main');
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /full commit SHA/);
  assert.equal(existsSync(f.request), false);
});

test('a failed download preserves installed skills', (t) => {
  const f = fixture(t);
  assert.equal(f.install().status, 0);
  const before = readFileSync(join(f.project, '.agents', 'skills', 'self-review', 'SKILL.md'));
  assert.notEqual(f.install(revision, { FIXTURE_DOWNLOAD_FAIL: '1' }).status, 0);
  assert.deepEqual(readFileSync(join(f.project, '.agents', 'skills', 'self-review', 'SKILL.md')), before);
});

test('validates all requested skills before replacing any installed skill', (t) => {
  const f = fixture(t);
  assert.equal(f.install().status, 0);
  f.commit();
  const installed = join(f.project, '.agents', 'skills', 'push-pr-branch', 'SKILL.md');
  const before = readFileSync(installed);
  writeFileSync(join(f.source, 'skills', 'push-pr-branch', 'SKILL.md'), 'Changed source.\n');
  rmSync(join(f.source, 'skills', 'independent-review'), { recursive: true });
  f.pack();
  const result = f.install('b'.repeat(40));
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Invalid skill directory/);
  assert.deepEqual(readFileSync(installed), before);
});

test('preserves tracked edits inside a managed skill', (t) => {
  const f = fixture(t);
  assert.equal(f.install().status, 0);
  f.commit();
  const edited = join(f.project, '.agents', 'skills', 'self-review', 'SKILL.md');
  writeFileSync(edited, 'Local changes.\n');
  const result = f.install();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /local changes/);
  assert.equal(readFileSync(edited, 'utf8'), 'Local changes.\n');
});

test('preserves untracked resources inside a managed skill', (t) => {
  const f = fixture(t);
  assert.equal(f.install().status, 0);
  f.commit();
  const resource = join(f.project, '.agents', 'skills', 'push-pr-branch', 'local.md');
  writeFileSync(resource, 'Local resource.\n');
  const result = f.install();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /local changes/);
  assert.equal(readFileSync(resource, 'utf8'), 'Local resource.\n');
});

test('rejects installation outside a Git checkout before downloading', (t) => {
  const f = fixture(t);
  rmSync(join(f.project, '.git'), { recursive: true });
  const existing = join(f.project, '.agents', 'skills', 'self-review', 'SKILL.md');
  mkdirSync(dirname(existing), { recursive: true });
  writeFileSync(existing, 'Existing local skill.\n');
  const result = f.install();
  assert.notEqual(result.status, 0);
  assert.equal(existsSync(f.request), false);
  assert.equal(readFileSync(existing, 'utf8'), 'Existing local skill.\n');
});

test('a failed Git status preserves the installed skill', (t) => {
  const f = fixture(t);
  assert.equal(f.install().status, 0);
  f.commit();
  const installed = join(f.project, '.agents', 'skills', 'self-review', 'SKILL.md');
  const before = readFileSync(installed);
  writeFileSync(join(f.source, 'skills', 'self-review', 'SKILL.md'), 'Upstream change.\n');
  f.pack();
  writeFileSync(join(f.bin, 'git'), `#!/usr/bin/env node
const cp = require('node:child_process');
if (process.argv[2] === 'status') process.exit(1);
const result = cp.spawnSync('git', process.argv.slice(2), { stdio: 'inherit', env: { ...process.env, PATH: process.env.FIXTURE_BASE_PATH } });
process.exit(result.status ?? 1);
`, { mode: 0o755 });
  const result = f.install('b'.repeat(40), { FIXTURE_BASE_PATH: process.env.PATH });
  assert.notEqual(result.status, 0);
  assert.deepEqual(readFileSync(installed), before);
});

test('installs a resource update that only changes the executable bit', (t) => {
  const f = fixture(t);
  const resource = join(f.source, 'skills', 'self-review', 'example.sh');
  writeFileSync(resource, '#!/bin/sh\nexit 0\n', { mode: 0o644 });
  f.pack();
  assert.equal(f.install().status, 0);
  f.commit();
  chmodSync(resource, 0o755);
  f.pack();
  const result = f.install('b'.repeat(40));
  assert.equal(result.status, 0, result.stderr);
  assert.notEqual(statSync(join(f.project, '.agents', 'skills', 'self-review', 'example.sh')).mode & 0o111, 0);
});

test('upgrades remove obsolete resources and a prior pin restores them', (t) => {
  const f = fixture(t);
  const resource = join(f.source, 'skills', 'self-review', 'old.md');
  writeFileSync(resource, 'Old version.\n');
  f.pack();
  assert.equal(f.install().status, 0);
  f.commit();
  rmSync(resource);
  f.pack();
  assert.equal(f.install('b'.repeat(40)).status, 0);
  assert.equal(existsSync(join(f.project, '.agents', 'skills', 'self-review', 'old.md')), false);
  f.commit();
  writeFileSync(resource, 'Old version.\n');
  f.pack();
  const result = f.install(revision);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(readFileSync(join(f.project, '.agents', 'skills', 'self-review', 'old.md'), 'utf8'), 'Old version.\n');
});

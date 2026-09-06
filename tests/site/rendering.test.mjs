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
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const output = resolve(dirname(fileURLToPath(import.meta.url)), '../../examples/site/public');
const html = readFileSync(resolve(output, 'index.html'), 'utf8');

test('rendered code uses CSS classes so the shared palettes can follow the theme', () => {
  assert.match(html, /<pre\b[^>]*\bclass="chroma"/);
  assert.doesNotMatch(html, /<pre\b[^>]*\bstyle=/);
});

test('the built page loads the shared stylesheet under the consumer URL prefix', () => {
  const href = html.match(/<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"/)?.[1];
  assert.ok(href?.startsWith('/library/'), href);
  const css = readFileSync(resolve(output, href.slice('/library/'.length)), 'utf8');
  assert.match(css, /\.book-theme-toggle/);
  assert.match(css, /data-theme[=\s"']+light/);
  assert.match(css, /data-theme[=\s"']+dark/);
});

test('the built page contains one theme control and initializes it in the head', () => {
  assert.equal((html.match(/<button\b[^>]*class="book-theme-toggle"/g) ?? []).length, 1);
  const head = html.slice(html.indexOf('<head>'), html.indexOf('</head>'));
  assert.match(head, /book\.theme/);
});

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
import vm from 'node:vm';

const output = resolve(dirname(fileURLToPath(import.meta.url)), '../../examples/site/public');
const html = readFileSync(resolve(output, 'index.html'), 'utf8');

test('the generated search module waits for its index and searches the latest input', async () => {
  const src = html.match(/<script[^>]*src="([^"]*search[^"/]*\.js)"/)?.[1];
  assert.ok(src?.startsWith('/library/'), src);
  const script = resolve(output, src.slice('/library/'.length));
  const listeners = new Map();
  const queries = [];
  const nodes = [];
  const input = {
    value: '', required: false,
    addEventListener: (event, listener) => listeners.set(event, listener),
    removeEventListener: event => listeners.delete(event),
  };
  const results = {
    get firstChild() { return nodes[0]; },
    removeChild(node) { assert.equal(nodes.shift(), node); },
    appendChild(node) { nodes.push(node); },
  };
  const document = {
    querySelector: selector => selector === '#book-search-input' ? input : results,
    addEventListener() {},
    createElement() {
      const anchor = {}, small = {};
      return {firstChild: {querySelector: tag => tag === 'a' ? anchor : small}};
    },
  };
  let resolveIndex;
  const download = new Promise(resolve => { resolveIndex = resolve; });
  const context = vm.createContext({document, window: {}, fetch: () => download});
  const search = new vm.SourceTextModule(readFileSync(script, 'utf8'), {context});
  const fuse = new vm.SyntheticModule(['default'], function () {
    this.setExport('default', class {
      search(query) {
        queries.push(query);
        return [{item: {href: '/page/', title: query, section: 'Documentation'}}];
      }
    });
  }, {context});
  await search.link(specifier => {
    assert(specifier.endsWith('/fuse.min.mjs'));
    return fuse;
  });
  await search.evaluate();
  listeners.get('focus')();
  assert.equal(input.required, true);
  input.value = 'first';
  listeners.get('keyup')();
  input.value = 'latest';
  listeners.get('keyup')();
  assert.deepEqual(queries, []);
  assert.equal(nodes.length, 0);
  resolveIndex({json: async () => []});
  await new Promise(setImmediate);
  assert.equal(input.required, false);
  assert.deepEqual(queries, ['latest']);
  assert.equal(nodes.length, 1);
  assert.equal(nodes[0].querySelector('a').textContent, 'latest');
  input.value = 'next';
  listeners.get('keyup')();
  assert.deepEqual(queries, ['latest', 'next']);
  assert.equal(nodes.length, 1);
  input.value = '';
  listeners.get('keyup')();
  assert.equal(nodes.length, 0);
});

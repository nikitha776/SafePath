const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
// Run the actual API module without loading React Native or native map bindings.
const compiled = ts.transpileModule(fs.readFileSync('src/lib/api.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
function load(fetch) {
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: () => ({ API_BASE: 'http://localhost:8000' }), fetch, AbortController, setTimeout, clearTimeout, Error, TypeError });
  return exports;
}
test('route bounds include every disconnected leg without joining them', () => {
  const { routeBounds } = load();
  const bounds = routeBounds({ geometry: { type: 'MultiLineString', coordinates: [[[80.61,16.51],[80.62,16.52]],[[80.65,16.49],[80.66,16.50]]] } });
  assert.equal(JSON.stringify(bounds), '[80.61,16.49,80.66,16.52]');
});
test('API sends route payload to our backend without provider credentials', async () => {
  const { api, post } = load(async (url, options) => {
    assert.equal(url, 'http://localhost:8000/api/routes');
    assert.deepEqual(JSON.parse(options.body), { start: { lat:16.52,lon:80.62 } });
    assert.equal(JSON.stringify(options.headers).includes('apiKey'), false);
    return { ok: true, json: async () => ({ features: [] }) };
  });
  const result = await api('/api/routes', post({ start:{lat:16.52,lon:80.62} }));
  assert.equal(result.features.length, 0);
});
test('API preserves useful provider failure messages', async () => {
  const { api } = load(async () => ({ ok: false, json: async () => ({ detail: 'No walking route was found.' }) }));
  await assert.rejects(api('/api/routes'), /No walking route was found/);
});
test('canceling a stale request aborts the underlying fetch', async () => {
  let aborted = false;
  const { api } = load((url, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener('abort', () => { aborted = true; reject(new Error('aborted')); });
  }));
  const controller = new AbortController();
  const result = api('/api/search?q=station', {}, controller.signal);
  controller.abort();
  await assert.rejects(result, /aborted/);
  assert.equal(aborted, true);
});
test('network failures explain backend connection recovery', async () => {
  const { api } = load(async () => { throw new TypeError('Network request failed'); });
  await assert.rejects(api('/api/health'), /backend address in App info/);
});

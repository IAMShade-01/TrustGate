const { test } = require('node:test');
const assert = require('node:assert/strict');
const { command, makeQueue } = require('./winget.cjs');

test('commands use exact package IDs, optional versions and the winget source', () => {
  const upgrade = command({ action: 'upgrade', id: 'Example.Package', version: '2.0.1' });
  assert.deepEqual(upgrade.slice(0, 6), ['upgrade', '--id', 'Example.Package', '--exact', '--source', 'winget']);
  assert.deepEqual(upgrade.slice(-2), ['--version', '2.0.1']);
  assert.ok(command({ action: 'versions', id: 'Example.Package' }).includes('--versions'));
  assert.ok(command({ action: 'search', query: ' Example Tools ' }).includes('Example Tools'));
  for (const input of [
    { action: 'install', id: '--override' },
    { action: 'upgrade', id: 'Example.Package', version: '2.0 & whoami' },
    { action: 'search', query: '--source example' },
    { action: 'uninstall', id: 'Example.Package', version: '2.0' },
  ]) assert.throws(() => command(input));
});

test('queue executes one job at a time and records failures without blocking the next job', async () => {
  const completions = [];
  const events = [];
  const queue = makeQueue(() => new Promise(resolve => completions.push(resolve)), event => events.push(event));
  queue.add({ action: 'install', id: 'Example.One' });
  queue.add({ action: 'uninstall', id: 'Example.Two' });
  assert.deepEqual(queue.list().map(job => job.status), ['queued', 'running']);
  assert.equal(completions.length, 1);
  completions[0]({ code: 9, output: 'Installer error' });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(completions.length, 2);
  completions[1]({ code: 0, output: 'OK' });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(queue.pending(), 0);
  assert.deepEqual(queue.list().map(job => job.status), ['succeeded', 'failed']);
  assert.deepEqual(events.filter(item => item.event === 'winget.finished').map(item => item.status), ['failed', 'succeeded']);
});

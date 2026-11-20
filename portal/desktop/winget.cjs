const { spawn } = require('node:child_process');
const path = require('node:path');
const { randomUUID } = require('node:crypto');

const source = ['--source', 'winget', '--disable-interactivity', '--accept-source-agreements'];
const packageId = /^[a-z0-9][a-z0-9._+-]{0,255}$/i;
const version = /^[a-z0-9][a-z0-9._+~-]{0,127}$/i;
const token = (value, pattern) => typeof value === 'string' && value === value.trim() && pattern.test(value);

function command(input) {
  if (!input || typeof input !== 'object') throw new Error('Select a winget action.');
  const { action, id, query } = input;
  const selectedVersion = input.version === undefined || input.version === '' ? undefined : input.version;
  if (action === 'search') {
    if (typeof query !== 'string' || !token(query.trim(), /^[\p{L}\p{N}][\p{L}\p{N} ._+()-]{0,79}$/u))
      throw new Error('Enter a search term starting with a letter or number (up to 80 characters).');
    return ['search', '--query', query.trim(), '--count', '30', ...source];
  }
  if (!['versions', 'install', 'upgrade', 'uninstall'].includes(action) || !token(id, packageId))
    throw new Error('Enter an exact package ID and select a supported action.');
  if (selectedVersion !== undefined && (!['install', 'upgrade'].includes(action) || !token(selectedVersion, version)))
    throw new Error('Enter a valid version for install or upgrade.');
  const target = ['--id', id, '--exact', ...source];
  if (action === 'versions') return ['show', ...target, '--versions'];
  if (action === 'uninstall') return ['uninstall', ...target, '--silent'];
  return [action, ...target, '--silent', '--accept-package-agreements',
    ...(selectedVersion ? ['--version', selectedVersion] : [])];
}

function runWinget(args, timeout) {
  if (process.platform !== 'win32' || !process.env.LOCALAPPDATA)
    return Promise.reject(new Error('Windows App Installer is required.'));
  const executable = path.join(process.env.LOCALAPPDATA, 'Microsoft', 'WindowsApps', 'winget.exe');
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, { shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    let timedOut = false;
    const timer = timeout && setTimeout(() => { timedOut = true; child.kill(); }, timeout);
    for (const stream of [child.stdout, child.stderr]) {
      stream.setEncoding('utf8');
      stream.on('data', chunk => { output = (output + chunk).slice(-20000); });
    }
    child.once('error', error => reject(new Error(
      error.code === 'ENOENT' ? 'winget was not found. Install or enable Microsoft App Installer.' : `Could not launch winget: ${error.message}`,
    )));
    child.once('close', (code) => {
      if (timer) clearTimeout(timer);
      if (timedOut) reject(new Error('winget timed out during the read-only request.'));
      else resolve({
        code,
        output: output.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, '').replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '').trim(),
      });
    });
  });
}

function makeQueue(run, log) {
  const jobs = [];
  let running = false;
  const pending = () => jobs.filter(job => ['queued', 'running'].includes(job.status)).length;
  async function drain() {
    if (running) return;
    running = true;
    try {
      for (let job; (job = jobs.find(item => item.status === 'queued'));) {
        job.status = 'running';
        try {
          const result = await run(job.args);
          job.status = result.code === 0 ? 'succeeded' : 'failed';
          job.output = result.output || (result.code === 0 ? 'winget exited successfully.' : 'winget did not report success.');
          job.code = result.code;
        } catch (error) {
          job.status = 'failed';
          job.output = error.message;
        }
        log({ event: 'winget.finished', id: job.id, action: job.action, packageId: job.packageId, status: job.status, code: job.code });
      }
    } finally { running = false; }
  }
  return {
    pending,
    add(input) {
      if (!['install', 'upgrade', 'uninstall'].includes(input?.action)) throw new Error('Select a deployment action.');
      const args = command(input);
      if (pending() >= 10) throw new Error('The deployment queue is full (10 pending operations).');
      if (jobs.length >= 50) jobs.shift(); // FIFO means the oldest job is already complete at this limit.
      const job = { id: randomUUID(), action: input.action, packageId: input.id, version: input.version || '', args, status: 'queued' };
      jobs.push(job);
      log({ event: 'winget.queued', id: job.id, action: job.action, packageId: job.packageId, version: job.version });
      void drain();
    },
    list: () => jobs.map(({ args, ...job }) => ({ ...job })).reverse(),
  };
}

module.exports = { command, runWinget, makeQueue };

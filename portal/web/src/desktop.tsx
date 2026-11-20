import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Action = 'install' | 'upgrade' | 'uninstall';
type Job = { id: string; action: Action; packageId: string; version: string; status: string; code?: number; output?: string };
type DesktopInfo = { version: string; updateState: string; updatesEnabled: boolean };
type Theme = 'system' | 'dark' | 'light';
declare global {
  interface Window {
    trustgate: {
      info(): Promise<DesktopInfo>;
      openPortal(): Promise<void>;
      openLogs(): Promise<void>;
      theme(value: Theme): Promise<void>;
      updates(): Promise<void>;
      lookup(input: { action: 'search'; query: string } | { action: 'versions'; id: string }): Promise<{ code: number | null; output: string }>;
      enqueue(input: { action: Action; id: string; version: string }): Promise<boolean>;
      jobs(): Promise<Job[]>;
    };
  }
}

const bridge = window.trustgate;
const pages = ['Dashboard', 'Devices', 'Software Deployment', 'Provisioning', 'Computer Rename',
  'Domain Join', 'BitLocker', 'Drivers', 'Printers', 'Compliance', 'Administration', 'Settings'] as const;
type Page = typeof pages[number];
const describeError = (reason: unknown) => reason instanceof Error ? reason.message : String(reason);

function Winget({ jobs }: { jobs: Job[] }) {
  const [query, setQuery] = useState('');
  const [id, setId] = useState('');
  const [version, setVersion] = useState('');
  const [versions, setVersions] = useState<string[]>([]);
  const [action, setAction] = useState<Action>('install');
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');

  async function lookup(kind: 'search' | 'versions') {
    setBusy(kind === 'search' ? 'Searching...' : 'Loading versions...');
    setOutput(''); setError(''); setNotice('');
    if (kind === 'versions') setVersions([]);
    try {
      const result = await bridge.lookup(kind === 'search' ? { action: kind, query } : { action: kind, id: id.trim() });
      setOutput(result.output);
      if (result.code !== 0) setError(`winget did not complete successfully (exit ${result.code ?? 'unknown'}).`);
      else if (kind === 'versions') {
        const lines = result.output.split(/\r?\n/).map(line => line.trim());
        const separator = lines.findIndex(line => /^-{3,}$/.test(line));
        if (separator >= 0)
          setVersions([...new Set(lines.slice(separator + 1).filter(line => /^[a-z0-9][a-z0-9._+~-]{0,127}$/i.test(line)))]);
      }
    } catch (reason) { setError(describeError(reason)); }
    finally { setBusy(''); }
  }

  async function deploy(event: FormEvent) {
    event.preventDefault();
    setBusy('Awaiting confirmation...'); setError(''); setNotice('');
    try {
      const accepted = await bridge.enqueue({ action, id: id.trim(), version: action === 'uninstall' ? '' : version.trim() });
      setNotice(accepted ? 'Added to the local queue.' : 'No software change was queued.');
    } catch (reason) { setError(describeError(reason)); }
    finally { setBusy(''); }
  }

  return <>
    <p>Run winget on this PC. These jobs are separate from tenant requests and are not sent to the server.</p>
    <details className="panel" open>
      <summary>Find a package</summary>
      <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); void lookup('search'); }}>
        <label className="min-w-52 flex-1">Package name or ID
          <input required value={query} maxLength={80} onChange={event => setQuery(event.target.value)} />
        </label>
        <button disabled={!!busy || !query.trim()}>Search winget</button>
      </form>
    </details>
    <details className="panel" open>
      <summary>Deploy an exact package</summary>
      <form onSubmit={deploy} className="mt-3 grid gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-52 flex-1">Exact package ID
            <input required value={id} onChange={event => { setId(event.target.value); setVersions([]); setVersion(''); }} placeholder="Microsoft.PowerToys" />
          </label>
          <button type="button" disabled={!!busy || !id.trim()} onClick={() => void lookup('versions')}>List versions</button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label>Action<select value={action} onChange={event => {
            const value = event.target.value;
            if (value === 'install' || value === 'upgrade' || value === 'uninstall') setAction(value);
          }}>
            <option value="install">Install</option><option value="upgrade">Upgrade</option><option value="uninstall">Uninstall</option>
          </select></label>
          {action !== 'uninstall' && <label>Version (optional)
            <input value={version} list="available-versions" onChange={event => setVersion(event.target.value)} placeholder="Default winget selection" />
            <datalist id="available-versions">{versions.map(value => <option key={value} value={value} />)}</datalist>
          </label>}
        </div>
        <button className="justify-self-start" disabled={!!busy || !id.trim()}>Review and queue</button>
      </form>
    </details>
    {(busy || notice) && <p role="status">{busy || notice}</p>}
    {error && <p className="panel border-red-500" role="alert">{error}</p>}
    {output && <pre className="panel max-h-56 overflow-auto text-xs">{output}</pre>}
    <details className="panel" open>
      <summary>Local deployment queue</summary>
      {jobs.length === 0 && <p className="mt-3">No jobs in this session.</p>}
      {jobs.map(job => <details className="mt-3 border-t border-slate-400/40 pt-2" key={job.id}>
        <summary>{job.action} {job.packageId} {job.version} — {job.status}{job.code != null && job.code !== 0 ? ` (${job.code})` : ''}</summary>
        {job.output && <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs">{job.output}</pre>}
      </details>)}
    </details>
  </>;
}

function RenamePreview() {
  const [name, setName] = useState('');
  const candidate = name.trim();
  const valid = /^(?=.*[a-z])[a-z0-9](?:[a-z0-9-]{0,13}[a-z0-9])?$/i.test(candidate);
  return <section className="panel">
    <label>Proposed computer name<input value={name} onChange={event => setName(event.target.value)} placeholder="LAB-DEVICE-01" /></label>
    <p className="mt-3" role="status">{valid ? `Name preview: ${candidate.toUpperCase()}` :
      'Use 1–15 ASCII letters, numbers, or hyphens, including at least one letter. Start and end with a letter or number.'}</p>
    <p className="mt-2">Preview only. This does not rename the computer or check directory availability.</p>
  </section>;
}

function App() {
  const [page, setPage] = useState<Page>('Dashboard');
  const [info, setInfo] = useState<DesktopInfo>();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [theme, setTheme] = useState<Theme>('system');
  const [systemDark, setSystemDark] = useState(() => matchMedia('(prefers-color-scheme: dark)').matches);
  const dark = theme === 'dark' || (theme === 'system' && systemDark);
  useEffect(() => {
    const preference = matchMedia('(prefers-color-scheme: dark)');
    const change = () => setSystemDark(preference.matches);
    preference.addEventListener('change', change);
    return () => preference.removeEventListener('change', change);
  }, []);
  useEffect(() => {
    let active = true;
    let pending = false;
    async function refresh() {
      if (pending) return;
      pending = true;
      try {
        const [info, jobs] = await Promise.all([bridge.info(), bridge.jobs()]);
        if (active) { setInfo(info); setJobs(jobs); setLoadError(''); }
      } catch (reason) { if (active) setLoadError(describeError(reason)); }
      finally { pending = false; }
    }
    void refresh();
    const timer = setInterval(() => void refresh(), 1000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  async function run(operation: () => Promise<void>) {
    setError('');
    try { await operation(); }
    catch (reason) { setError(describeError(reason)); }
  }
  const openPortal = () => void run(bridge.openPortal);
  return <div className={dark ? 'dark' : ''}>
    <div className="grid h-screen grid-cols-[12rem_minmax(0,1fr)] overflow-hidden bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-slate-100">
      <aside className="overflow-auto border-r border-slate-400/30 bg-slate-200 p-3 dark:bg-slate-900">
        <strong className="block p-3 text-lg">TrustGate</strong>
        <nav className="grid gap-1" aria-label="TrustGate modules">
          {pages.map(item => <button key={item} aria-current={page === item ? 'page' : undefined}
            className={page === item ? 'text-left' : 'bg-transparent text-left text-slate-800 hover:bg-slate-300 dark:text-slate-100 dark:hover:bg-slate-800'}
            onClick={() => { setError(''); setPage(item); }}>{item}</button>)}
        </nav>
      </aside>
      <main className="grid content-start gap-4 overflow-auto p-5">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold">{page}</h1>
          <button onClick={openPortal}>Open enterprise portal</button>
        </header>
        {(error || loadError) && <p className="panel border-red-500" role="alert">{error || loadError}</p>}
        {page === 'Dashboard' && <div className="grid gap-3 lg:grid-cols-3">
          <p className="panel">Active jobs <strong>{jobs.filter(job => ['queued', 'running'].includes(job.status)).length}</strong></p>
          <p className="panel">Succeeded <strong>{jobs.filter(job => job.status === 'succeeded').length}</strong></p>
          <p className="panel">Failed <strong>{jobs.filter(job => job.status === 'failed').length}</strong></p>
        </div>}
        {page === 'Software Deployment' && <Winget jobs={jobs} />}
        {page === 'Computer Rename' && <RenamePreview />}
        {page === 'Provisioning' && <section className="panel"><p>Plan a local computer name before provisioning.</p>
          <button className="mt-3" onClick={() => setPage('Computer Rename')}>Preview computer name</button></section>}
        {page === 'Settings' && <section className="panel grid gap-3">
          <label>Appearance<select value={theme} onChange={event => {
            const value = event.target.value;
            if (value === 'system' || value === 'dark' || value === 'light')
              void run(async () => { await bridge.theme(value); setTheme(value); });
          }}>
            <option value="system">Match Windows</option><option value="dark">Dark</option><option value="light">Light</option>
          </select></label>
          <p>Desktop version: {info?.version ?? 'Loading'}</p>
          <p role="status">{info?.updateState}</p>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => void run(bridge.openLogs)}>Open logs</button>
            <button disabled={!info?.updatesEnabled || info.updateState.startsWith('Checking') ||
              info.updateState.startsWith('Downloading')} onClick={() => void run(bridge.updates)}>
              {info?.updateState.startsWith('Update downloaded') ? 'Restart to update' : 'Check for updates'}
            </button>
          </div>
          <p>Closing the window keeps TrustGate in the system tray. Quit from the tray menu.</p>
        </section>}
        {page === 'Devices' || page === 'Administration' ? <section className="panel">
          <p>Use the enterprise portal for tenant inventory and authenticated workflows. Local winget does not use tenant roles.</p>
        </section> : null}
        {(['Domain Join', 'BitLocker', 'Drivers', 'Printers', 'Compliance'] as readonly Page[]).includes(page) &&
          <p className="panel">{page} has no execution integration in this release.</p>}
      </main>
    </div>
  </div>;
}

const root = document.getElementById('root');
if (!root) throw new Error('Missing desktop root element.');
createRoot(root).render(<App />);

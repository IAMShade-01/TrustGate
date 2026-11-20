import { InteractionRequiredAuthError, PublicClientApplication } from '@azure/msal-browser';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { createRoot } from 'react-dom/client';
import { api, filterCatalog } from './api';
import type { Deployment, Device, Session, Software } from './api';
import './styles.css';

const { VITE_ENTRA_TENANT_ID: tenant, VITE_ENTRA_SPA_CLIENT_ID: clientId,
  VITE_ENTRA_API_CLIENT_ID: apiId } = import.meta.env;
const guid = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
const identity = [tenant, clientId, apiId].every(value => typeof value === 'string' && guid.test(value))
  ? new PublicClientApplication({
      auth: { clientId, authority: `https://login.microsoftonline.com/${tenant}`, redirectUri: location.origin },
      cache: { cacheLocation: 'memoryStorage' },
    })
  : null;
const scope = [`api://${apiId}/Deployments.Access`];

type PortalData = { session: Session; devices: Device[]; catalog: Software[]; history: Deployment[] };

async function token() {
  if (!identity) throw new Error('Entra ID is not configured.');
  const account = identity.getActiveAccount();
  if (!account) throw new Error('Sign in before using the portal.');
  try {
    return (await identity.acquireTokenSilent({ account, scopes: scope })).accessToken;
  } catch (error) {
    if (!(error instanceof InteractionRequiredAuthError)) throw error;
    return (await identity.acquireTokenPopup({ account, scopes: scope })).accessToken;
  }
}

function App() {
  const [data, setData] = useState<PortalData>();
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [softwareId, setSoftwareId] = useState('');
  const [dark, setDark] = useState(() => matchMedia('(prefers-color-scheme: dark)').matches);
  const reportError = (reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unexpected portal error.');

  async function signIn() {
    if (!identity || busy) return;
    setBusy('Signing in...');
    setError('');
    try {
      await identity.initialize();
      const { account } = await identity.loginPopup({ scopes: scope });
      identity.setActiveAccount(account);
      const access = await token();
      const [session, devices, catalog, history] = await Promise.all([
        api<Session>('session', access), api<Device[]>('devices', access),
        api<Software[]>('catalog', access), api<Deployment[]>('deployments', access),
      ]);
      setData({ session, devices, catalog, history });
    } catch (reason) { reportError(reason); }
    finally { setBusy(''); }
  }

  async function signOut() {
    if (!identity || busy) return;
    setBusy('Signing out...');
    setData(undefined);
    setDeviceId(''); setSoftwareId(''); setQuery(''); setNotice(''); setError('');
    try { await identity.logoutPopup({ account: identity.getActiveAccount(), mainWindowRedirectUri: location.origin }); }
    catch (reason) { reportError(reason); }
    finally { identity.setActiveAccount(null); setBusy(''); }
  }

  async function record(event: FormEvent) {
    event.preventDefault();
    if (!data?.session.canRequest || !deviceId || !softwareId || busy) return;
    setBusy('Recording request...');
    setError(''); setNotice('');
    try {
      const row = await api<Deployment>('deployments', await token(), { deviceId, softwareId });
      setData({ ...data, history: [row, ...data.history].slice(0, 100) });
      setNotice('Request recorded and audited. No software was deployed.');
    } catch (reason) { reportError(reason); }
    finally { setBusy(''); }
  }

  const catalog = filterCatalog(data?.catalog ?? [], query);
  return <div className={dark ? 'dark' : ''}>
    <div className="min-h-screen bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-slate-100">
      <header className="border-b border-slate-400/30">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 p-5">
          <strong>TrustGate Enterprise</strong>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setDark(!dark)}>{dark ? 'Light mode' : 'Dark mode'}</button>
            {data ? <button disabled={!!busy} onClick={signOut}>Sign out</button> :
              <button disabled={!identity || !!busy} onClick={signIn}>Sign in with Microsoft</button>}
          </div>
        </div>
      </header>
      <main className="mx-auto grid max-w-6xl gap-5 p-5">
        <div>
          <h1 className="text-3xl font-semibold">Software Deployment</h1>
          <p>Browse your tenant catalog, record deployment requests, and review request history.</p>
        </div>
        {error && <p className="panel border-red-500" role="alert">{error}</p>}
        {(busy || notice) && <p role="status">{busy || notice}</p>}
        {!identity && <p className="panel" role="status">Entra ID is not configured. Set the portal's Entra environment values before signing in.</p>}
        {data && <>
          <nav aria-label="Deployment sections" className="flex flex-wrap gap-4">
            <a href="#request">Request</a><a href="#history">History</a><a href="#integrations">Integrations</a>
          </nav>
          <div className="grid gap-3 sm:grid-cols-3">
            <p className="panel">Devices shown <strong>{data.devices.length}</strong></p>
            <p className="panel">Catalog entries shown <strong>{data.catalog.length}</strong></p>
            <p className="panel">Recent requests <strong>{data.history.length}</strong></p>
          </div>
          <details className="panel" id="request" open>
            <summary>New deployment request</summary>
            {!data.session.canRequest && <p className="mt-3">Reader access: you can browse but cannot record requests.</p>}
            <form onSubmit={record} className="mt-4 grid gap-3">
              <label>Filter catalog <input value={query} onChange={event => {
                setQuery(event.target.value); setSoftwareId('');
              }} placeholder="Name, version, or method" /></label>
              <label>Package and version <select required value={softwareId} onChange={event => setSoftwareId(event.target.value)}>
                <option value="">{catalog.length ? 'Select a package' : 'No matching packages'}</option>
                {catalog.map(item => <option key={item.id} value={item.id}>{item.name} {item.version} ({item.method})</option>)}
              </select></label>
              <label>Target device <select required value={deviceId} onChange={event => setDeviceId(event.target.value)}>
                <option value="">{data.devices.length ? 'Select a device' : 'No devices available'}</option>
                {data.devices.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select></label>
              <button className="justify-self-start" disabled={!!busy || !data.session.canRequest || !deviceId || !softwareId}>
                Record request
              </button>
              <p>Recording does not execute software on a device.</p>
            </form>
          </details>
          <details className="panel" id="history" open>
            <summary>Recent request history</summary>
            {data.history.length === 0 ? <p className="mt-3">No requests recorded.</p> :
              <div className="mt-3 overflow-x-auto"><table className="w-full text-left">
                <thead><tr>{['Package', 'Device', 'Status', 'Requested'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
                <tbody>{data.history.map(row => <tr key={row.id}>
                  <td>{row.softwareName} {row.version}</td><td>{row.deviceName}</td>
                  <td>Recorded only</td><td>{new Date(row.requestedAt).toLocaleString()}</td>
                </tr>)}</tbody>
              </table></div>}
          </details>
        </>}
        <details className="panel" id="integrations">
          <summary>Integration availability</summary>
          <p className="mt-3">Intune, SCCM/MECM, Active Directory, Microsoft Graph, winget, Chocolatey, and PowerShell execution are not connected in this portal. No request is queued for execution.</p>
        </details>
      </main>
    </div>
  </div>;
}

const root = document.getElementById('root');
if (!root) throw new Error('Missing portal root element.');
createRoot(root).render(<App />);

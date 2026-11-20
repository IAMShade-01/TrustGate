export type Device = { id: string; name: string };
export type Software = { id: string; name: string; version: string; method: string };
export type Deployment = {
  id: string; deviceName: string; softwareName: string; version: string;
  status: 'RecordedOnly'; requestedAt: string;
};
export type Session = { tenantId: string; canRequest: boolean };

export function filterCatalog(catalog: Software[], query: string) {
  const search = query.trim().toLowerCase();
  return catalog.filter(item => `${item.name} ${item.version} ${item.method}`.toLowerCase().includes(search));
}

export async function api<T>(path: string, accessToken: string, input?: object): Promise<T> {
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  if (input) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api/${path}`, {
    headers, method: input ? 'POST' : 'GET', body: input ? JSON.stringify(input) : undefined,
    cache: 'no-store', redirect: 'error',
  });
  if (response.status === 401) throw new Error('Your session is not authorized. Sign out and try again.');
  if (response.status === 403) throw new Error('You do not have the required TrustGate role.');
  if (response.status === 404) throw new Error('The selected device or package could not be found.');
  if (!response.ok) throw new Error(`The request failed (${response.status}).`);
  return response.json();
}

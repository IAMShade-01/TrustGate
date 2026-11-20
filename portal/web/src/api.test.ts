import { expect, test, vi } from 'vitest';
import { api, filterCatalog } from './api';

test('filters catalog by package, method, or version without case sensitivity', () => {
  const catalog = [
    { id: '1', name: 'Firefox', version: '100', method: 'winget' },
    { id: '2', name: 'Example', version: '200', method: 'manual' },
  ];
  expect(filterCatalog(catalog, '  FIREFOX ')).toEqual([catalog[0]]);
  expect(filterCatalog(catalog, '200')).toEqual([catalog[1]]);
  expect(filterCatalog(catalog, 'absent')).toEqual([]);
});

test('does not present a forbidden deployment request as successful', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 403 })));
  try {
    await expect(api('deployments', 'test-token', { deviceId: '1', softwareId: '2' }))
      .rejects.toThrow('required TrustGate role');
  } finally { vi.unstubAllGlobals(); }
});

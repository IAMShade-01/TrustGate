const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('trustgate', {
  info: () => ipcRenderer.invoke('desktop:info'),
  openPortal: () => ipcRenderer.invoke('desktop:open-portal'),
  openLogs: () => ipcRenderer.invoke('desktop:open-logs'),
  theme: value => ipcRenderer.invoke('desktop:theme', value),
  updates: () => ipcRenderer.invoke('desktop:updates'),
  lookup: input => ipcRenderer.invoke('winget:read', input),
  enqueue: input => ipcRenderer.invoke('winget:queue', input),
  jobs: () => ipcRenderer.invoke('winget:jobs'),
});

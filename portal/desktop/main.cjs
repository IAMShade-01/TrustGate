const { app, BrowserWindow, dialog, ipcMain, Menu, nativeTheme, net, protocol, shell, Tray } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { command, runWinget, makeQueue } = require('./winget.cjs');

const page = 'trustgate://desktop/desktop.html';
protocol.registerSchemesAsPrivileged([{ scheme: 'trustgate', privileges: { standard: true, secure: true } }]);
let window;
let tray;
let quitting = false;
let readBusy = false;
let confirming = false;
let updater;
let updateState = 'Automatic updates are not configured for this build.';
const icon = name => path.join(__dirname, 'icons', name);
const queue = makeQueue(runWinget, log);

function log(entry) {
  const file = path.join(app.getPath('logs'), 'desktop.jsonl');
  try {
    if (fs.existsSync(file) && fs.statSync(file).size >= 1024 * 1024)
      fs.renameSync(file, `${file}.1`);
    fs.appendFileSync(file, JSON.stringify({ at: new Date().toISOString(), ...entry }) + '\n');
  } catch (error) {
    console.error('TrustGate could not write the desktop log:', error.message);
  }
}

function show() {
  if (window?.isMinimized()) window.restore();
  window?.show();
  window?.focus();
}

function handle(channel, handler) {
  ipcMain.handle(channel, (event, ...args) => {
    if (event.sender !== window?.webContents || event.senderFrame !== window.webContents.mainFrame
      || event.senderFrame.url !== page)
      throw new Error('Untrusted desktop IPC sender.');
    return handler(...args);
  });
}

function portalUrl() {
  const raw = process.env.TRUSTGATE_PORTAL_URL;
  if (!raw) throw new Error('Set TRUSTGATE_PORTAL_URL to your hosted .NET portal URL and restart the app.');
  const url = new URL(raw);
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.username || url.password || !(url.protocol === 'https:' || (loopback && url.protocol === 'http:')))
    throw new Error('Use an HTTPS portal URL without credentials (HTTP is allowed for local development only).');
  return url.href;
}

function configureUpdates() {
  if (!app.isPackaged || !fs.existsSync(path.join(process.resourcesPath, 'app-update.yml'))) return;
  updater = require('electron-updater').autoUpdater;
  updater.autoInstallOnAppQuit = false;
  updater.allowDowngrade = false;
  updater.logger = null;
  updateState = 'Ready to check for signed updates.';
  updater.on('checking-for-update', () => { updateState = 'Checking for updates...'; });
  updater.on('update-available', () => { updateState = 'Downloading signed update...'; });
  updater.on('update-not-available', () => { updateState = 'No update available.'; });
  updater.on('update-downloaded', () => { updateState = 'Update downloaded. Ready to restart.'; });
  updater.on('error', error => {
    updateState = 'Update failed. Ask your administrator to check the release feed and signing configuration.';
    log({ event: 'update.error', code: error.code ?? 'unknown' });
  });
}

function setup() {
  app.setAppLogsPath();
  const uiRoot = path.join(__dirname, 'ui');
  protocol.handle('trustgate', request => {
    const url = new URL(request.url);
    if (url.hostname !== 'desktop' || !/^\/(?:desktop\.html|assets\/[\w.-]+)$/.test(url.pathname))
      return new Response('Not found', { status: 404 });
    return net.fetch(pathToFileURL(path.join(uiRoot, url.pathname.slice(1))).href);
  });

  window = new BrowserWindow({
    width: 1200, height: 800, minWidth: 740, minHeight: 550, title: 'TrustGate Enterprise',
    icon: icon('trustgate.ico'), backgroundColor: '#0f172a',
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), sandbox: true, contextIsolation: true, nodeIntegration: false },
  });
  window.removeMenu();
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-frame-navigate', event => event.preventDefault());
  window.webContents.on('will-attach-webview', event => event.preventDefault());
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  window.webContents.session.setPermissionCheckHandler(() => false);
  window.on('close', event => {
    if (!quitting && tray) {
      event.preventDefault();
      window.hide();
    }
  });

  tray = new Tray(icon('trustgate.ico'));
  tray.setToolTip('TrustGate Enterprise');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Open TrustGate', click: show },
    { label: 'Quit TrustGate', click: () => app.quit() },
  ]));
  tray.on('double-click', show);
  configureUpdates();
  handle('desktop:info', () => ({ version: app.getVersion(), updateState, updatesEnabled: Boolean(updater) }));
  handle('desktop:open-portal', () => shell.openExternal(portalUrl()));
  handle('desktop:open-logs', async () => {
    const error = await shell.openPath(app.getPath('logs'));
    if (error) throw new Error(error);
  });
  handle('desktop:theme', value => {
    if (!['system', 'dark', 'light'].includes(value)) throw new Error('Unsupported theme.');
    nativeTheme.themeSource = value;
  });
  handle('desktop:updates', async () => {
    if (!updater) throw new Error(updateState);
    if (updateState === 'Update downloaded. Ready to restart.') {
      if (queue.pending()) throw new Error('Wait for the winget queue to finish before restarting.');
      quitting = true;
      updater.quitAndInstall();
    } else await updater.checkForUpdates();
  });
  handle('winget:jobs', () => queue.list());
  handle('winget:read', async input => {
    if (!['search', 'versions'].includes(input?.action)) throw new Error('Unsupported read-only action.');
    if (readBusy) throw new Error('A winget lookup is already running.');
    const args = command(input);
    readBusy = true;
    try { return await runWinget(args, 45000); }
    finally { readBusy = false; }
  });
  handle('winget:queue', async input => {
    if (!['install', 'upgrade', 'uninstall'].includes(input?.action)) throw new Error('Unsupported deployment action.');
    command(input);
    if (confirming) throw new Error('A confirmation is already open.');
    confirming = true;
    try {
      const { response } = await dialog.showMessageBox(window, {
        type: 'warning', title: 'Confirm local software change',
        message: `${input.action.toUpperCase()} ${input.id}${input.version ? ` (${input.version})` : ''}?`,
        detail: 'Runs on this PC from the configured winget source and accepts applicable agreements. The installer may request Windows administrator approval. Check that you trust this package before proceeding.',
        buttons: ['Cancel', 'Add to queue'], defaultId: 0, cancelId: 0, noLink: true,
      });
      if (response !== 1) return false;
      queue.add(input);
      return true;
    } finally { confirming = false; }
  });
  void window.loadURL(page).catch(error => {
    log({ event: 'window.load.error', code: error.code ?? 'unknown' });
    dialog.showErrorBox('TrustGate could not start', error.message);
    app.exit(1);
  });
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.setAppUserModelId('com.trustgate.enterprise');
  app.on('second-instance', show);
  app.on('before-quit', event => {
    if (queue.pending()) {
      event.preventDefault();
      show();
      dialog.showMessageBoxSync(window, { type: 'info', message: 'Let the winget queue finish before quitting.' });
    } else quitting = true;
  });
  app.whenReady().then(setup).catch(error => {
    dialog.showErrorBox('TrustGate could not start', error.message);
    app.exit(1);
  });
}

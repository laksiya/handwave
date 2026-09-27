const { app, BrowserWindow, Menu, Tray, globalShortcut, nativeImage, session, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const { createServer } = require('node:http');
const { readFile } = require('node:fs/promises');
const path = require('node:path');

const WEB_PORT = 4174;
const appRoot = path.join(__dirname, '..');
const webRoot = path.join(appRoot, 'outputs', 'handwave-poc');
let window;
let tray;
let helper;
let webServer;
let quitting = false;
const hasSingleInstanceLock = app.requestSingleInstanceLock();

function trayIcon() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="8" fill="#151217"/><path d="M8 17c3-6 5-8 8-8s5 2 8 8c-3 4-5 6-8 6s-5-2-8-6Z" fill="#d9ff42"/><circle cx="16" cy="16" r="3" fill="#151217"/></svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`).resize({ width: 16, height: 16 });
}

function startWebServer() {
  webServer = createServer(async (request, response) => {
    const file = request.url === '/' ? 'index.html' : request.url.slice(1);
    if (file.includes('..')) {
      response.writeHead(403).end();
      return;
    }
    try {
      const body = await readFile(path.join(webRoot, file));
      response.writeHead(200, { 'Content-Type': file.endsWith('.html') ? 'text/html; charset=utf-8' : 'application/octet-stream' });
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  webServer.listen(WEB_PORT, '127.0.0.1');
}

function startCursorHelper() {
  const script = app.isPackaged
    ? path.join(process.resourcesPath, 'app.asar.unpacked', 'outputs', 'handwave-poc', 'cursor_server.py')
    : path.join(webRoot, 'cursor_server.py');
  helper = spawn('python', [script, '--stdio'], { cwd: path.dirname(script), windowsHide: true, stdio: ['pipe', 'ignore', 'ignore'] });
  helper.on('error', () => window?.webContents.send('helper-error'));
}

function sendHelper(message) {
  if (helper?.stdin?.writable) helper.stdin.write(`${JSON.stringify(message)}\n`);
}

function showWindow() {
  window.show();
  window.focus();
}

function createWindow() {
  window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 920,
    minHeight: 620,
    title: 'Handwave',
    backgroundColor: '#f4f0e8',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      backgroundThrottling: false
    }
  });
  window.loadURL(`http://127.0.0.1:${WEB_PORT}`);
  window.on('close', event => {
    if (!quitting) {
      event.preventDefault();
      window.hide();
    }
  });
}

if (!hasSingleInstanceLock) {
  app.quit();
} else app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((contents, permission, callback) => {
    callback(permission === 'media' && contents.getURL().startsWith(`http://127.0.0.1:${WEB_PORT}`));
  });
  startWebServer();
  startCursorHelper();
  createWindow();

  ipcMain.on('cursor-move', (_event, point) => sendHelper({ type: 'move', x: point.x, y: point.y }));
  ipcMain.on('mouse-button', (_event, action) => sendHelper({ type: 'mouse', action }));

  tray = new Tray(trayIcon());
  tray.setToolTip('Handwave · running');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show Handwave', click: showWindow },
    { label: 'Stop desktop control', click: () => window.webContents.send('emergency-stop') },
    { type: 'separator' },
    { label: 'Quit Handwave', click: () => { quitting = true; app.quit(); } }
  ]));
  tray.on('double-click', showWindow);

  globalShortcut.register('Escape', () => window.webContents.send('emergency-stop'));
});

app.on('second-instance', showWindow);

app.on('before-quit', () => { quitting = true; });
app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  sendHelper({ type: 'mouse', action: 'up' });
  helper?.kill();
  webServer?.close();
});
app.on('window-all-closed', () => {});

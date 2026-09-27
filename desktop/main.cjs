const { app, BrowserWindow, Menu, Tray, globalShortcut, nativeImage, ipcMain, screen } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');

let window, previewWindow, tray, engine;
let quitting = false, buffer = '';
const hasSingleInstanceLock = app.requestSingleInstanceLock();
const root = path.join(__dirname, '..');

function trayIcon() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="8" fill="#151217"/><path d="M8 17c3-6 5-8 8-8s5 2 8 8c-3 4-5 6-8 6s-5-2-8-6Z" fill="#d9ff42"/><circle cx="16" cy="16" r="3" fill="#151217"/></svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`).resize({ width: 16, height: 16 });
}

function sendCommand(command, extra = {}) {
  if (engine?.stdin?.writable) engine.stdin.write(`${JSON.stringify({ command, ...extra })}\n`);
}

function publish(message) {
  if (message.event === 'preview') {
    previewWindow?.webContents.send('preview-frame', message.image);
    return;
  }
  window?.webContents.send('engine-status', message);
  if (message.event === 'tracking') tray?.setToolTip(`Handwave · ${message.fps} fps`);
}

function startEngine() {
  if (engine && !engine.killed) return;
  const executable = app.isPackaged ? path.join(process.resourcesPath, 'engine', 'handwave-engine.exe') : path.join(root, '.venv', 'Scripts', 'python.exe');
  const args = app.isPackaged ? [] : [path.join(root, 'engine', 'handwave_engine.py')];
  engine = spawn(executable, args, { cwd: path.join(root, 'engine'), windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  engine.stdout.on('data', chunk => {
    buffer += chunk.toString(); const lines = buffer.split(/\r?\n/); buffer = lines.pop();
    for (const line of lines) { try { publish(JSON.parse(line)); } catch {} }
  });
  engine.stderr.on('data', chunk => publish({ event: 'diagnostic', message: chunk.toString() }));
  engine.on('error', error => publish({ event: 'fault', message: `Engine could not start: ${error.message}` }));
  engine.on('exit', code => { engine = null; if (!quitting && code) publish({ event: 'fault', message: 'Tracking engine stopped unexpectedly.' }); });
}

function stopEngine() {
  if (!engine) return;
  sendCommand('stop'); setTimeout(() => engine?.kill(), 1200);
}

function restartEngine() { stopEngine(); setTimeout(startEngine, 1400); }
function showWindow() { window.show(); window.focus(); }
function showPreview() { previewWindow.showInactive(); }

if (!hasSingleInstanceLock) app.quit();
else app.whenReady().then(() => {
  window = new BrowserWindow({ width: 820, height: 700, minWidth: 720, minHeight: 620, title: 'Handwave', backgroundColor: '#f4f0e8', webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false } });
  window.loadFile(path.join(__dirname, 'control.html'));
  window.on('close', event => { if (!quitting) { event.preventDefault(); window.hide(); } });
  const workArea = screen.getPrimaryDisplay().workArea;
  previewWindow = new BrowserWindow({ width: 264, height: 184, x: workArea.x + workArea.width - 284, y: workArea.y + workArea.height - 204, frame: false, transparent: true, resizable: false, alwaysOnTop: true, skipTaskbar: true, title: 'Handwave camera', webPreferences: { preload: path.join(__dirname, 'preview-preload.cjs'), contextIsolation: true, nodeIntegration: false } });
  previewWindow.loadFile(path.join(__dirname, 'preview.html'));
  previewWindow.on('close', event => { if (!quitting) { event.preventDefault(); previewWindow.hide(); } });
  tray = new Tray(trayIcon()); tray.setToolTip('Handwave · starting');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Show settings', click: showWindow }, { label: 'Show camera tile', click: showPreview }, { type: 'separator' }, { label: 'Pause control', click: () => sendCommand('pause') }, { label: 'Resume control', click: () => sendCommand('resume') }, { type: 'separator' }, { label: 'Quit Handwave', click: () => { quitting = true; app.quit(); } }
  ]));
  tray.on('double-click', showWindow);
  globalShortcut.register('Escape', () => sendCommand('pause'));
  ipcMain.on('engine-pause', () => sendCommand('pause'));
  ipcMain.on('engine-resume', () => sendCommand('resume'));
  ipcMain.on('engine-restart', restartEngine);
  ipcMain.on('engine-configure', (_event, values) => sendCommand('configure', { values }));
  ipcMain.on('preview-hide', () => previewWindow.hide());
  startEngine();
});

app.on('second-instance', showWindow);
app.on('before-quit', () => { quitting = true; });
app.on('will-quit', () => { globalShortcut.unregisterAll(); stopEngine(); });
app.on('window-all-closed', () => {});

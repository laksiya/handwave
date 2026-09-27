const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('handwaveDesktop', {
  pause: () => ipcRenderer.send('engine-pause'),
  resume: () => ipcRenderer.send('engine-resume'),
  restart: () => ipcRenderer.send('engine-restart'),
  configure: values => ipcRenderer.send('engine-configure', values),
  onStatus: callback => ipcRenderer.on('engine-status', (_event, message) => callback(message))
});

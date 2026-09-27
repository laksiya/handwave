const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('handwavePreview', {
  hide: () => ipcRenderer.send('preview-hide'),
  onFrame: callback => ipcRenderer.on('preview-frame', (_event, image) => callback(image))
});

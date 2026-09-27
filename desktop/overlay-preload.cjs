const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('handwaveOverlay', { onMarkers: callback => ipcRenderer.on('markers', (_event, markers) => callback(markers)) });

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('handwaveDesktop', {
  onEmergencyStop: callback => ipcRenderer.on('emergency-stop', callback),
  onHelperError: callback => ipcRenderer.on('helper-error', callback),
  moveCursor: (x, y) => ipcRenderer.send('cursor-move', { x, y }),
  mouseButton: action => ipcRenderer.send('mouse-button', action)
});

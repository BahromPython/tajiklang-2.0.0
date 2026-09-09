const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("studio", {
  open: () => ipcRenderer.invoke("file:open"),
  save: value => ipcRenderer.invoke("file:save", value),
  run: value => ipcRenderer.invoke("program:run", value),
  onExternalFile: callback => ipcRenderer.on("file:external", (_event, file) => callback(file)),
  onError: callback => ipcRenderer.on("studio:error", (_event, message) => callback(message))
});

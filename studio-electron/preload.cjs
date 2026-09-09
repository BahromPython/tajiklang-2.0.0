const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("studio", {
  open: () => ipcRenderer.invoke("file:open"),
  openProject: () => ipcRenderer.invoke("project:open"),
  readFile: path => ipcRenderer.invoke("file:read", path),
  save: value => ipcRenderer.invoke("file:save", value),
  run: value => ipcRenderer.invoke("program:run", value),
  check: value => ipcRenderer.invoke("program:check", value),
  packages: value => ipcRenderer.invoke("packages:list", value),
  onExternalFile: callback => ipcRenderer.on("file:external", (_event, file) => callback(file)),
  onError: callback => ipcRenderer.on("studio:error", (_event, message) => callback(message))
});

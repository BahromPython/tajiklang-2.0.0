const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("studio", {
  open: () => ipcRenderer.invoke("file:open"),
  save: value => ipcRenderer.invoke("file:save", value),
  run: value => ipcRenderer.invoke("program:run", value)
});

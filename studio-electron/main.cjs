const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");

let window;

function createWindow() {
  window = new BrowserWindow({
    width: 1440, height: 900, minWidth: 960, minHeight: 650,
    backgroundColor: "#11131a", autoHideMenuBar: true,
    title: "TajikLang Studio",
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, nodeIntegration: false }
  });
  window.loadFile(path.join(__dirname, "src", "index.html"));
}

function runtime() {
  if (app.isPackaged) {
    const executable = process.platform === "win32" ? ["tajik.exe"] : ["tajik", "tajik"];
    return { command: path.join(process.resourcesPath, "runtime", ...executable), args: [] };
  }
  return process.platform === "win32"
    ? { command: "py", args: [path.join(__dirname, "..", "main.py")] }
    : { command: "python3", args: [path.join(__dirname, "..", "main.py")] };
}

function execute(source, currentPath) {
  return new Promise(async (resolve) => {
    const file = currentPath || path.join(app.getPath("temp"), `tajiklang-${Date.now()}.tj`);
    await fs.writeFile(file, source, "utf8");
    const runner = runtime();
    const child = spawn(runner.command, [...runner.args, file], { windowsHide: true });
    let output = "", errors = "";
    child.stdout.on("data", data => output += data);
    child.stderr.on("data", data => errors += data);
    child.on("error", error => resolve({ ok: false, output: "", error: `Муҳаррики TajikLang оғоз нашуд: ${error.message}` }));
    child.on("close", code => resolve({ ok: code === 0, output, error: errors }));
  });
}

app.whenReady().then(() => {
  createWindow();
  ipcMain.handle("file:open", async () => {
    const result = await dialog.showOpenDialog(window, { properties: ["openFile"], filters: [{ name: "TajikLang", extensions: ["tj"] }] });
    if (result.canceled) return null;
    const filePath = result.filePaths[0];
    return { path: filePath, name: path.basename(filePath), source: await fs.readFile(filePath, "utf8") };
  });
  ipcMain.handle("file:save", async (_event, value) => {
    let filePath = value.path;
    if (!filePath) {
      const result = await dialog.showSaveDialog(window, { defaultPath: "барнома.tj", filters: [{ name: "TajikLang", extensions: ["tj"] }] });
      if (result.canceled) return null;
      filePath = result.filePath;
    }
    await fs.writeFile(filePath, value.source, "utf8");
    return { path: filePath, name: path.basename(filePath) };
  });
  ipcMain.handle("program:run", (_event, value) => execute(value.source, value.path));
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });

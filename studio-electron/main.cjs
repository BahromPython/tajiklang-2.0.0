const { app, BrowserWindow, dialog, ipcMain, Menu } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");

let window;
const PROJECT_FILE_LIMIT = 180;
const NEW_PROGRAM = "# TajikLang Next\nдода ном <- \"Баҳром\"\n\nнишон \"Салом\", ном\n";
const SMOKE_TEST = process.env.TAJIKLANG_SMOKE === "1";

function sendMenuAction(action) {
  if (window && !window.isDestroyed()) window.webContents.send("studio:menu", action);
}

function installMenu() {
  const template = [
    { label: "Файл", submenu: [
      { label: "Файли нав", accelerator: "Ctrl+N", click: () => sendMenuAction("new") },
      { label: "Кушодани файл…", accelerator: "Ctrl+O", click: () => sendMenuAction("open") },
      { label: "Кушодани лоиҳа…", accelerator: "Ctrl+Shift+O", click: () => sendMenuAction("project") },
      { type: "separator" },
      { label: "Нигоҳ доштан", accelerator: "Ctrl+S", click: () => sendMenuAction("save") },
      { type: "separator" },
      { role: "quit", label: "Баромадан" }
    ] },
    { label: "Таҳрир", submenu: [
      { role: "undo", label: "Бозгашт" }, { role: "redo", label: "Такрор" }, { type: "separator" },
      { role: "cut", label: "Буридан" }, { role: "copy", label: "Нусха кардан" },
      { role: "paste", label: "Часпондан" }, { role: "selectAll", label: "Ҳамаро интихоб кардан" }
    ] },
    { label: "Намоиш", submenu: [
      { label: "Файлҳо", accelerator: "Ctrl+Shift+F", click: () => sendMenuAction("files") },
      { label: "Ҷустуҷӯ", accelerator: "Ctrl+F", click: () => sendMenuAction("search") },
      { label: "Равшанӣ / торикӣ", click: () => sendMenuAction("theme") },
      { type: "separator" }, { role: "toggleDevTools", label: "Абзорҳои таҳия" }
    ] },
    { label: "Иҷро", submenu: [
      { label: "Иҷрои барнома", accelerator: "F5", click: () => sendMenuAction("run") },
      { label: "Санҷиши барнома", accelerator: "F7", click: () => sendMenuAction("check") }
    ] },
    { label: "Терминал", submenu: [
      { label: "Кушодани Tajik terminal", accelerator: "Ctrl+`", click: () => sendMenuAction("terminal") },
      { label: "TajikLang version", click: () => sendMenuAction("version") }
    ] },
    { label: "Кумак", submenu: [
      { label: "TajikLang Next", click: () => sendMenuAction("help") },
      { role: "about", label: "Дар бораи TajikLang Studio" }
    ] }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function fileArgument(arguments_) {
  return arguments_.find(argument => argument.toLowerCase().endsWith(".tj"));
}

async function openFromSystem(filePath) {
  if (!filePath || !window) return;
  try {
    const resolved = path.resolve(filePath);
    const source = await fs.readFile(resolved, "utf8");
    window.webContents.send("file:external", { path: resolved, name: path.basename(resolved), source });
  } catch (error) {
    window.webContents.send("studio:error", `Файл кушода нашуд: ${error.message}`);
  }
}

function createWindow() {
  window = new BrowserWindow({
    width: 1440, height: 900, minWidth: 960, minHeight: 650,
    backgroundColor: "#11131a", autoHideMenuBar: false, show: !SMOKE_TEST,
    title: "TajikLang Studio",
    webPreferences: { preload: path.join(__dirname, "preload.cjs"), contextIsolation: true, nodeIntegration: false }
  });
  window.loadFile(path.join(__dirname, "src", "index.html"));
  window.webContents.once("did-finish-load", async () => {
    await openFromSystem(fileArgument(process.argv));
    if (SMOKE_TEST) await runSmokeTest();
  });
}

async function writeNewProgram(filePath) {
  await fs.writeFile(filePath, NEW_PROGRAM, "utf8");
  return { path: filePath, name: path.basename(filePath), source: NEW_PROGRAM };
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

function runRuntime(arguments_, cwd) {
  return new Promise(resolve => {
    const runner = runtime();
    const child = spawn(runner.command, [...runner.args, ...arguments_], { windowsHide: true, cwd });
    let output = "", errors = "";
    child.stdout.on("data", data => output += data);
    child.stderr.on("data", data => errors += data);
    child.on("error", error => resolve({ ok: false, output: "", error: `Муҳаррики TajikLang оғоз нашуд: ${error.message}` }));
    child.on("close", code => resolve({ ok: code === 0, output, error: errors }));
  });
}

function commandArguments(command) {
  const words = command.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
  if (words[0]?.toLowerCase() === "tajik") words.shift();
  return words.map(word => word.replace(/^"|"$/g, ""));
}

function execute(source, currentPath, mode = "run") {
  return new Promise(async (resolve) => {
    const file = currentPath || path.join(app.getPath("temp"), `tajiklang-${Date.now()}.tj`);
    await fs.writeFile(file, source, "utf8");
    const args = mode === "check" ? ["--санҷиш", file] : [file];
    resolve(await runRuntime(args, path.dirname(file)));
  });
}

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
async function runSmokeTest() {
  try {
    const labels = Menu.getApplicationMenu().items.map(item => item.label);
    for (const label of ["Файл", "Таҳрир", "Намоиш", "Иҷро", "Терминал", "Кумак"]) {
      if (!labels.includes(label)) throw new Error(`Menu missing: ${label}`);
    }
    const page = await window.webContents.executeJavaScript(
      "Boolean(window.studio && document.querySelector('#new-file') && document.querySelector('#terminal-panel'))"
    );
    if (!page) throw new Error("Studio UI or preload bridge missing.");
    const saved = await writeNewProgram(path.join(app.getPath("temp"), "tajiklang-smoke.tj"));
    if (!saved.source.includes("дода ном")) throw new Error("New file template failed.");
    const ran = await execute(NEW_PROGRAM, null);
    if (!ran.ok || !ran.output.includes("Салом Баҳром")) throw new Error("Run command failed.");
    const terminal = await runRuntime(["--version"], app.getPath("temp"));
    if (!terminal.ok || !terminal.output.includes("TajikLang")) throw new Error("Terminal runner failed.");
    sendMenuAction("terminal");
    await wait(80);
    const terminalVisible = await window.webContents.executeJavaScript(
      "!document.querySelector('#terminal-panel').hidden"
    );
    if (!terminalVisible) throw new Error("Terminal menu shortcut bridge failed.");
    await fs.unlink(saved.path).catch(() => {});
    console.log("TajikLang Studio smoke test passed.");
    app.exit(0);
  } catch (error) {
    console.error(`TajikLang Studio smoke test failed: ${error.stack || error}`);
    app.exit(1);
  }
}

async function projectFiles(folder, prefix = "", state = { count: 0, depth: 0 }) {
  if (state.depth > 5 || state.count >= PROJECT_FILE_LIMIT) return [];
  const entries = await fs.readdir(folder, { withFileTypes: true });
  const files = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (entry.name === ".git" || entry.name === "node_modules" || entry.name === "dist") continue;
    const relative = path.join(prefix, entry.name);
    const absolute = path.join(folder, entry.name);
    if (entry.isDirectory()) {
      const children = await projectFiles(absolute, relative, { count: state.count, depth: state.depth + 1 });
      state.count += children.length;
      if (children.length) files.push({ type: "folder", name: entry.name, path: absolute, children });
    } else if (/\.(tj|md|json|txt|html|css)$/iu.test(entry.name) && state.count++ < PROJECT_FILE_LIMIT) {
      files.push({ type: "file", name: entry.name, path: absolute, relative });
    }
  }
  return files;
}

app.whenReady().then(() => {
  const singleInstance = app.requestSingleInstanceLock();
  if (!singleInstance) { app.quit(); return; }
  installMenu();
  createWindow();
  ipcMain.handle("file:open", async () => {
    const result = await dialog.showOpenDialog(window, { properties: ["openFile"], filters: [{ name: "TajikLang", extensions: ["tj"] }] });
    if (result.canceled) return null;
    const filePath = result.filePaths[0];
    return { path: filePath, name: path.basename(filePath), source: await fs.readFile(filePath, "utf8") };
  });
  ipcMain.handle("file:new", async () => {
    const result = await dialog.showSaveDialog(window, {
      defaultPath: "барномаи нав.tj",
      filters: [{ name: "TajikLang", extensions: ["tj"] }]
    });
    if (result.canceled) return null;
    return writeNewProgram(result.filePath);
  });
  ipcMain.handle("project:open", async () => {
    const result = await dialog.showOpenDialog(window, { properties: ["openDirectory"] });
    if (result.canceled) return null;
    const root = result.filePaths[0];
    return { path: root, name: path.basename(root), files: await projectFiles(root) };
  });
  ipcMain.handle("file:read", async (_event, filePath) => ({
    path: filePath, name: path.basename(filePath), source: await fs.readFile(filePath, "utf8")
  }));
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
  ipcMain.handle("program:check", (_event, value) => execute(value.source, value.path, "check"));
  ipcMain.handle("packages:list", (_event, value) => runRuntime(["ҷустуҷӯ"], value?.projectPath || app.getPath("home")));
  ipcMain.handle("terminal:run", (_event, value) => {
    const args = commandArguments(value.command || "");
    if (!args.length) return { ok: true, output: "Tajik terminal омода аст. Мисол: tajik --version", error: "" };
    return runRuntime(args, value.projectPath || app.getPath("home"));
  });
  app.on("second-instance", (_event, arguments_) => {
    if (window.isMinimized()) window.restore();
    window.focus();
    openFromSystem(fileArgument(arguments_));
  });
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });

const editor = document.querySelector("#editor");
const lines = document.querySelector("#line-numbers");
const output = document.querySelector("#output");
const fileName = document.querySelector("#file-name");
const tabName = document.querySelector("#tab-name");
const breadcrumb = document.querySelector("#breadcrumb");
const status = document.querySelector("#status");
const saveState = document.querySelector("#save-state");
let currentPath = null;

function refreshLines() { lines.textContent = Array.from({ length: editor.value.split("\n").length }, (_, i) => i + 1).join("\n"); }
function setStatus(message) { status.textContent = message; saveState.textContent = message; }
function setFile(file) { currentPath = file.path; fileName.textContent = file.name; tabName.textContent = file.name; breadcrumb.innerHTML = `ЛОИҲА <span>›</span> ${file.name}`; editor.value = file.source; refreshLines(); setStatus("Кушода шуд"); }
function newFile() { currentPath = null; editor.value = "# TajikLang Next\nдода ном <- \"Баҳром\"\n\nнишон \"Салом\", ном\n"; setFile({ path: null, name: "барномаи нав.tj", source: editor.value }); }
async function save() { const saved = await window.studio.save({ path: currentPath, source: editor.value }); if (saved) setFile({ ...saved, source: editor.value }); }
async function run() { setStatus("Иҷро мешавад…"); output.classList.remove("error"); output.textContent = "Иҷро мешавад…"; const result = await window.studio.run({ path: currentPath, source: editor.value }); output.textContent = result.ok ? (result.output || "(натиҷа нест)") : (result.error || result.output || "Хатои номаълум"); output.classList.toggle("error", !result.ok); setStatus(result.ok ? "Иҷро шуд" : "Хатои иҷро"); }

editor.addEventListener("input", () => { refreshLines(); setStatus("Тағйир ёфт"); });
editor.addEventListener("scroll", () => { lines.scrollTop = editor.scrollTop; });
document.querySelector("#new-file").addEventListener("click", newFile);
document.querySelector(".add-tab").addEventListener("click", newFile);
document.querySelector("#open-file").addEventListener("click", async () => { const file = await window.studio.open(); if (file) setFile(file); });
document.querySelector("#run").addEventListener("click", run);
document.querySelector("#activity-run").addEventListener("click", run);
document.querySelector("#check").addEventListener("click", () => { output.textContent = "Санҷиш ҳангоми иҷро анҷом меёбад."; setStatus("Омода барои санҷиш"); });
document.addEventListener("keydown", event => { if (event.key === "F5") { event.preventDefault(); run(); } if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); save(); } if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "o") { event.preventDefault(); document.querySelector("#open-file").click(); } });
refreshLines();

"""Сомонаро месозад — builds the public site into `site/`.

    py tools/build_site.py

Three pages, no framework and no build chain: a landing page, the playground,
and a download page. Everything factual on them — the version, how many
builtins there are, how many tests pass — is read off the project at build
time, so the site cannot quietly drift from what the language actually is.

Code samples are coloured by `tajiklang.highlight`, the same module the editor
uses. A website whose syntax colours disagree with the editor's is a small lie
in the first place a newcomer looks.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
REPO = "https://github.com/BahromPython/tajiklang-2.0.0"
# Netlify hosts the public site; GitHub Releases host the signed-by-checksum
# platform artifacts.  This stable link always selects the newest Windows
# x64 installer, which is the right choice for nearly every student.
DOWNLOAD = f"{REPO}/releases/latest/download/TajikLang-windows-x64.zip"
RELEASES = f"{REPO}/releases/latest"

sys.path.insert(0, str(ROOT))


def _utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def facts() -> dict[str, str]:
    """Read the numbers off the project rather than typing them into HTML."""
    from tajiklang import __version__
    from tajiklang.interpreter import Interpreter

    builtins = len(Interpreter([], lambda _: None).builtins.values)

    tests = 0
    for path in (ROOT / "tests").glob("test_*.py"):
        tests += len(re.findall(r"\n    def test_", path.read_text(encoding="utf-8")))

    lessons = len(re.findall(
        r"^## Дарси ",
        (ROOT / "docs" / "дарсҳо.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    ))
    messages = re.search(
        r"Ҳамагӣ (\d+) матн",
        (ROOT / "docs" / "ТАРҶУМА.md").read_text(encoding="utf-8"),
    )

    return {
        "version": __version__,
        "builtins": str(builtins),
        "tests": str(tests),
        "lessons": str(lessons),
        "examples": str(len(list((ROOT / "examples").glob("*.tj")))),
        "messages": messages.group(1) if messages else "?",
    }


def code(source: str) -> str:
    """One TajikLang sample, coloured by the language's own rules."""
    from tajiklang.highlight import to_html
    from tajiklang.interpreter import Interpreter

    builtins = set(Interpreter([], lambda _: None).builtins.values)
    return f'<pre class="tj"><code>{to_html(source.strip(), builtins)}</code></pre>'


STYLE = """
  :root {
    --ink: #0e1418; --soft: #5a6773; --faint: #8b98a5;
    --line: #e3e8ec; --bg: #ffffff; --panel: #f6f8f9;
    --accent: #0f7b5f; --accent-ink: #ffffff; --accent-soft: #e7f4ef;
    --code-bg: #0f1519; --code-ink: #dfe7ec;
    --k: #7cc4ff; --b: #c9a0ff; --s: #8ee08e; --n: #f2c078; --c: #6b7784;
    --mono: ui-monospace, "Cascadia Code", "Segoe UI Mono", Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ink: #e9edf1; --soft: #97a3b0; --faint: #7c8794;
      --line: #232a32; --bg: #0d1114; --panel: #141a1f;
      --accent: #35b48b; --accent-ink: #06120d; --accent-soft: #13251e;
      --code-bg: #0a0e11;
    }
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 17px/1.65 system-ui, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 900px; margin: 0 auto; padding: 0 24px; }

  nav {
    position: sticky; top: 0; z-index: 10; backdrop-filter: blur(10px);
    background: color-mix(in srgb, var(--bg) 88%, transparent);
    border-bottom: 1px solid var(--line);
  }
  nav .wrap { display: flex; align-items: center; gap: 22px; height: 58px; }
  nav b { font-size: 17px; letter-spacing: -0.01em; }
  nav a { color: var(--soft); text-decoration: none; font-size: 15px; }
  nav a:hover { color: var(--ink); }
  nav .spacer { flex: 1; }

  header { padding: 74px 0 20px; }
  h1 {
    font-size: clamp(40px, 7vw, 60px); margin: 0 0 14px;
    letter-spacing: -0.03em; line-height: 1.05;
  }
  .lede { font-size: clamp(19px, 2.6vw, 23px); color: var(--soft); margin: 0 0 32px; max-width: 30em; }
  .cta { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
  a.btn {
    display: inline-flex; align-items: center; gap: 9px;
    padding: 13px 24px; border-radius: 11px; text-decoration: none;
    font-weight: 600; font-size: 16px; border: 1px solid var(--line);
    color: var(--ink); background: var(--panel); transition: transform .12s;
  }
  a.btn:hover { transform: translateY(-1px); }
  a.btn.primary { background: var(--accent); color: var(--accent-ink); border-color: transparent; }
  .note { color: var(--faint); font-size: 14px; margin: 0; }

  .stats {
    display: flex; flex-wrap: wrap; gap: 0; margin: 44px 0 0;
    border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
  }
  .stats div {
    flex: 1 1 120px; padding: 18px 20px; border-left: 1px solid var(--line);
    background: var(--panel);
  }
  .stats div:first-child { border-left: 0; }
  .stats b { display: block; font-size: 25px; letter-spacing: -0.02em; }
  .stats span { color: var(--faint); font-size: 13px; }

  section { padding: 60px 0; border-top: 1px solid var(--line); }
  h2 { font-size: clamp(26px, 3.4vw, 32px); margin: 0 0 10px; letter-spacing: -0.02em; }
  h3 { font-size: 19px; margin: 34px 0 10px; }
  .sub { color: var(--soft); margin: 0 0 26px; max-width: 34em; }
  p { margin: 0 0 15px; }

  pre.tj, pre.out {
    background: var(--code-bg); color: var(--code-ink); border-radius: 13px;
    padding: 20px 22px; overflow-x: auto; font-family: var(--mono);
    font-size: 14.5px; line-height: 1.7; margin: 0 0 18px;
    border: 1px solid #1d262d;
  }
  pre.out { color: #b7c4cd; }
  code { font-family: var(--mono); font-size: 0.92em; }
  p code, li code, td code {
    background: var(--panel); padding: 2px 6px; border-radius: 5px;
    border: 1px solid var(--line);
  }
  .tj-keyword { color: var(--k); }
  .tj-builtin { color: var(--b); }
  .tj-string  { color: var(--s); }
  .tj-number  { color: var(--n); }
  .tj-comment { color: var(--c); font-style: italic; }

  table { width: 100%; border-collapse: collapse; margin: 0 0 18px; font-size: 15.5px; }
  th, td { text-align: right; padding: 11px 14px; border-bottom: 1px solid var(--line); }
  th { color: var(--faint); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: .06em; }
  tr:last-child td { border-bottom: 0; }
  .win { background: var(--accent-soft); }

  .cards { display: grid; gap: 16px; grid-template-columns: 1fr 1fr; }
  @media (max-width: 760px) { .cards { grid-template-columns: 1fr; } }
  .card { border: 1px solid var(--line); border-radius: 13px; padding: 20px 22px; background: var(--panel); }
  .card h3 { margin: 0 0 8px; font-size: 17px; }
  .card p { margin: 0; color: var(--soft); font-size: 15.5px; }
  .download-card {
    margin: 26px 0 0; padding: 28px; border-radius: 16px;
    border: 1px solid #14916d; background: linear-gradient(135deg, var(--accent-soft), var(--panel));
  }
  .download-card h2 { margin-bottom: 8px; }
  .download-card .cta { margin: 20px 0 10px; }
  .download-meta { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 18px; }
  .pill { border: 1px solid var(--line); border-radius: 999px; padding: 4px 10px; color: var(--soft); font-size: 13px; background: var(--bg); }

  .steps { counter-reset: s; padding: 0; list-style: none; }
  .steps li { counter-increment: s; position: relative; padding-right: 42px; margin-bottom: 22px; }
  .steps li::before {
    content: counter(s); position: absolute; right: 0; top: 1px;
    width: 28px; height: 28px; border-radius: 50%; background: var(--accent);
    color: var(--accent-ink); font-size: 15px; font-weight: 700;
    display: grid; place-items: center;
  }
  .steps b { display: block; margin-bottom: 6px; }

  .quiet { color: var(--soft); }
  footer { padding: 46px 0 80px; color: var(--faint); font-size: 14.5px; border-top: 1px solid var(--line); }
  a { color: var(--accent); }
"""

NAV = """
<nav><div class="wrap">
  <b>TajikLang</b>
  <a href="./#чаро">Чаро</a>
  <a href="./install.html">Насб</a>
  <a href="playground.html">Майдонча</a>
  <span class="spacer"></span>
  <a href="{repo}">GitHub</a>
</div></nav>
"""

HEAD = """<!doctype html>
<html lang="tg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta property="og:title" content="TajikLang">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>Т</text></svg>">
<style>{style}</style>
</head>
<body>
"""

FOOT = """
<footer><div class="wrap">
  TajikLang {version} · MIT ·
  <a href="{repo}">GitHub</a> ·
  <a href="{repo}/blob/main/docs/дарсҳо.md">Дарсҳо</a> ·
  <a href="{repo}/blob/main/docs/ТАРҶУМА.md">Барои муаллимон</a>
</div></footer>
</body>
</html>
"""


def landing(f: dict[str, str]) -> str:
    return (
        HEAD.format(
            title="TajikLang — забони барномасозӣ бо забони тоҷикӣ",
            description="Забони барномасозӣ, ки калимаҳо, хатогиҳо ва тартиби "
                        "алифбои он тоҷикӣ мебошанд. Барои хонандагони тоҷикзабон.",
            style=STYLE,
        )
        + NAV.format(repo=REPO)
        + f"""
<div class="wrap">

<header>
  <h1>Барномасозӣ<br>бо забони модарӣ</h1>
  <p class="lede">Забоне, ки калимаҳо, хатогиҳо ва ҳатто тартиби алифбои он
     тоҷикӣ мебошанд. Барои хонандагоне, ки набояд пеш аз барномасозӣ
     англисиро омӯзанд.</p>

  <div class="cta">
    <a class="btn primary" href="playground.html">▶ Дар браузер санҷед</a>
    <a class="btn" href="install.html">⬇ Насб кардан</a>
  </div>
  <p class="note">Дар браузер ҳеҷ насб лозим нест. Барои Windows нусхаи
     мустақил ҳаст — ҳеҷ чизи дигар лозим нест.</p>

  <div class="stats">
    <div><b>{f['version']}</b><span>версия</span></div>
    <div><b>{f['builtins']}</b><span>функсияи тайёр</span></div>
    <div><b>{f['lessons']}</b><span>дарс бо тоҷикӣ</span></div>
    <div><b>{f['examples']}</b><span>мисол</span></div>
    <div><b>{f['tests']}</b><span>санҷиш</span></div>
  </div>
</header>

<section>
  <h2>Барномаи ҳақиқӣ</h2>
  <p class="sub">Ҳеҷ калимаи англисӣ нест — на дар барнома, на дар хатогиҳо.</p>
""" + code('''
қолиб Донишҷӯ:
    функсия оғоз(худ, ном, баҳо):
        худ.ном = ном
        худ.баҳо = баҳо

    функсия хулоса(худ):
        агар худ.баҳо >= 4.5:
            баргардон "аъло"
        баргардон "хуб"

бигзор синф = [
    Донишҷӯ("Яқубов", 4.75),
    Донишҷӯ("Ғафуров", 3.5),
]

функсия номи(д):
    баргардон д.ном

барои д аз тартиб_бо(синф, номи):
    навис(д.ном, "—", д.хулоса())
''') + """
</section>

<section id="чаро">
  <h2>Се чиз, ки забонҳои дигар намекунанд</h2>

  <h3>1 · Барнома пеш аз иҷро санҷида мешавад</h3>
  <p class="sub">Python хатои имлоиро танҳо вақте меёбад, ки он сатр иҷро
     шавад. TajikLang ҳамаи хатоҳоро пеш аз он ки чизе чоп шавад нишон
     медиҳад — ва ҳамаашро якбора.</p>
  <pre class="out">Хатои санҷиш (CheckError) (сатри 3, сутуни 11):

        навис(нмо)
              ^

Номи "нмо" муайян нашудааст.
Маслиҳат: Оё шумо "ном" -ро дар назар доштед?

Ҳамагӣ 2 хато. Барнома иҷро нашуд.</pre>

  <h3>2 · Ҳисоби даҳӣ</h3>
""" + code('''
навис(0.1 + 0.2)          # 0.3
навис(0.1 + 0.2 == 0.3)   # рост
''') + """
  <table>
    <tr><th>Забон</th><th>0.1 + 0.2</th><th>== 0.3</th></tr>
    <tr><td class="quiet">Python, C, Java, JavaScript</td>
        <td><code>0.30000000000000004</code></td><td><code>false</code></td></tr>
    <tr class="win"><td><b>TajikLang</b></td>
        <td><b><code>0.3</code></b></td><td><b><code>рост</code></b></td></tr>
  </table>
  <p class="quiet">Ҳисоби мактабӣ даҳӣ аст. Пул даҳӣ аст. Баҳо даҳӣ аст.</p>

  <h3>3 · «чаро» — саволе, ки ҷавоб намеёбад</h3>
""" + code('''
бигзор ҷамъ = 0
барои i аз 1 то 3:
    ҷамъ += i
чаро(ҷамъ)
''') + """
  <pre class="out">Тағйирёбандаи "ҷамъ":
    сатри 1    →  0    (эълон)
    сатри 3    →  1    (ивазкунӣ)
    сатри 3    →  3    (ивазкунӣ)
    сатри 3    →  6    (ивазкунӣ)</pre>
  <p class="quiet">«Чаро тағйирёбандаи ман ҳамин аст?» — саволи асосии ҳар
     навомӯз, ки дигар забонҳо ба он ҷавоб намедиҳанд.</p>
</section>

<section>
  <h2>Тоҷикӣ, на тарҷума</h2>
  <div class="cards">
    <div class="card">
      <h3>Тартиби алифбои тоҷикӣ</h3>
      <p>Дар Unicode ҳарфҳои <code>ғ ӣ қ ӯ ҳ ҷ</code> баъд аз <code>я</code>
         меоянд, бинобар ин ҳар забони дигар рӯйхати синфро нодуруст тартиб
         медиҳад. Дар ин ҷо «Ғафуров» пеш аз «Яқубов» меистад.</p>
    </div>
    <div class="card">
      <h3>Муттаҳидсозии Unicode</h3>
      <p>Ҳарфи <code>ӣ</code> ду шакли навишт дорад, ки дар экран якхелаанд.
         Бе ислоҳ як ном ду тағйирёбандаи гуногун мешуд.</p>
    </div>
    <div class="card">
      <h3>Ҳеҷ ҷодугарӣ нест</h3>
      <p><code>агар ном:</code> хато аст — <code>агар ном != ""</code>
         нависед. Ҳар қоида равшан ва гуфташуда аст.</p>
    </div>
    <div class="card">
      <h3>Хатогиҳо таълим медиҳанд</h3>
      <p>Ҳар хатогӣ сатр, сутун, аломати <code>^</code>, маслиҳат ва роҳи
         даъватро дорад — ҳама бо забони тоҷикӣ.</p>
    </div>
  </div>
</section>

<section>
  <h2>Бастаҳои худӣ</h2>
  <p class="sub">Феҳристи худӣ, на pip. Хонандае, ки китобхонаи тоҷикӣ насб
     мекунад, набояд аввал абзорҳои Python-ро омӯзад.</p>
  <pre class="out">tajik ҷустуҷӯ           бастаҳои мавҷуда
tajik гирифтан омор     насб мекунад
tajik бастаҳо           насбшударо нишон медиҳад</pre>
""" + code('''
ворид омор
ворид шакл

бигзор баҳоҳо = [5, 4, 5, 3, 5, 4, 2]

шакл.қуттӣ("Журнали синф")
навис("Медиана:", омор.медиана(баҳоҳо))
шакл.диаграмма(["Душанбе", "Хуҷанд"], [95, 60])
''') + f"""
  <p class="quiet">Ҳарду бастаи тайёр — <code>омор</code> ва <code>шакл</code> —
     бо худи TajikLang навишта шудаанд, на бо Python.</p>
</section>

<section>
  <h2>Омӯзиш</h2>
  <div class="cards">
    <div class="card">
      <h3><a href="{REPO}/blob/main/docs/дарсҳо.md">{f['lessons']} дарс бо тоҷикӣ</a></h3>
      <p>Аз «Салом Тоҷикистон» то қолибҳо ва саҳифаи интернетӣ. Ҳар дарс машқ
         дорад.</p>
    </div>
    <div class="card">
      <h3><a href="{REPO}/blob/main/docs/чӣ_тавр_кор_мекунад.md">Дар дохил чӣ мешавад</a></h3>
      <p>Лексер, парсер, дарахти синтаксисӣ, интерпретатор — бо забони тоҷикӣ.</p>
    </div>
    <div class="card">
      <h3><a href="{REPO}/tree/main/examples">{f['examples']} мисоли тайёр</a></h3>
      <p>Барномаҳои кориро хонед ва тағйир диҳед.</p>
    </div>
    <div class="card">
      <h3><a href="{REPO}/blob/main/LANGUAGE_SPEC.md">Мушаххасоти забон</a></h3>
      <p>Тавсифи пурра ва сабаби ҳар қарор (бо англисӣ).</p>
    </div>
  </div>
</section>

<section>
  <h2>Барои муаллимон</h2>
  <p class="sub">Файли <a href="{REPO}/blob/main/docs/ТАРҶУМА.md">ТАРҶУМА.md</a>
     рӯйхати ҳамаи {f['messages']} матнест, ки забон ба донишҷӯ нишон медиҳад,
     бо сутуни «варианти беҳтар».</p>
  <p>Агар шумо тоҷикзабон бошед ва бист дақиқа вақт дошта бошед, онро хонед ва
     ҷумлаҳои носуфтаро ислоҳ кунед. Ин муфидтарин кӯмакест, ки ба ин лоиҳа
     расонида метавонед — муаллифи он тоҷикзабон нест.</p>
</section>

</div>
""" + FOOT.format(version=f["version"], repo=REPO)
    )


def install_page(f: dict[str, str]) -> str:
    return (
        HEAD.format(
            title="Насб кардани TajikLang",
            description="TajikLang-ро дар браузер санҷед ё барои Windows "
                        "боргирӣ кунед. Ҳеҷ чизи дигар лозим нест.",
            style=STYLE,
        )
        + NAV.format(repo=REPO)
        + f"""
<div class="wrap">

<header>
  <h1>TajikLang-ро<br>ба компютер гиред</h1>
  <p class="lede">Барои Windows — як боргирӣ, бе Python ва бе насби иловагӣ.
     Тайёр барои синфхона, хона ва лоиҳаҳои ҷиддӣ.</p>

  <div class="download-card">
    <h2>TajikLang {f['version']} барои Windows</h2>
    <p class="quiet">Нусхаи пурраи мустақил: забон, муҳаррир, TajikBlocks,
       муҳити лоиҳаҳо ва намунаҳои омӯзишӣ.</p>
    <div class="cta">
      <a class="btn primary" href="{DOWNLOAD}">⬇ Зеркашӣ барои Windows</a>
      <a class="btn" href="{REPO}">Коди манбаъ</a>
    </div>
    <div class="download-meta">
      <span class="pill">Windows 10 / 11 · 64-bit</span>
      <span class="pill">ZIP · 11.7 МБ</span>
      <span class="pill">Python лозим нест</span>
      <span class="pill">Версияи {f['version']}</span>
    </div>
  </div>
</header>

<section style="border-top:0; padding-top:0">
  <h2>1 · Бе ҳеҷ насб — дар браузер</h2>
  <p class="sub">Тамоми забон дар як саҳифа кор мекунад. Барои мактабҳо роҳи
     соддатарин.</p>
  <div class="cta">
    <a class="btn primary" href="playground.html">▶ Майдончаро кушоед</a>
  </div>
</section>

<section>
  <h2>2 · Пас аз зеркашӣ чӣ кор кунед</h2>
  <p class="sub">Нусхаи мустақил барои мактаб ва хона. Ҳеҷ чизи дигар лозим
     нест — на Python, на интернети доимӣ.</p>

  <ol class="steps" style="margin-top:30px">
    <li><b>Боргирӣ ва кушодан</b>
        Файли ZIP-ро боргирӣ карда, ба ҷузвдони худ кушоед.</li>
    <li><b>Насбкунандаро иҷро кунед</b>
        <pre class="out">powershell -ExecutionPolicy Bypass -File насб.ps1</pre>
        Ин фармони <code>tajik</code>-ро ба PATH илова мекунад, файлҳои
        <code>.tj</code>-ро мепайвандад (ду клик — иҷро) ва муҳаррирро ба
        менюи Start мегузорад.</li>
    <li><b>Терминали навро кушоед</b>
        <pre class="out">tajik                 реҷаи интерактивӣ
tajik барнома.tj      барномаро иҷро мекунад
tajik муҳаррир        муҳаррирро мекушояд</pre></li>
  </ol>

  <p class="quiet">Барои нест кардан: <code>нест.ps1</code> дар ҳамон ҷузвдон.</p>
</section>

<section>
  <h2>3 · Аз манбаъ — барои таҳиягарон</h2>
  <p class="sub">Ин роҳ барои онҳоест, ки мехоҳанд худи забонро тағйир диҳанд
     ё дар таҳияи он ҳисса гузоранд. Барои омӯзиш роҳи 1 ё 2 кофист.</p>
  <pre class="out">pip install git+{REPO}.git</pre>
  <p class="quiet">Талаб мекунад: Python 3.10 ё навтар. Тафсилот дар
     <a href="{REPO}">GitHub</a>.</p>
</section>

<section>
  <h2>Дар дохили зеркашӣ чӣ ҳаст</h2>

  <div class="cards">
    <div class="card"><h3>Муҳаррири TajikLang</h3><p>Дарахти лоиҳаҳо, ранга кардани код, хатогиҳои тоҷикӣ, пешнамоиш ва F5 барои иҷро.</p></div>
    <div class="card"><h3>TajikBlocks</h3><p>Барномасозии блокӣ барои оғози осон — бо нигоҳ доштан, кушодан, тағйирёбандаҳо ва функсияҳо.</p></div>
    <div class="card"><h3>Муҳити лоиҳа</h3><p>Ҳар лоиҳа ҷудо аст: бастаҳо, вебсаҳифаҳо ва файлҳои худи он дар як ҷо нигоҳ дошта мешаванд.</p></div>
    <div class="card"><h3>Намунаҳо ва дарсҳо</h3><p>Барномаҳои тайёрро боз кунед, тағйир диҳед ва аз онҳо омӯзед — ҳатто ҳангоми набудани интернет.</p></div>
  </div>

  <h2 style="margin-top:52px">Муҳаррирҳо</h2>

  <h3>Муҳаррири худӣ</h3>
  <p>Бо забон меояд. Дарахти файлҳо, ранга кардан, панели хатоҳо, F5 — иҷро,
     F6 — санҷиш.</p>
  <pre class="out">tajik муҳаррир</pre>

  <h3>VS Code</h3>
  <p>Васеъкуниро аз саҳифаи нашрҳо боргирӣ кунед:</p>
  <pre class="out">code --install-extension tajiklang-{f['version']}.vsix</pre>
  <div class="cta">
    <a class="btn" href="{RELEASES}">⬇ Васеъкунии VS Code</a>
  </div>
</section>

<section>
  <h2>Бастаҳо</h2>
  <pre class="out">tajik ҷустуҷӯ           бастаҳои мавҷуда
tajik гирифтан омор     насб мекунад
tajik бастаҳо           насбшударо нишон медиҳад
tajik нест омор         нест мекунад</pre>
  <p class="quiet">Бастаҳо дар <code>%LOCALAPPDATA%\\TajikLang</code> нигоҳ дошта
     мешаванд. Барои иваз кардани ин ҷо тағйирёбандаи муҳити
     <code>TAJIKLANG_HOME</code>-ро гузоред — масалан ба диски муштараки мактаб.</p>
</section>

</div>
""" + FOOT.format(version=f["version"], repo=REPO)
    )


def main() -> int:
    _utf8_stdout()
    data = facts()

    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_playground.py")],
        check=True, cwd=ROOT,
    )

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    (SITE / "index.html").write_text(landing(data), encoding="utf-8")
    (SITE / "install.html").write_text(install_page(data), encoding="utf-8")
    (SITE / "playground.html").write_text(
        (ROOT / "playground" / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copy(ROOT / "assets" / "banner.svg", SITE / "banner.svg")

    total = sum(p.stat().st_size for p in SITE.iterdir() if p.is_file())
    print(
        f"site/ — 3 саҳифа, {total / 1024:.0f} KB "
        f"(версия {data['version']}, {data['tests']} санҷиш)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

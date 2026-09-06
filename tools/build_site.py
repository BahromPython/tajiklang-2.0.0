"""Сомонаро месозад — builds the public site into `site/`.

    py tools/build_site.py

Two pages and no framework: a landing page that explains the language and
tells you how to install it, and the playground beside it so anyone can try
the language before installing anything at all.

Everything on the landing page is generated from the project itself — the
version, the built-in function count, the number of tests, the lessons — so
the site cannot quietly drift away from what the language actually is.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
REPO = "https://github.com/BahromPython/tajiklang"


def _utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def project_facts() -> dict[str, str]:
    """Read the numbers off the project rather than typing them into HTML."""
    sys.path.insert(0, str(ROOT))
    from tajiklang import __version__
    from tajiklang.interpreter import Interpreter

    builtins = len(Interpreter([], lambda _: None).builtins.values)

    tests = 0
    for path in (ROOT / "tests").glob("test_*.py"):
        tests += len(re.findall(r"\n    def test_", path.read_text(encoding="utf-8")))

    lessons = len(
        re.findall(
            r"^## Дарси ",
            (ROOT / "docs" / "дарсҳо.md").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    examples = len(list((ROOT / "examples").glob("*.tj")))

    return {
        "version": __version__,
        "builtins": str(builtins),
        "tests": str(tests),
        "lessons": str(lessons),
        "examples": str(examples),
    }


PAGE = """<!doctype html>
<html lang="tg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TajikLang — забони барномасозӣ бо забони тоҷикӣ</title>
<meta name="description" content="Забони барномасозӣ, ки калимаҳо, хатогиҳо ва
тартиби алифбои он тоҷикӣ мебошанд. Барои хонандагони тоҷикзабон.">
<meta property="og:title" content="TajikLang">
<meta property="og:description" content="Забони барномасозӣ бо забони тоҷикӣ.">
<style>
  :root {{
    --ink: #11161b; --soft: #5c6773; --line: #e2e6ea;
    --bg: #ffffff; --panel: #f7f9fa; --accent: #0f7b5f; --accent-ink: #fff;
    --code: ui-monospace, "Cascadia Code", "Segoe UI Mono", Consolas, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --ink: #e9edf1; --soft: #97a3b0; --line: #262d35;
      --bg: #0f1317; --panel: #161c22; --accent: #35b48b; --accent-ink: #06120d;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 17px/1.65 system-ui, "Segoe UI", Roboto, sans-serif;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 0 22px; }}
  header {{ padding: 72px 0 40px; border-bottom: 1px solid var(--line); }}
  h1 {{ font-size: 44px; margin: 0 0 6px; letter-spacing: -0.02em; }}
  .tag {{ font-size: 21px; color: var(--soft); margin: 0 0 26px; }}
  .cta {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  a.btn {{
    display: inline-block; padding: 12px 22px; border-radius: 10px;
    text-decoration: none; font-weight: 600; border: 1px solid var(--line);
    color: var(--ink); background: var(--panel);
  }}
  a.btn.primary {{
    background: var(--accent); color: var(--accent-ink); border-color: transparent;
  }}
  .stats {{
    display: flex; flex-wrap: wrap; gap: 26px; margin: 34px 0 0;
    color: var(--soft); font-size: 15px;
  }}
  .stats b {{ color: var(--ink); font-size: 20px; display: block; }}
  section {{ padding: 48px 0; border-bottom: 1px solid var(--line); }}
  h2 {{ font-size: 27px; margin: 0 0 14px; letter-spacing: -0.01em; }}
  h3 {{ font-size: 19px; margin: 28px 0 8px; }}
  p {{ margin: 0 0 14px; }}
  pre {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 12px;
    padding: 16px 18px; overflow-x: auto; font-family: var(--code);
    font-size: 14.5px; line-height: 1.6; margin: 0 0 16px;
  }}
  code {{ font-family: var(--code); font-size: 0.92em; }}
  ul {{ padding-right: 22px; padding-left: 22px; }}
  li {{ margin-bottom: 7px; }}
  .grid {{ display: grid; gap: 22px; grid-template-columns: 1fr 1fr; }}
  @media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px;
    background: var(--panel);
  }}
  .card h3 {{ margin-top: 0; }}
  footer {{ padding: 40px 0 70px; color: var(--soft); font-size: 15px; }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>

<div class="wrap">
<header>
  <h1>TajikLang</h1>
  <p class="tag">Забони барномасозӣ бо забони тоҷикӣ.</p>
  <div class="cta">
    <a class="btn primary" href="playground.html">Дар браузер санҷед</a>
    <a class="btn" href="#насб">Насб кардан</a>
    <a class="btn" href="{repo}">GitHub</a>
  </div>
  <div class="stats">
    <div><b>{version}</b>версия</div>
    <div><b>{builtins}</b>функсияи тайёр</div>
    <div><b>{lessons}</b>дарс бо тоҷикӣ</div>
    <div><b>{examples}</b>мисол</div>
    <div><b>{tests}</b>санҷиш</div>
  </div>
</header>

<section>
  <h2>Барнома бо забони модарӣ</h2>
  <pre>қолиб Донишҷӯ:
    функсия оғоз(худ, ном, баҳо):
        худ.ном = ном
        худ.баҳо = баҳо

    функсия хулоса(худ):
        агар худ.баҳо &gt;= 4.5:
            баргардон "аъло"
        баргардон "хуб"

бигзор синф = [
    Донишҷӯ("Яқубов", 4.75),
    Донишҷӯ("Ғафуров", 3.5),
]

функсия номи(д):
    баргардон д.ном

барои д аз тартиб_бо(синф, номи):
    навис(д.ном, "—", д.хулоса())</pre>
  <p>Ҳеҷ калимаи англисӣ нест — на дар барнома, на дар хатогиҳо.</p>
</section>

<section>
  <h2>Се чиз, ки забонҳои дигар намекунанд</h2>

  <h3>1. Барнома пеш аз иҷро санҷида мешавад</h3>
  <p>Python хатои имлоиро танҳо вақте меёбад, ки он сатр иҷро шавад.
     TajikLang ҳамаи хатоҳоро <b>пеш аз он ки чизе чоп шавад</b> нишон
     медиҳад — ва ҳамаашро якбора.</p>
  <pre>Хатои санҷиш (CheckError) (сатри 3, сутуни 11):

        навис(нмо)
              ^

Номи "нмо" муайян нашудааст.
Маслиҳат: Оё шумо "ном" -ро дар назар доштед?

Ҳамагӣ 2 хато. Барнома иҷро нашуд.</pre>

  <h3>2. Ҳисоби даҳӣ</h3>
  <pre>навис(0.1 + 0.2)          # 0.3
навис(0.1 + 0.2 == 0.3)   # рост</pre>
  <p>Дар Python, C, Java ва JavaScript ҷавоб <code>0.30000000000000004</code>
     ва <code>false</code> аст. Ҳисоби мактабӣ даҳӣ аст — забон низ.</p>

  <h3>3. «чаро» — саволе, ки дигар забонҳо ҷавоб намедиҳанд</h3>
  <pre>бигзор ҷамъ = 0
барои i аз 1 то 3:
    ҷамъ += i
чаро(ҷамъ)</pre>
  <pre>Тағйирёбандаи "ҷамъ":
    сатри 1    →  0    (эълон)
    сатри 3    →  1    (ивазкунӣ)
    сатри 3    →  3    (ивазкунӣ)
    сатри 3    →  6    (ивазкунӣ)</pre>
</section>

<section>
  <h2>Тоҷикӣ, на тарҷума</h2>
  <div class="grid">
    <div class="card">
      <h3>Тартиби алифбои тоҷикӣ</h3>
      <p>Дар Unicode ҳарфҳои <code>ғ ӣ қ ӯ ҳ ҷ</code> баъд аз <code>я</code>
         меоянд, бинобар ин ҳар забони дигар рӯйхати синфро нодуруст тартиб
         медиҳад. Дар TajikLang «Ғафуров» пеш аз «Яқубов» меистад.</p>
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

<section id="насб">
  <h2>Насб кардан</h2>

  <h3>Ҳеҷ насб лозим нест</h3>
  <p><a href="playground.html">Майдончаи браузерӣ</a> тамоми забонро дар як
     саҳифа иҷро мекунад. Барои мактабҳо ин роҳи соддатарин аст.</p>

  <h3>Дар компютер</h3>
  <pre>pip install git+{repo}.git
tajik барнома.tj
tajik                      # реҷаи интерактивӣ</pre>

  <h3>Аз манбаъ</h3>
  <pre>git clone {repo}.git
cd tajiklang
python main.py examples/журнал.tj</pre>

  <h3>VS Code</h3>
  <pre>py tools/build_vsix.py
code --install-extension dist/tajiklang-{version}.vsix</pre>
  <p>Ранга кардани синтаксис, фосилаи дурусти 4 холигӣ, ва
     <b>Ctrl+Shift+B</b> барои иҷро.</p>

  <h3>Муҳаррири худӣ</h3>
  <pre>py -m tajiklang.ide</pre>
  <p>Муҳаррири оддӣ бо дарахти файлҳо, ранга кардан, панели хатоҳо ва тугмаи
     иҷро — танҳо бо Python, бе ягон китобхонаи иловагӣ.</p>
</section>

<section>
  <h2>Омӯзиш</h2>
  <ul>
    <li><a href="{repo}/blob/main/docs/дарсҳо.md">{lessons} дарс бо забони
        тоҷикӣ</a> — аз «Салом Тоҷикистон» то қолибҳо ва саҳифаи интернетӣ</li>
    <li><a href="{repo}/blob/main/docs/чӣ_тавр_кор_мекунад.md">Забон дар дохил
        чӣ тавр кор мекунад</a> — лексер, парсер, дарахт, интерпретатор</li>
    <li><a href="{repo}/blob/main/LANGUAGE_SPEC.md">Мушаххасоти забон</a>
        (бо англисӣ)</li>
    <li><a href="{repo}/tree/main/examples">{examples} мисоли тайёр</a></li>
  </ul>
</section>

<section>
  <h2>Барои муаллимон</h2>
  <p>Файли <a href="{repo}/blob/main/docs/ТАРҶУМА.md">ТАРҶУМА.md</a> рӯйхати
     ҳамаи матнҳоест, ки забон ба донишҷӯ нишон медиҳад. Агар шумо тоҷикзабон
     бошед ва бист дақиқа вақт дошта бошед, онро хонед ва ҷумлаҳои носуфтаро
     ислоҳ кунед. Ин муфидтарин кӯмакест, ки ба ин лоиҳа расонида метавонед.</p>
</section>

<footer>
  <p>TajikLang {version} — MIT. Сарчашма дар
     <a href="{repo}">GitHub</a>.</p>
</footer>
</div>

</body>
</html>
"""


def main() -> int:
    _utf8_stdout()
    facts = project_facts()

    # The playground is generated from the interpreter, so rebuild it here
    # rather than trusting whatever is on disk.
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_playground.py")],
        check=True,
        cwd=ROOT,
    )

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(PAGE.format(repo=REPO, **facts), encoding="utf-8")
    (SITE / "playground.html").write_text(
        (ROOT / "playground" / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    # GitHub Pages must not run these through Jekyll.
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    total = sum(path.stat().st_size for path in SITE.iterdir() if path.is_file())
    print(
        f"site/ — index.html + playground.html, {total / 1024:.0f} KB "
        f"(версия {facts['version']}, {facts['tests']} санҷиш)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

// асос.js — ёрирасони JavaScript барои коди тарҷумашуда.
//
// Ҳадаф: маънои TajikLang дар JavaScript низ ҳамон бошад. Се ваъдаи забон
// махсусан осебпазиранд ва дар ин ҷо нигоҳ дошта мешаванд:
//
//   1. Рақамҳо дақиқанд:  0.1 + 0.2 == 0.3
//   2. Шарт бояд мантиқӣ бошад: `агар 5:` хатост, на «рост»
//   3. Ҳарфҳои тоҷикӣ тартиби худро доранд: ғ баъди г меояд, на баъди я

'use strict';

const АЛИФБО = "абвгғдеёжзиӣйкқлмнопрстуӯфхҳчҷшъэюя";
const ҶОЙҲО = new Map();
for (let i = 0; i < АЛИФБО.length; i++) {
  ҶОЙҲО.set(АЛИФБО[i], i);
  ҶОЙҲО.set(АЛИФБО[i].toUpperCase(), i);
}

function хато(паём) {
  const e = new Error(паём);
  e.тоҷикӣ = true;
  throw e;
}

// --- рақамҳои дақиқ --------------------------------------------------------
// JavaScript танҳо рақамҳои дуӣ дорад, ки 0.1 + 0.2 = 0.30000000000000004
// медиҳанд. Ин ҷо ҳисоб бо адади бутуни миқёсшуда иҷро мешавад, то натиҷа
// ҳамон чизе бошад, ки хонанда дар дафтар менависад.

function даҳӣ(x) {
  const s = String(x);
  const i = s.indexOf('.');
  return i < 0 ? 0 : s.length - i - 1;
}

function миқёс(x, p) {
  return Math.round(x * Math.pow(10, p));
}

function __ҷамъ(a, b) {
  if (typeof a === 'string' && typeof b === 'string') return a + b;
  if (Array.isArray(a) && Array.isArray(b)) return a.concat(b);
  if (typeof a === 'number' && typeof b === 'number') {
    const p = Math.max(даҳӣ(a), даҳӣ(b));
    return (миқёс(a, p) + миқёс(b, p)) / Math.pow(10, p);
  }
  хато('Ҷамъи ' + __навъ(a) + ' ва ' + __навъ(b) + ' мумкин нест.');
}

function __тарҳ(a, b) {
  if (typeof a !== 'number' || typeof b !== 'number') {
    хато('Тарҳи ' + __навъ(a) + ' ва ' + __навъ(b) + ' мумкин нест.');
  }
  const p = Math.max(даҳӣ(a), даҳӣ(b));
  return (миқёс(a, p) - миқёс(b, p)) / Math.pow(10, p);
}

function __зарб(a, b) {
  if (typeof a !== 'number' || typeof b !== 'number') {
    хато('Зарби ' + __навъ(a) + ' ва ' + __навъ(b) + ' мумкин нест.');
  }
  const pa = даҳӣ(a), pb = даҳӣ(b);
  return (миқёс(a, pa) * миқёс(b, pb)) / Math.pow(10, pa + pb);
}

function __тақсим(a, b) {
  if (typeof a !== 'number' || typeof b !== 'number') {
    хато('Тақсими ' + __навъ(a) + ' ва ' + __навъ(b) + ' мумкин нест.');
  }
  if (b === 0) хато('Тақсим ба сифр мумкин нест.');
  return Number((a / b).toPrecision(15));
}

function __бақия(a, b) {
  if (b === 0) хато('Тақсим ба сифр мумкин нест.');
  const p = Math.max(даҳӣ(a), даҳӣ(b));
  const f = Math.pow(10, p);
  return (((миқёс(a, p) % миқёс(b, p)) + миқёс(b, p)) % миқёс(b, p)) / f;
}

// --- шарт ------------------------------------------------------------------
// Дар TajikLang ҳеҷ чиз «худ ба худ» рост нест. Ин хатогиҳои хомӯшро
// пешгирӣ мекунад: `агар рӯйхат:` бояд `агар дарозӣ(рӯйхат) > 0:` бошад.

function __шарт(x) {
  if (x === true || x === false) return x;
  хато('Шарт бояд рост ё дурӯғ бошад, на ' + __навъ(x) + '.');
}

// --- муқоиса ---------------------------------------------------------------

function __баробар(a, b) {
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (!__баробар(a[i], b[i])) return false;
    return true;
  }
  return a === b;
}

// Калиди як ҳарф — се рақам, ки аз чап ба рост муқоиса мешаванд:
//
//   1. гурӯҳ    — 0 барои ҳарфи ғайритоҷикӣ (аломат, рақам, лотинӣ), 1 барои
//                 ҳарфи тоҷикӣ. Пас аломатҳо аввал меоянд.
//   2. ҷой      — рақами ҳарф дар алифбо, ё рамзи Unicode барои дигарон.
//   3. ҳолат    — 0 барои ҳарфи калон, 1 барои хурд, то «Анор» пеш аз «анор»
//                 биёяд, вале аз он ҷудо нашавад.
//
// Ин ҳамон тартибест, ки тарҷумони асосӣ дорад. Агар ин ҷо фарқ мекард,
// як барнома дар ду муҳит ду ҷавоби гуногун медод.
function калиди_ҳарф(ҳарф) {
  const хурд = ҳарф.toLowerCase();
  const ҷо = ҶОЙҲО.get(хурд);
  if (ҷо !== undefined) return [1, ҷо, ҳарф !== хурд ? 0 : 1];
  return [0, ҳарф.codePointAt(0), 0];
}

function матнро_муқоиса(a, b) {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i++) {
    const x = калиди_ҳарф(a[i]), y = калиди_ҳарф(b[i]);
    for (let ҷ = 0; ҷ < 3; ҷ++) {
      if (x[ҷ] !== y[ҷ]) return x[ҷ] < y[ҷ] ? -1 : 1;
    }
  }
  if (a.length === b.length) return 0;
  return a.length < b.length ? -1 : 1;
}

function __муқоиса(a, b, аломат) {
  let c;
  if (typeof a === 'string' && typeof b === 'string') {
    c = матнро_муқоиса(a, b);
  } else if (typeof a === 'number' && typeof b === 'number') {
    c = a < b ? -1 : (a > b ? 1 : 0);
  } else {
    хато('Муқоисаи ' + __навъ(a) + ' ва ' + __навъ(b) + ' мумкин нест.');
  }

  if (аломат === '<') return c < 0;
  if (аломат === '>') return c > 0;
  if (аломат === '<=') return c <= 0;
  return c >= 0;
}

// --- дастрасӣ --------------------------------------------------------------

function __унсур(чиз, калид) {
  if (typeof чиз === 'string' || Array.isArray(чиз)) {
    let i = калид;
    if (i < 0) i += чиз.length;
    if (i < 0 || i >= чиз.length) {
      хато('Ҷои ' + калид + ' берун аз ҳудуд аст (дарозӣ ' + чиз.length + ').');
    }
    return чиз[i];
  }
  if (чиз && typeof чиз === 'object') {
    if (!(калид in чиз)) хато('Калиди "' + калид + '" ёфт нашуд.');
    return чиз[калид];
  }
  хато('Аз ' + __навъ(чиз) + ' унсур гирифтан мумкин нест.');
}

function __дарак(аз, то) {
  const р = [];
  if (аз <= то) {
    for (let i = аз; i <= то; i++) р.push(i);
  } else {
    for (let i = аз; i >= то; i--) р.push(i);
  }
  return р;
}

function __рӯйхат(чиз) {
  if (Array.isArray(чиз)) return чиз;
  if (typeof чиз === 'string') return Array.from(чиз);
  if (чиз && typeof чиз === 'object') return Object.keys(чиз);
  хато('Аз ' + __навъ(чиз) + ' давр гирифтан мумкин нест.');
}

// --- чоп -------------------------------------------------------------------

function __навъ(x) {
  if (x === null || x === undefined) return 'холӣ';
  if (x === true || x === false) return 'мантиқӣ';
  if (typeof x === 'number') return 'рақам';
  if (typeof x === 'string') return 'матн';
  if (Array.isArray(x)) return 'рӯйхат';
  if (typeof x === 'function') return 'функсия';
  return 'луғат';
}

function матн_кун(x, дарун) {
  if (x === null || x === undefined) return 'холӣ';
  if (x === true) return 'рост';
  if (x === false) return 'дурӯғ';
  if (typeof x === 'string') return дарун ? '"' + x + '"' : x;
  if (typeof x === 'number') return String(x);
  if (Array.isArray(x)) return '[' + x.map(v => матн_кун(v, true)).join(', ') + ']';
  if (typeof x === 'function') return '<функсия>';
  return '{' + Object.keys(x).map(k => '"' + k + '": ' + матн_кун(x[k], true)).join(', ') + '}';
}

function __навис(...чизҳо) {
  console.log(чизҳо.map(v => матн_кун(v, false)).join(' '));
  return null;
}

// --- функсияҳои тайёр ------------------------------------------------------

function __дарозӣ(x) {
  if (typeof x === 'string' || Array.isArray(x)) return x.length;
  if (x && typeof x === 'object') return Object.keys(x).length;
  хато('Дарозии ' + __навъ(x) + ' муайян нест.');
}

function __илова(рӯйхат, чиз) {
  рӯйхат.push(чиз);
  return null;
}

function __тартиб(р) {
  const н = р.slice();
  н.sort((a, b) => (typeof a === 'string' ? матнро_муқоиса(a, b) : a - b));
  return н;
}

function __баръакс(р) {
  if (typeof р === 'string') return Array.from(р).reverse().join('');
  return р.slice().reverse();
}

function __ҷамъи(р) {
  let s = 0;
  for (const v of р) s = __ҷамъ(s, v);
  return s;
}

function __миёна(р) {
  if (р.length === 0) хато('Миёнаи рӯйхати холӣ вуҷуд надорад.');
  return __тақсим(__ҷамъи(р), р.length);
}

function __калонтарин(р) {
  if (р.length === 0) хато('Рӯйхат холӣ аст.');
  return р.reduce((a, b) => (__муқоиса(b, a, '>') ? b : a));
}

function __хурдтарин(р) {
  if (р.length === 0) хато('Рӯйхат холӣ аст.');
  return р.reduce((a, b) => (__муқоиса(b, a, '<') ? b : a));
}

function __ба_матн(x) {
  return матн_кун(x, false);
}

function __ба_рақам(x) {
  if (typeof x === 'number') return x;
  const n = Number(String(x).trim());
  if (Number.isNaN(n)) хато('"' + x + '" ба рақам табдил намеёбад.');
  return n;
}

function __калон(м) { return String(м).toUpperCase(); }
function __хурд(м) { return String(м).toLowerCase(); }
function __такрор(м, н) { return String(м).repeat(н); }

function __рақамҳо(м) {
  return Array.from(String(м)).filter(c => c >= '0' && c <= '9').join('');
}

function __дорад(чиз, чӣ) {
  if (Array.isArray(чиз)) return чиз.some(v => __баробар(v, чӣ));
  if (typeof чиз === 'string') return чиз.includes(чӣ);
  if (чиз && typeof чиз === 'object') return чӣ in чиз;
  return false;
}

// Ҳудуди [аз, то] — ҳар ду тараф дохил мешаванд, чун дар забони асосӣ.
function __буриш(чиз, аз, то) {
  const н = чиз.length;
  let a = аз < 0 ? аз + н : аз;
  let b = то < 0 ? то + н : то;
  if (a < 0) a = 0;
  if (b >= н) b = н - 1;
  if (a > b) return typeof чиз === 'string' ? '' : [];
  return чиз.slice(a, b + 1);
}

function __ёфтан(чиз, чӣ) {
  if (Array.isArray(чиз)) {
    for (let i = 0; i < чиз.length; i++) if (__баробар(чиз[i], чӣ)) return i;
    return null;
  }
  const i = String(чиз).indexOf(чӣ);
  return i < 0 ? null : i;
}

function __тоза(м) { return String(м).trim(); }
function __сар_мешавад(м, п) { return String(м).startsWith(п); }
function __тамом_мешавад(м, п) { return String(м).endsWith(п); }
function __ҷудо(м, ҷ) { return String(м).split(ҷ); }
function __пайваст(р, ҷ) { return р.map(v => матн_кун(v, false)).join(ҷ); }
function __иваз(м, аз, ба) { return String(м).split(аз).join(ба); }
function __ҳарфҳо(м) { return Array.from(String(м)); }
function __нусха(x) { return Array.isArray(x) ? x.slice() : Object.assign({}, x); }
function __калидҳо(л) { return Object.keys(л); }
function __қиматҳо(л) { return Object.keys(л).map(k => л[k]); }
function __шумор(чиз, чӣ) {
  if (Array.isArray(чиз)) return чиз.filter(v => __баробар(v, чӣ)).length;
  return String(чиз).split(чӣ).length - 1;
}
function __васеъ(р, дигар) { for (const v of дигар) р.push(v); return null; }
function __холӣ_аст(x) { return __дарозӣ(x) === 0; }

function __хориҷ(р, ҷо) {
  let i = ҷо === undefined || ҷо === null ? р.length - 1 : ҷо;
  if (i < 0) i += р.length;
  if (i < 0 || i >= р.length) {
    хато('Ҷои ' + ҷо + ' берун аз ҳудуд аст (дарозӣ ' + р.length + ').');
  }
  return р.splice(i, 1)[0];
}

function __дарҷ(л, калид, қимат) { л[калид] = қимат; return null; }
function __мутлақ(x) { return Math.abs(x); }
function __бутун(x) { return Math.trunc(x); }
function __гирд(x, ҷ) { const f = Math.pow(10, ҷ || 0); return Math.round(x * f) / f; }

module.exports = {
  __ҷамъ, __тарҳ, __зарб, __тақсим, __бақия, __шарт, __баробар, __муқоиса,
  __унсур, __дарак, __рӯйхат, __навис, __навъ, __дарозӣ, __илова, __тартиб,
  __баръакс, __ҷамъи, __миёна, __калонтарин, __хурдтарин, __ба_матн,
  __ба_рақам, __калон, __хурд, __такрор, __рақамҳо, __дорад,
  __буриш, __ёфтан, __тоза, __сар_мешавад, __тамом_мешавад, __ҷудо,
  __пайваст, __иваз, __ҳарфҳо, __нусха, __калидҳо, __қиматҳо, __шумор,
  __васеъ, __холӣ_аст, __хориҷ, __дарҷ, __мутлақ, __бутун, __гирд,
};

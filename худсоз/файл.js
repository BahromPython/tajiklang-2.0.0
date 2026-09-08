// файл.js — модули «файл» барои муҳити Node.js.
//
// Ҳамон ду амале, ки модули файли забони асосӣ дорад, то коди тарҷумашуда
// ҳеҷ фарқеро ҳис накунад.

'use strict';

const fs = require('fs');

function хондан(ном) {
  return fs.readFileSync(ном, 'utf8');
}

function навиштан(ном, матн) {
  fs.writeFileSync(ном, матн, 'utf8');
  return null;
}

function илова_кардан(ном, матн) {
  fs.appendFileSync(ном, матн, 'utf8');
  return null;
}

function ҳаст(ном) {
  return fs.existsSync(ном);
}

module.exports = { хондан, навиштан, илова_кардан, ҳаст };

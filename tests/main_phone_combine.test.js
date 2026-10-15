const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function loadMain() {
  const documentStub = {
    documentElement: { classList: { add() {} } },
    getElementById() { return null; },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    addEventListener() {},
    createElement() {
      return {
        textContent: '', innerHTML: '',
        setAttribute() {}, getAttribute() { return null; },
      };
    },
  };
  const context = {
    window: { fetch: async () => ({ ok: true, json: async () => ({}) }) },
    document: documentStub,
    console,
    setTimeout,
    clearTimeout,
    MutationObserver: class {},
    lucide: { createIcons() {} },
    t: (k) => k,
    escapeHtml: (v) => v,
    FormData: class { constructor() { this._d = {}; } append() {} entries() { return []; } },
    Headers: class { constructor() {} has() { return false; } set() {} },
  };
  context.window.document = documentStub;
  context.window.window = context.window;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('static/js/main.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('static/js/forms.js', 'utf8'), context);
  return context;
}

const context = loadMain();

test('combineCountryAreaPhone con provincia no duplica el area (Fase 0 item 1)', () => {
  const cases = [
    ['9 11 2345 6789', '+54 9 11 23456789'],
    ['15 11 2345 6789', '+54 9 11 23456789'],
    ['11 2345 6789', '+54 9 11 23456789'],
    ['011 15 2345 6789', '+54 9 11 23456789'],
    ['+54 9 11 2345 6789', '+54 9 11 23456789'],
  ];
  for (const [input, expected] of cases) {
    assert.equal(context.window.combineCountryAreaPhone('+54', '11', input), expected, `input: ${input}`);
  }
});

test('combineCountryAreaPhone sin provincia normaliza a +54 9... (Fase 0 item 1)', () => {
  const cases = [
    ['11 2345 6789', '+54 91123456789'],
    ['011 2345 6789', '+54 91123456789'],
    ['+54 9 11 2345 6789', '+54 91123456789'],
  ];
  for (const [input, expected] of cases) {
    assert.equal(context.window.combineCountryAreaPhone('+54', '', input), expected, `input: ${input}`);
  }
});

test('combineCountryAreaPhone respeta otras banderas sin tocar el numero', () => {
  assert.equal(
    context.window.combineCountryAreaPhone('+52', '', '55 1234 5678'),
    '+52 55 1234 5678'
  );
});

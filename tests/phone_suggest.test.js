const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const DB = {
  '+54': [
    { code: '11', city: 'Buenos Aires / CABA', province: 'CABA' },
    { code: '3541', city: 'Villa Carlos Paz', province: 'Córdoba' },
    { code: '388', city: 'Salta', province: 'Salta' },
  ],
  '+598': [
    { code: '2', city: 'Montevideo', province: 'Montevideo' },
    { code: '42', city: 'Punta del Este', province: 'Maldonado' },
  ],
  '+56': [
    { code: '2', city: 'Santiago', province: 'Metropolitana de Santiago' },
  ],
  '+55': [
    { code: '11', city: 'São Paulo', province: 'São Paulo' },
  ],
  '+595': [
    { code: '21', city: 'Asunción', province: 'Central' },
  ],
  '+591': [
    { code: '2', city: 'La Paz', province: 'La Paz' },
    { code: '3', city: 'Santa Cruz', province: 'Santa Cruz' },
  ],
  '+57': [
    { code: '1', city: 'Bogotá', province: 'Cundinamarca' },
    { code: '4', city: 'Medellín', province: 'Antioquia' },
  ],
  '+52': [
    { code: '55', city: 'Ciudad de México', province: 'CDMX' },
  ],
  '+34': [
    { code: '91', city: 'Madrid', province: 'Madrid' },
  ],
  '+1': [
    { code: '212', city: 'New York', province: 'NY' },
  ],
};

function loadPhoneSuggest() {
  const context = { window: {} };
  context.window.window = context.window;
  context.window.__PHONE_DB_BY_COUNTRY = DB;
  context.document = {
    createElement(tag) {
      return {
        tagName: tag,
        value: '',
        textContent: '',
        innerHTML: '',
        selected: false,
        options: [],
        setAttribute() {},
        appendChild() {},
      };
    },
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('static/js/phone-suggest.js', 'utf8'), context);
  return vm.runInContext('PhoneSuggest', context);
}

test('suggestNationalNumber per country', () => {
  const P = loadPhoneSuggest();
  const cases = [
    ['+54', '93541388368', '+54 9 3541 388 368'],
    ['+54', '153541388368', '+54 9 3541 388 368'],
    ['+54', '91158230000', '+54 9 11 5823 0000'],
    ['+54', '388368', null],
    ['+598', '99123456', '+598 99 123 456'],
    ['+598', '24001234', '+598 2 400 1234'],
    ['+56', '951234567', '+56 9 5123 4567'],
    ['+56', '271234567', '+56 2 7123 4567'],
    ['+55', '11987654321', '+55 11 9 8765 4321'],
    ['+55', '1134567890', '+55 11 3456 7890'],
    ['+595', '981234567', '+595 98 123 4567'],
    ['+595', '21451234', '+595 21 451 234'],
    ['+591', '71234567', '+591 7 123 4567'],
    ['+591', '22440000', '+591 2 244 0000'],
    ['+57', '3123456789', '+57 3 123 456 789'],
    ['+57', '16012345', '+57 1 601 2345'],
    ['+52', '5512345678', '+52 55 1234 5678'],
    ['+34', '612345678', '+34 612 345 678'],
    ['+34', '912345678', '+34 91 234 5678'],
    ['+1', '2125550123', '+1 (212) 555-0123'],
  ];
  for (const [cc, digits, expected] of cases) {
    assert.equal(P.suggestNationalNumber(cc, digits), expected, `${cc} ${digits}`);
  }
});

test('isPlausible length rules', () => {
  const P = loadPhoneSuggest();
  assert.equal(P.isPlausible('+54', '93541388368'), true);
  assert.equal(P.isPlausible('+54', '388368'), false);
  assert.equal(P.isPlausible('+1', '2125550123'), true);
  assert.equal(P.isPlausible('+1', '21255501'), false);
  assert.equal(P.isPlausible('+56', '951234567'), true);
  assert.equal(P.isPlausible('+55', '11987654321'), true);
  assert.equal(P.isPlausible('+99', '12345'), false);
});

test('getRegionInfo strips mobile prefixes and resolves area', () => {
  const P = loadPhoneSuggest();
  let info = P.getRegionInfo('+54', '93541388368');
  assert.equal(info.code, '3541');
  assert.equal(info.city, 'Villa Carlos Paz');
  assert.equal(info.province, 'Córdoba');
  info = P.getRegionInfo('+54', '153541388368');
  assert.equal(info.code, '3541');
  info = P.getRegionInfo('+1', '2125550123');
  assert.equal(info.code, '212');
  assert.equal(P.getRegionInfo('+56', '912345678'), null);
  assert.equal(P.getRegionLabel('+54', '93541388368').city, 'Villa Carlos Paz');
});

test('formatNational partial formatting', () => {
  const P = loadPhoneSuggest();
  assert.equal(P.formatNational('+54', '388368'), '+54 9 388 368');
  assert.equal(P.formatNational('+54', ''), '+54');
  assert.equal(P.formatNational('+1', '212'), '+1 (212)');
  assert.equal(P.formatNational('+1', '212555'), '+1 (212) 555');
  assert.equal(P.formatNational('+34', '612345678'), '+34 612 345 678');
});

test('populateAreaSelect preserves selection and other option', () => {
  const P = loadPhoneSuggest();
  const select = {
    innerHTML: '',
    options: [
      { value: '11', textContent: 'Buenos Aires', selected: true },
      { value: 'other', textContent: 'Otra...', selected: false },
    ],
    _allOptions: ['cached'],
    appendChild(opt) { this.options.push(opt); },
  };
  P.populateAreaSelect(select, '+54');
  assert.ok(select.options.some(o => o.value === '3541'));
  assert.ok(select.options.some(o => o.value === 'other'));
  assert.ok(select.options.some(o => o.value === '11' && o.selected));
  assert.equal(select._allOptions, undefined);
});

test('populateAreaSelect falls back to other when previous not in new country', () => {
  const P = loadPhoneSuggest();
  const select = {
    innerHTML: '',
    options: [
      { value: '55', textContent: 'Ciudad de México', selected: true },
      { value: 'other', textContent: 'Otra...', selected: false },
    ],
    _allOptions: null,
    appendChild(opt) { this.options.push(opt); },
  };
  Object.defineProperty(select, 'innerHTML', {
    set() { this.options = []; },
    get() { return ''; },
  });
  P.populateAreaSelect(select, '+54');
  assert.ok(select.options.some(o => o.value === '55') === false);
  assert.ok(select.options.some(o => o.value === 'other' && o.selected));
});

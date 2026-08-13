const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function createElement(id) {
  return {
    id,
    value: '',
    textContent: '',
    innerHTML: '',
    className: '',
    hidden: false,
    checked: false,
    disabled: false,
    classList: {
      add() {},
      remove() {},
      contains() { return false; },
      toggle() { return false; }
    },
    style: {},
    dataset: {},
    options: [],
    appendChild(child) { this.options.push(child); },
    querySelectorAll() { return []; },
    setAttribute() {},
    getAttribute() { return null; },
    removeAttribute() {},
    addEventListener() {},
    focus() {},
    click() {},
  };
}

test('suggest and apply phone correction for Villa Carlos Paz', () => {
  const elements = {};
  const create = (id) => {
    const el = createElement(id);
    elements[id] = el;
    return el;
  };

  const phoneInput = create('profile-phone');
  const countryCode = create('profile-country-code');
  const provinceSelect = create('profile-province');
  const customAreaInput = create('profile-custom-area');
  const suggestionEl = create('profile-phone-suggestion');
  const previewEl = create('phone-correction-preview');
  const correctionFrom = create('correction-from');
  const correctionTo = create('correction-to');

  countryCode.value = '+54';
  provinceSelect.value = 'other';
  provinceSelect.classList.contains = (cls) => cls === 'hidden' ? false : false;
  provinceSelect.options = [{ value: '11' }, { value: '221' }, { value: 'other' }];
  provinceSelect.querySelectorAll = () => provinceSelect.options;

  const documentStub = {
    getElementById(id) { return elements[id] || null; },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    addEventListener() {},
    createElement(tag) {
      return {
        tagName: tag,
        value: '',
        textContent: '',
        innerHTML: '',
        selected: false,
        setAttribute() {},
        getAttribute() { return null; },
        appendChild() {},
      };
    },
  };

  const context = {
    window: {},
    document: documentStub,
    console,
    setTimeout,
    clearTimeout,
    MutationObserver: class {},
    lucide: { createIcons() {} },
    t: () => '',
    escapeHtml: (value) => value,
  };
  context.window.document = documentStub;
  context.window.window = context.window;
  context.window.__PHONE_DB_BY_COUNTRY = {
    '+54': [
      { code: '11', city: 'Buenos Aires / CABA', province: 'CABA' },
      { code: '3541', city: 'Villa Carlos Paz', province: 'Córdoba' },
    ],
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('static/js/phone-suggest.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('static/js/profile.js', 'utf8'), context);

  phoneInput.value = '3541388368';
  context.validateProfilePhone();

  const suggestion = vm.runInContext('_lastPhoneSuggestion', context);
  assert.equal(suggestion, '+54 9 3541 388 368');
  context.showPhoneCorrection();
  assert.equal(correctionTo.textContent, '+54 9 3541 388 368');

  context.applyPhoneCorrection();
  assert.equal(phoneInput.value, '9 3541 388 368');
  assert.equal(customAreaInput.value, '3541');
});

test('applyProvincePrefix no acumula codigos de area al cambiar de provincia varias veces', () => {
  const elements = {};
  const create = (id) => {
    const el = createElement(id);
    elements[id] = el;
    return el;
  };

  const phoneInput = create('profile-phone');
  const countryCode = create('profile-country-code');
  const provinceSelect = create('profile-province');
  const customAreaInput = create('profile-custom-area');

  countryCode.value = '+54';
  provinceSelect.options = [
    { value: '11' }, { value: '351' }, { value: '221' }, { value: 'other' }
  ];

  const documentStub = {
    getElementById(id) { return elements[id] || null; },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    addEventListener() {},
    createElement(tag) {
      return {
        tagName: tag, value: '', textContent: '', innerHTML: '', selected: false,
        setAttribute() {}, getAttribute() { return null; }, appendChild() {},
      };
    },
  };

  const context = {
    window: {},
    document: documentStub,
    console,
    setTimeout,
    clearTimeout,
    MutationObserver: class {},
    lucide: { createIcons() {} },
    t: () => '',
    escapeHtml: (value) => value,
  };
  context.window.document = documentStub;
  context.window.window = context.window;
  context.window.__PHONE_DB_BY_COUNTRY = {
    '+54': [
      { code: '11', city: 'Buenos Aires / CABA', province: 'CABA' },
      { code: '351', city: 'Córdoba', province: 'Córdoba' },
      { code: '221', city: 'La Plata', province: 'Buenos Aires' },
    ],
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('static/js/phone-suggest.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('static/js/profile.js', 'utf8'), context);

  phoneInput.value = '4123456';

  provinceSelect.value = '351';
  context.applyProvincePrefix();
  provinceSelect.value = '11';
  context.applyProvincePrefix();
  provinceSelect.value = '221';
  context.applyProvincePrefix();

  const finalDigits = phoneInput.value.replace(/\D/g, '');
  assert.equal(finalDigits.length, 11);
  assert.equal(phoneInput.value, '221 9 4123456');
});

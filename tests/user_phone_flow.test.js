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

const DB = {
  '+54': [
    { code: '11', city: 'Buenos Aires / CABA', province: 'CABA' },
    { code: '3541', city: 'Villa Carlos Paz', province: 'Córdoba' },
  ],
  '+52': [
    { code: '55', city: 'Ciudad de México', province: 'CDMX' },
  ],
};

function buildContext(fetchImpl) {
  const elements = {};
  const create = (id) => {
    const el = createElement(id);
    elements[id] = el;
    return el;
  };

  const phoneInput = create('phone-input');
  const countrySelect = create('country-code-select');
  const provinceSelect = create('phone-province');
  const errorMsg = create('phone-error-msg');
  const saveBtn = create('save-phone-btn');
  const suggestionEl = create('user-phone-suggestion');
  const previewEl = create('user-correction-preview');
  const correctionFrom = create('user-correction-from');
  const correctionTo = create('user-correction-to');

  const countryOptions = ['+52', '+54'].map((value) => ({ value, selected: false }));
  countrySelect.querySelectorAll = () => countryOptions;

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
    t: (key) => key,
    escapeHtml: (value) => value,
    showToast() {},
    showProvinceSearchToggle() {},
    fetch: fetchImpl,
  };
  context.window.document = documentStub;
  context.window.window = context.window;
  context.window.__PHONE_DB_BY_COUNTRY = DB;
  vm.createContext(context);

  const run = (file) => vm.runInContext(fs.readFileSync(file, 'utf8'), context);

  return { context, elements, run, countryOptions };
}

test('user.js initializes area select for existing MX phone', () => {
  const { context, elements, run, countryOptions } = buildContext(() => {});
  elements['phone-input'].value = '+52 55 1234 5678';
  run('static/js/phone-suggest.js');
  run('static/js/user.js');
  assert.ok(countryOptions[0].selected, 'MX should be selected');
  assert.equal(elements['phone-input'].value, '55 1234 5678', 'area code must stay in display for submit');
  assert.ok(elements['phone-province'].options.some(o => o.value === '55' && o.selected));
});

test('user.js initializes AR phone keeping mobile prefix and area', () => {
  const { context, elements, run, countryOptions } = buildContext(() => {});
  elements['phone-input'].value = '+54 9 3541 388 368';
  run('static/js/phone-suggest.js');
  run('static/js/user.js');
  assert.equal(elements['phone-input'].value, '9 3541 388 368');
  assert.ok(elements['phone-province'].options.some(o => o.value === '3541' && o.selected));
});

test('user.js suggests and applies AR phone correction', () => {
  const { context, elements, run } = buildContext(() => {});
  run('static/js/phone-suggest.js');
  run('static/js/user.js');

  const countrySelect = elements['country-code-select'];
  countrySelect.value = '+54';
  elements['phone-input'].value = '3541388368';
  context.onUserPhoneInput();
  let suggestion = vm.runInContext('_lastUserPhoneSuggestion', context);
  assert.equal(suggestion, '+54 9 3541 388 368');
  context.applyUserPhoneCorrection();
  assert.equal(elements['phone-input'].value, '9 3541 388 368');
});

test('user.js savePhoneToProfile rejects implausible length', async () => {
  let fetchCalls = 0;
  const { context, elements, run } = buildContext(async () => {
    fetchCalls++;
    return { ok: true, json: async () => ({}) };
  });
  run('static/js/phone-suggest.js');
  run('static/js/user.js');

  const countrySelect = elements['country-code-select'];
  countrySelect.value = '+54';
  elements['phone-input'].value = '388368';
  await context.savePhoneToProfile();
  assert.equal(fetchCalls, 0, 'fetch must not be called for implausible phone');
  assert.equal(elements['phone-error-msg'].textContent, 'phone.incomplete_autocomplete');
});

test('user.js savePhoneToProfile sends formatted MX phone', async () => {
  let body = null;
  const { context, elements, run } = buildContext(async (url, opts) => {
    body = JSON.parse(opts.body);
    return { ok: true, json: async () => ({}) };
  });
  run('static/js/phone-suggest.js');
  run('static/js/user.js');

  const countrySelect = elements['country-code-select'];
  countrySelect.value = '+52';
  elements['phone-input'].value = '5512345678';
  await context.savePhoneToProfile();
  assert.deepEqual(body, { phone: '+52 55 1234 5678' });
});

test('user.js applyPhoneProvincePrefix no acumula codigos de area al cambiar de provincia varias veces', () => {
  const { context, elements, run } = buildContext(() => {});
  context.window.__PHONE_DB_BY_COUNTRY = {
    '+54': [
      { code: '11', city: 'Buenos Aires / CABA', province: 'CABA' },
      { code: '351', city: 'Córdoba', province: 'Córdoba' },
      { code: '221', city: 'La Plata', province: 'Buenos Aires' },
    ],
  };
  run('static/js/phone-suggest.js');
  run('static/js/user.js');

  const countrySelect = elements['country-code-select'];
  const provinceSelect = elements['phone-province'];
  const phoneInput = elements['phone-input'];
  countrySelect.value = '+54';
  provinceSelect.options = [{ value: '11' }, { value: '351' }, { value: '221' }];

  phoneInput.value = '4123456';
  provinceSelect.value = '351';
  context.applyPhoneProvincePrefix();
  provinceSelect.value = '11';
  context.applyPhoneProvincePrefix();
  provinceSelect.value = '221';
  context.applyPhoneProvincePrefix();

  const finalDigits = phoneInput.value.replace(/\D/g, '');
  assert.equal(finalDigits.length, 11);
});

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
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('static/js/profile.js', 'utf8'), context);

  phoneInput.value = '3541388368';
  context.validateProfilePhone();

  const suggestion = vm.runInContext('_lastPhoneSuggestion', context);
  assert.equal(suggestion, '+54 3541 9 388368');
  context.showPhoneCorrection();
  assert.equal(correctionTo.textContent, '+54 3541 9 388368');

  context.applyPhoneCorrection();
  assert.equal(phoneInput.value, '3541 9 388368');
  assert.equal(customAreaInput.value, '3541');
});

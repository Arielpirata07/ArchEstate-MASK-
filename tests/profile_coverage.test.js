const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function createElement(id) {
  const classes = new Set();
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
      add(c) { classes.add(c); },
      remove(c) { classes.delete(c); },
      contains(c) { return classes.has(c); },
      toggle(c, force) {
        const shouldAdd = force !== undefined ? force : !classes.has(c);
        if (shouldAdd) classes.add(c); else classes.delete(c);
        return shouldAdd;
      },
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

function buildContext(fetchImpl) {
  const elements = {};
  const create = (id) => { const el = createElement(id); elements[id] = el; return el; };

  create('coverage-zone-input');
  create('coverage-zones-list');
  create('coverage-zones-count').textContent = '0/20';
  create('coverage-zone-add-btn');
  create('coverage-zone-error');
  create('coverage-fallback-hint');
  create('coverage-save-msg');
  create('coverage-save-error');
  create('coverage-save-btn');
  create('coverage-save-btn-label');

  // Checkboxes de especialidad: simulamos 3 opciones fijas, como las que
  // renderiza el template desde form_options('property_type').
  const specialtyCheckboxes = ['departamento', 'casa', 'terreno'].map(value => {
    const cb = createElement('specialty-' + value);
    cb.value = value;
    cb.checked = false;
    return cb;
  });

  const documentStub = {
    getElementById(id) { return elements[id] || null; },
    querySelectorAll(selector) {
      if (selector === '.coverage-specialty-checkbox') return specialtyCheckboxes;
      if (selector === '.coverage-specialty-checkbox:checked') return specialtyCheckboxes.filter(cb => cb.checked);
      return [];
    },
    querySelector() { return null; },
    addEventListener() {},
  };

  const context = {
    window: {},
    document: documentStub,
    console,
    setTimeout,
    clearTimeout,
    fetch: fetchImpl,
    MutationObserver: class {},
    lucide: { createIcons() {} },
    t: (key) => key,
    escapeHtml: (v) => v,
  };
  context.window.document = documentStub;
  context.window.window = context.window;
  context.window.fetch = fetchImpl;
  vm.createContext(context);

  return {
    context, elements, specialtyCheckboxes,
    run(path) { vm.runInContext(fs.readFileSync(path, 'utf8'), context); },
  };
}

test('loadCoverage popula zonas y tilda las especialidades guardadas', async () => {
  const { context, elements, specialtyCheckboxes, run } = buildContext(async () => ({
    ok: true,
    json: async () => ({ success: true, coverage: { zones: ['Nueva Córdoba', 'Cerro de las Rosas'], specialties: ['casa'], configured: true } }),
  }));
  run('static/js/profile.js');

  await context.loadCoverage();

  const html = elements['coverage-zones-list'].innerHTML;
  assert.ok(html.includes('Nueva Córdoba'));
  assert.ok(html.includes('Cerro de las Rosas'));

  const casa = specialtyCheckboxes.find(cb => cb.value === 'casa');
  const depto = specialtyCheckboxes.find(cb => cb.value === 'departamento');
  assert.equal(casa.checked, true);
  assert.equal(depto.checked, false);
});

test('addCoverageZone agrega una zona nueva y evita duplicados (case-insensitive)', () => {
  const { context, elements, run } = buildContext(async () => ({ ok: true, json: async () => ({ success: true }) }));
  run('static/js/profile.js');

  elements['coverage-zone-input'].value = 'Nueva Córdoba';
  context.addCoverageZone();
  elements['coverage-zone-input'].value = 'nueva córdoba';
  context.addCoverageZone();

  const html = elements['coverage-zones-list'].innerHTML;
  const occurrences = (html.match(/Nueva Córdoba/g) || []).length;
  assert.equal(occurrences, 1);
});

test('removeCoverageZone saca la zona correcta de la lista', () => {
  const { context, elements, run } = buildContext(async () => ({ ok: true, json: async () => ({ success: true }) }));
  run('static/js/profile.js');

  elements['coverage-zone-input'].value = 'Zona A';
  context.addCoverageZone();
  elements['coverage-zone-input'].value = 'Zona B';
  context.addCoverageZone();

  context.removeCoverageZone(0);

  const html = elements['coverage-zones-list'].innerHTML;
  assert.ok(!html.includes('Zona A'));
  assert.ok(html.includes('Zona B'));
});

test('saveCoverage envia las zonas actuales y las especialidades tildadas', async () => {
  let sentBody = null;
  const { context, elements, specialtyCheckboxes, run } = buildContext(async (url, opts) => {
    sentBody = JSON.parse(opts.body);
    return { ok: true, json: async () => ({ success: true, coverage: sentBody }) };
  });
  run('static/js/profile.js');

  elements['coverage-zone-input'].value = 'Nueva Córdoba';
  context.addCoverageZone();
  specialtyCheckboxes.find(cb => cb.value === 'terreno').checked = true;

  await context.saveCoverage();

  assert.deepEqual(sentBody, { zones: ['Nueva Córdoba'], specialties: ['terreno'] });
  assert.equal(elements['coverage-save-msg'].classList.contains('hidden'), false);
});

test('saveCoverage muestra el error del servidor si la validacion falla', async () => {
  const { context, elements, run } = buildContext(async () => ({
    ok: false,
    json: async () => ({ error: 'Demasiadas zonas o especialidades (máximo 20 cada una)' }),
  }));
  run('static/js/profile.js');

  await context.saveCoverage();

  assert.equal(elements['coverage-save-error'].textContent, 'Demasiadas zonas o especialidades (máximo 20 cada una)');
  assert.equal(elements['coverage-save-error'].classList.contains('hidden'), false);
});

test('el contador de zonas se actualiza al agregar y sacar', () => {
  const { context, elements, run } = buildContext(async () => ({ ok: true, json: async () => ({ success: true }) }));
  run('static/js/profile.js');

  assert.equal(elements['coverage-zones-count'].textContent, '0/20');

  elements['coverage-zone-input'].value = 'Zona A';
  context.addCoverageZone();
  assert.equal(elements['coverage-zones-count'].textContent, '1/20');

  context.removeCoverageZone(0);
  assert.equal(elements['coverage-zones-count'].textContent, '0/20');
});

test('al llegar a 20 zonas se deshabilita agregar y se avisa el limite', () => {
  const { context, elements, run } = buildContext(async () => ({ ok: true, json: async () => ({ success: true }) }));
  run('static/js/profile.js');

  for (let i = 0; i < 20; i++) {
    elements['coverage-zone-input'].value = 'Zona ' + i;
    context.addCoverageZone();
  }
  assert.equal(elements['coverage-zones-count'].textContent, '20/20');
  assert.equal(elements['coverage-zone-add-btn'].disabled, true);
  assert.equal(elements['coverage-zone-input'].disabled, true);

  // Intentar agregar una mas (ej. si quedo texto tipeado antes de que se
  // deshabilitara el input) no debe sumar una 21a zona, y avisa el limite.
  elements['coverage-zone-input'].disabled = false;
  elements['coverage-zone-input'].value = 'Zona de mas';
  context.addCoverageZone();
  assert.equal(elements['coverage-zones-count'].textContent, '20/20');
  assert.equal(elements['coverage-zone-error'].classList.contains('hidden'), false);
});

test('agregar una zona duplicada muestra un error inline en vez de fallar en silencio', () => {
  const { context, elements, run } = buildContext(async () => ({ ok: true, json: async () => ({ success: true }) }));
  run('static/js/profile.js');

  elements['coverage-zone-input'].value = 'Nueva Córdoba';
  context.addCoverageZone();
  elements['coverage-zone-input'].value = 'Nueva Córdoba';
  context.addCoverageZone();

  assert.equal(elements['coverage-zone-error'].classList.contains('hidden'), false);
  assert.equal(elements['coverage-zones-count'].textContent, '1/20');
});

test('loadCoverage muestra el aviso de fallback cuando configured es false', async () => {
  const { context, elements, run } = buildContext(async () => ({
    ok: true,
    json: async () => ({ success: true, coverage: { zones: ['Palermo'], specialties: [], configured: false } }),
  }));
  run('static/js/profile.js');

  await context.loadCoverage();
  assert.equal(elements['coverage-fallback-hint'].classList.contains('hidden'), false);
});

test('loadCoverage oculta el aviso de fallback cuando configured es true', async () => {
  const { context, elements, run } = buildContext(async () => ({
    ok: true,
    json: async () => ({ success: true, coverage: { zones: ['Palermo'], specialties: [], configured: true } }),
  }));
  run('static/js/profile.js');

  await context.loadCoverage();
  assert.equal(elements['coverage-fallback-hint'].classList.contains('hidden'), true);
});

test('saveCoverage deshabilita el boton y cambia el label mientras esta en curso', async () => {
  let resolveFetch;
  const pending = new Promise(resolve => { resolveFetch = resolve; });
  const { context, elements, run } = buildContext(() => pending);
  run('static/js/profile.js');

  const savePromise = context.saveCoverage();

  // En este punto el fetch todavia no resolvio -- el boton debe estar
  // deshabilitado y mostrando el estado de "guardando".
  assert.equal(elements['coverage-save-btn'].disabled, true);
  assert.equal(elements['coverage-save-btn-label'].textContent, 'profile.saving');

  resolveFetch({ ok: true, json: async () => ({ success: true }) });
  await savePromise;

  assert.equal(elements['coverage-save-btn'].disabled, false);
  assert.equal(elements['coverage-save-btn-label'].textContent, 'profile.coverage_save');
});

test('guardar con exito oculta el aviso de fallback', async () => {
  const { context, elements, run } = buildContext(async () => ({ ok: true, json: async () => ({ success: true }) }));
  run('static/js/profile.js');

  elements['coverage-fallback-hint'].classList.remove('hidden');
  await context.saveCoverage();

  assert.equal(elements['coverage-fallback-hint'].classList.contains('hidden'), true);
});

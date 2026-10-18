// Regresión: escapeHtml debe escapar comillas, no solo & < >.
// innerHTML sobre textContent escapa & < > pero NO comillas: sin el replace,
// un valor con " rompe atributos HTML entre comillas dobles (XSS por atributo).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function loadEscapeHtml() {
  const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'main.js'), 'utf8');
  const match = src.match(/function escapeHtml\(str\) \{[\s\S]*?\n\}/);
  assert.ok(match, 'escapeHtml no encontrada en static/js/main.js');

  // Document mínimo que emula el navegador: textContent -> innerHTML escapa & < >.
  const documentStub = {
    createElement() {
      let text = '';
      return {
        set textContent(v) { text = String(v); },
        get innerHTML() {
          return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        },
      };
    },
  };

  const ctx = { document: documentStub };
  vm.createContext(ctx);
  vm.runInContext(`${match[0]}\nthis.escapeHtml = escapeHtml;`, ctx);
  return ctx.escapeHtml;
}

test('escapeHtml escapa comillas dobles', () => {
  const out = loadEscapeHtml()('a"b');
  assert.strictEqual(out.includes('"'), false);
  assert.ok(out.includes('&quot;'));
});

test('escapeHtml escapa comillas simples', () => {
  const out = loadEscapeHtml()("a'b");
  assert.strictEqual(out.includes("'"), false);
  assert.ok(out.includes('&#39;'));
});

test('escapeHtml sigue escapando ampersands y etiquetas', () => {
  assert.strictEqual(loadEscapeHtml()('<b>&"'), '&lt;b&gt;&amp;&quot;');
});

test('escapeHtml convierte null y undefined en vacío', () => {
  const escapeHtml = loadEscapeHtml();
  assert.strictEqual(escapeHtml(null), '');
  assert.strictEqual(escapeHtml(undefined), '');
});

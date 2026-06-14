/**
 * AuthForm - Validación pre-envío para Login y Register
 *
 * Namespace global. Se attacha a un <form> y conecta:
 * - Validación on-blur y on-submit (configurable).
 * - Toggle ver/ocultar contraseña.
 * - Spinner + disable durante el envío.
 * - Para register: medidor de fuerza, reglas vivas, check async de username.
 *
 * Convención de marcado HTML:
 *  - Cada campo: <input data-auth-rules="..."> (JSON con reglas).
 *  - Contenedor de error: <div class="field-error" data-for="username" aria-live="polite"></div>.
 *  - Botón submit: <button type="submit" data-default-label="...">.
 *  - Toggle pass: <button data-toggle-pass="password" type="button">.
 *  - Spinner: <span data-spinner class="hidden">...</span> dentro del botón.
 *  - Medidor: <div data-strength-meter> con 4 niveles visuales.
 *  - Reglas: <li data-password-rule="length|letter|number|upper|symbol">.
 *
 * Mensajes en español rioplatense.
 */
(function () {
    'use strict';

    var CHECK_URL = '/api/auth/check-username';
    var USERNAME_DEBOUNCE_MS = 300;

    var escapeHtml = window.escapeHtml || function (str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };

    // -------------------------------------------------------------- helpers

    function $(sel, root) { return (root || document).querySelector(sel); }
    function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

    function debounce(fn, wait) {
        var t;
        return function () {
            var args = arguments, ctx = this;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(ctx, args); }, wait);
        };
    }

    function setAriaInvalid(input, invalid) {
        if (!input) return;
        if (invalid) {
            input.setAttribute('aria-invalid', 'true');
            input.classList.add('input-invalid');
            input.classList.remove('input-valid');
        } else {
            input.removeAttribute('aria-invalid');
            input.classList.remove('input-invalid');
            if (input.value) input.classList.add('input-valid');
        }
    }

    function showFieldError(input, message) {
        var name = input.name || input.getAttribute('data-name');
        var box = $('[data-for="' + name + '"].field-error');
        if (!box) return;
        if (message) {
            box.textContent = message;
            box.classList.add('field-error--visible');
            setAriaInvalid(input, true);
        } else {
            box.textContent = '';
            box.classList.remove('field-error--visible');
            setAriaInvalid(input, false);
        }
    }

    function clearAllErrors(form) {
        $$('.field-error', form).forEach(function (el) {
            el.textContent = '';
            el.classList.remove('field-error--visible');
        });
        $$('input, select, textarea', form).forEach(function (i) {
            i.classList.remove('input-invalid');
        });
    }

    // ----------------------------------------------------------- validators

    var validators = {
        required: function (val) {
            return (val || '').trim().length > 0;
        },
        usernameFormat: function (val) {
            return /^[a-zA-Z0-9_]{3,30}$/.test(val || '');
        },
        email: function (val) {
            return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val || '');
        },
        phone: function (val) {
            // Validación cliente alineada con utils.normalize_phone_to_e164 (server-side).
            // Server hace soft-migration con AR, así que también permitimos números
            // AR legacy (10-13 dígitos sin '+') que se asumirán como +54.
            var v = (val || '').trim();
            if (!v) return false;
            // Caso 1: internacional explícito (+código país)
            if (v.charAt(0) === '+') {
                // replace(/[^\d]/g,'') ya elimina el '+' (no es un dígito).
                var digits = v.replace(/[^\d]/g, '');
                if (digits.length < 8 || digits.length > 15) return false;
                return /^\+[\d\s\-\(\)]+$/.test(v);
            }
            // Caso 2: legacy AR (10-13 dígitos sin '+' — server-side intentará con AR)
            var digitsOnly = v.replace(/[^\d]/g, '');
            return digitsOnly.length >= 10 && digitsOnly.length <= 13;
        },
        minLength: function (val, n) {
            return (val || '').length >= (n || 0);
        },
        hasLetter: function (val) { return /[A-Za-z]/.test(val || ''); },
        hasNumber: function (val) { return /\d/.test(val || ''); },
        licenseFormat: function (val) {
            return /^[a-zA-Z0-9\-]{3,50}$/.test(val || '');
        }
    };

    // Devuelve { ok: bool, msg: string|null }
    function runFieldRules(input) {
        var rulesJson = input.getAttribute('data-auth-rules') || '{}';
        var rules;
        try { rules = JSON.parse(rulesJson); } catch (e) { rules = {}; }
        var val = input.value;

        // required
        if (rules.required && !validators.required(val)) {
            return { ok: false, msg: rules.messages && rules.messages.required || 'Este campo es obligatorio.' };
        }
        // si está vacío y no es required, pasa
        if (!rules.required && !validators.required(val)) {
            return { ok: true, msg: null };
        }
        if (rules.usernameFormat && !validators.usernameFormat(val)) {
            return { ok: false, msg: rules.messages && rules.messages.usernameFormat || '3-30 caracteres, solo letras, números y guión bajo.' };
        }
        if (rules.email && !validators.email(val)) {
            return { ok: false, msg: rules.messages && rules.messages.email || 'Email inválido.' };
        }
        if (rules.phone && !validators.phone(val)) {
            return { ok: false, msg: rules.messages && rules.messages.phone || 'Teléfono inválido. Usá formato internacional (+54 9 11 1234 5678).' };
        }
        if (rules.minLength && !validators.minLength(val, rules.minLength)) {
            return { ok: false, msg: (rules.messages && rules.messages.minLength || 'Mínimo {n} caracteres.').replace('{n}', rules.minLength) };
        }
        if (rules.hasLetter && !validators.hasLetter(val)) {
            return { ok: false, msg: rules.messages && rules.messages.hasLetter || 'Debe contener al menos una letra.' };
        }
        if (rules.hasNumber && !validators.hasNumber(val)) {
            return { ok: false, msg: rules.messages && rules.messages.hasNumber || 'Debe contener al menos un número.' };
        }
        if (rules.licenseFormat && !validators.licenseFormat(val)) {
            return { ok: false, msg: rules.messages && rules.messages.licenseFormat || '3-50 caracteres, solo letras, números y guiones.' };
        }
        return { ok: true, msg: null };
    }

    // -------------------------------------------------------- password meter

    // --------------------------------------------------------- phone preview

    /**
     * Normaliza un teléfono a E.164 (alineado con utils.normalize_phone_to_e164).
     * Sin librerías: heurística liviana que coincide con el server-side.
     *   - Si empieza con '+', toma los dígitos (sin contar el '+') y los antepone con '+'.
     *   - Si no, asume AR legacy y antepone +54.
     *   - Si no se puede normalizar, retorna null.
     */
    function normalizePhoneClient(val) {
        var v = (val || '').trim();
        if (!v) return null;
        if (v.charAt(0) === '+') {
            // replace(/[^\d]/g,'') ya elimina el '+' (no es un dígito).
            var digits = v.replace(/[^\d]/g, '');
            if (digits.length < 8 || digits.length > 15) return null;
            return '+' + digits;
        }
        var digitsOnly = v.replace(/[^\d]/g, '');
        if (digitsOnly.length < 10 || digitsOnly.length > 13) return null;
        // Asumimos AR legacy → +54 + últimos 10 dígitos
        return '+54' + digitsOnly.slice(-10);
    }

    function renderPhonePreview(form) {
        var input = $('input[name="phone"]', form);
        var preview = $('[data-phone-preview]', form);
        var status = $('[data-phone-status]', form);
        var statusIcon = status ? $('[data-phone-status-icon]', status) : null;
        if (!input || !preview) return;
        var raw = input.value;
        if (!raw.trim()) {
            preview.textContent = '';
            preview.classList.add('hidden');
            if (status) {
                status.classList.add('hidden');
                // Resetear el icono a estado neutral para evitar "fantasma"
                // si el status se re-mostrara antes de un nuevo render.
                if (statusIcon) {
                    statusIcon.setAttribute('data-lucide', 'circle');
                    statusIcon.className = 'w-5 h-5 text-midnight/30 dark:text-white/30';
                }
            }
            return;
        }
        var e164 = normalizePhoneClient(raw);
        if (e164) {
            preview.textContent = '✓ Se enviará como ' + e164;
            preview.className = 'phone-preview phone-preview--ok text-[10px] font-mono text-green-600 dark:text-green-400';
            preview.classList.remove('hidden');
            if (status && statusIcon) {
                statusIcon.setAttribute('data-lucide', 'check-circle-2');
                statusIcon.className = 'w-5 h-5 text-green-600 dark:text-green-400';
                status.classList.remove('hidden');
            }
        } else {
            preview.textContent = '';
            preview.classList.add('hidden');
            if (status) {
                status.classList.add('hidden');
                if (statusIcon) {
                    statusIcon.setAttribute('data-lucide', 'circle');
                    statusIcon.className = 'w-5 h-5 text-midnight/30 dark:text-white/30';
                }
            }
        }
        if (window.lucide) lucide.createIcons();
    }

    function bindPhoneExampleButtons(form) {
        $$('[data-phone-example]', form).forEach(function (btn) {
            btn.addEventListener('click', function () {
                var input = $('input[name="phone"]', form);
                if (!input) return;
                input.value = btn.getAttribute('data-phone-example') || '';
                input.focus();
                renderPhonePreview(form);
                // Disparar blur para que aparezca el field-error si corresponde
                input.dispatchEvent(new Event('blur'));
            });
        });
    }

    function passwordStrength(val) {
        var v = val || '';
        var score = 0;
        if (v.length >= 6) score++;
        if (v.length >= 8) score++;
        if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
        if (/\d/.test(v) && /[^\w\s]/.test(v)) score++;
        // Cap a 4
        if (score > 4) score = 4;
        var labels = ['vacía', 'débil', 'aceptable', 'buena', 'fuerte'];
        return { score: score, label: labels[score] };
    }

    function renderPasswordStrength(form) {
        var passInput = $('input[name="password"][data-strength]', form);
        var meter = $('[data-strength-meter]', form);
        if (!passInput || !meter) return;
        var bar = $('[data-strength-bar]', meter);
        var label = $('[data-strength-label]', meter);
        var s = passwordStrength(passInput.value);
        if (bar) {
            bar.className = 'password-strength__bar password-strength__bar--score-' + s.score;
        }
        if (label) {
            label.textContent = s.label;
            label.className = 'password-strength__label password-strength__label--score-' + s.score;
        }
        meter.classList.toggle('password-strength--active', passInput.value.length > 0);

        // Reglas vivas
        $$('[data-password-rule]', form).forEach(function (li) {
            var rule = li.getAttribute('data-password-rule');
            var passed = false;
            if (rule === 'length') passed = (passInput.value.length >= 6);
            if (rule === 'letter') passed = /[A-Za-z]/.test(passInput.value);
            if (rule === 'number') passed = /\d/.test(passInput.value);
            if (rule === 'upper') passed = /[A-Z]/.test(passInput.value);
            if (rule === 'symbol') passed = /[^\w\s]/.test(passInput.value);
            li.classList.toggle('password-rule--ok', passed);
            var icon = $('i[data-rule-icon]', li);
            if (icon) {
                icon.setAttribute('data-lucide', passed ? 'check' : 'circle');
            }
        });
        if (window.lucide) lucide.createIcons();
    }

    // -------------------------------------------------------- username async

    var usernameCache = {};

    function checkUsernameAvailable(value, cb) {
        if (!validators.usernameFormat(value)) {
            cb({ available: null, reason: 'invalid' });
            return;
        }
        if (usernameCache[value] !== undefined) {
            cb(usernameCache[value]);
            return;
        }
        fetch(CHECK_URL + '?q=' + encodeURIComponent(value), {
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
        })
            .then(function (r) {
                if (r.status === 429) throw new Error('rate_limited');
                if (!r.ok) throw new Error('http_' + r.status);
                return r.json();
            })
            .then(function (data) {
                usernameCache[value] = data;
                cb(data);
            })
            .catch(function () {
                cb({ available: null, reason: 'error' });
            });
    }

    function renderUsernameHint(input, data) {
        var hint = $('[data-username-hint]', input.closest('div') || document);
        if (!hint) {
            var parent = input.closest('.field') || input.parentElement;
            hint = parent ? $('[data-username-hint]', parent) : null;
        }
        if (!hint) return;
        if (data.reason === 'invalid') {
            hint.textContent = '3-30 caracteres, letras, números y guión bajo.';
            hint.className = 'username-hint';
        } else if (data.reason === 'taken') {
            hint.textContent = '✗ Ese usuario ya está en uso';
            hint.className = 'username-hint username-hint--taken';
        } else if (data.reason === 'ok') {
            hint.textContent = '✓ Disponible';
            hint.className = 'username-hint username-hint--ok';
        } else {
            hint.textContent = '';
            hint.className = 'username-hint';
        }
    }

    // ---------------------------------------------------------- toggle pass

    function bindPasswordToggle(form) {
        $$('[data-toggle-pass]', form).forEach(function (btn) {
            btn.addEventListener('click', function () {
                var name = btn.getAttribute('data-toggle-pass');
                var input = $('input[name="' + name + '"]', form);
                var icon = $('i[data-pass-icon]', btn);
                if (!input) return;
                if (input.type === 'password') {
                    input.type = 'text';
                    if (icon) icon.setAttribute('data-lucide', 'eye-off');
                    btn.setAttribute('aria-label', 'Ocultar contraseña');
                } else {
                    input.type = 'password';
                    if (icon) icon.setAttribute('data-lucide', 'eye');
                    btn.setAttribute('aria-label', 'Mostrar contraseña');
                }
                if (window.lucide) lucide.createIcons();
            });
        });
    }

    // -------------------------------------------------------------- submit

    function showFormBanner(form, message, type) {
        var banner = $('[data-form-banner]', form);
        if (!banner) {
            banner = document.createElement('div');
            banner.setAttribute('data-form-banner', '');
            banner.setAttribute('role', 'alert');
            banner.setAttribute('aria-live', 'assertive');
            banner.className = 'form-banner form-banner--' + (type || 'error');
            form.insertBefore(banner, form.firstChild);
        } else {
            banner.className = 'form-banner form-banner--' + (type || 'error');
        }
        banner.textContent = message;
    }

    function startSubmitting(form) {
        var btn = $('button[type="submit"]', form);
        if (!btn) return;
        btn.disabled = true;
        btn.classList.add('is-submitting');
        var label = $('[data-label]', btn);
        var spinner = $('[data-spinner]', btn);
        if (label) label.classList.add('hidden');
        if (spinner) spinner.classList.remove('hidden');
    }

    function validateForm(form, options) {
        clearAllErrors(form);
        options = options || {};
        var inputs = $$('input[data-auth-rules], select[data-auth-rules], textarea[data-auth-rules]', form);
        var firstInvalid = null;
        var ok = true;
        inputs.forEach(function (input) {
            // Saltar campos condicionalmente ocultos (ej. license si role=client)
            if (input.closest('[hidden],[style*="display: none"],[style*="display:none"]')) return;
            var r = runFieldRules(input);
            if (!r.ok) {
                showFieldError(input, r.msg);
                if (!firstInvalid) firstInvalid = input;
                ok = false;
            }
        });
        // Check async username: SOLO en register. En login, el usuario conoce su
        // username y el check devolvería 'taken' bloqueando el submit. Bug histórico
        // (2024-Q2) donde admin no podía loguearse.
        var usernameInput = $('input[name="username"]', form);
        var usernamePromise = Promise.resolve(true);
        if (options.mode === 'register' && usernameInput && validators.usernameFormat(usernameInput.value)) {
            usernamePromise = new Promise(function (resolve) {
                checkUsernameAvailable(usernameInput.value, function (data) {
                    if (data.available === false && data.reason === 'taken') {
                        showFieldError(usernameInput, 'Ese nombre de usuario ya está en uso.');
                        resolve(false);
                    } else {
                        resolve(true);
                    }
                });
            });
        }
        return usernamePromise.then(function (uOk) {
            if (!ok || !uOk) {
                if (firstInvalid) firstInvalid.focus();
                showFormBanner(form, 'Revisá los campos marcados antes de continuar.', 'error');
                return false;
            }
            return true;
        });
    }

    // ----------------------------------------------------------- role gate

    function bindRoleLicenseGate(form) {
        var roleSelect = $('select[name="role"]', form);
        var licenseContainer = $('[data-license-container]', form);
        if (!roleSelect || !licenseContainer) return;
        function sync() {
            var isPro = roleSelect.value === 'professional';
            licenseContainer.classList.toggle('hidden', !isPro);
            var licInput = $('input[name="license"]', licenseContainer);
            if (licInput) {
                if (isPro) {
                    licInput.setAttribute('data-auth-rules', JSON.stringify({
                        required: true,
                        licenseFormat: true,
                        messages: {
                            required: 'La matrícula es obligatoria para profesionales.',
                            licenseFormat: '3-50 caracteres, solo letras, números y guiones.'
                        }
                    }));
                } else {
                    licInput.removeAttribute('data-auth-rules');
                    showFieldError(licInput, null);
                }
            }
        }
        roleSelect.addEventListener('change', sync);
        sync();
    }

    // --------------------------------------------------------- public API

    function attach(form, options) {
        if (!form) return;
        options = options || {};
        // Solo register hace check async de disponibilidad de username.
        // En login, el usuario conoce su username y el check es contraproducente.
        var isRegister = options.mode === 'register';

        // Para cada input con data-auth-rules, conectar blur
        $$('input[data-auth-rules], select[data-auth-rules], textarea[data-auth-rules]', form).forEach(function (input) {
            input.addEventListener('blur', function () {
                // No validar teléfono en blur si tiene menos de 8 dígitos
                // (el usuario puede estar escribiendo todavía)
                if (input.name === 'phone') {
                    var digits = (input.value || '').replace(/[^\d]/g, '');
                    if (digits.length < 8) return;
                }
                var r = runFieldRules(input);
                showFieldError(input, r.ok ? null : r.msg);
            });
            // Si es username y está en register, disparar fetch con debounce
            if (isRegister && input.name === 'username' && input.getAttribute('data-async-check') !== 'false') {
                var debouncedCheck = debounce(function () {
                    if (!validators.usernameFormat(input.value)) {
                        renderUsernameHint(input, { reason: 'invalid' });
                        return;
                    }
                    checkUsernameAvailable(input.value, function (data) {
                        renderUsernameHint(input, data);
                    });
                }, USERNAME_DEBOUNCE_MS);
                input.addEventListener('input', debouncedCheck);
            }
            // Si es phone, actualizar preview en vivo
            if (input.name === 'phone') {
                input.addEventListener('input', function () { renderPhonePreview(form); });
            }
            // Si tiene data-strength, actualizar medidor
            if (input.getAttribute('data-strength') === 'true') {
                input.addEventListener('input', function () { renderPasswordStrength(form); });
            }
        });

        // Toggle pass
        bindPasswordToggle(form);

        // Role gate
        bindRoleLicenseGate(form);

        // Phone example buttons + preview inicial
        bindPhoneExampleButtons(form);
        renderPhonePreview(form);

        // Submit
        form.addEventListener('submit', function (ev) {
            ev.preventDefault();
            validateForm(form, options).then(function (valid) {
                if (!valid) return;
                startSubmitting(form);
                // Submit nativo
                form.submit();
            });
        });
    }

    // Expose for tests
    window.AuthForm = {
        attach: attach,
        validators: validators,
        passwordStrength: passwordStrength,
        runFieldRules: runFieldRules,
        checkUsernameAvailable: checkUsernameAvailable,
        validateForm: validateForm
    };

    // Auto-attach si encuentra form con data-auth-form
    document.addEventListener('DOMContentLoaded', function () {
        $$('form[data-auth-form]').forEach(function (form) {
            var mode = form.getAttribute('data-auth-form');
            attach(form, { mode: mode });
        });
        // Refrescar íconos después de pintar medidor inicial
        if (window.lucide) lucide.createIcons();
    });
})();

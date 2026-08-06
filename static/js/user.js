// ================================================================
// TIPO DE PROPIEDAD: toggle dinámico desde form_options
// ================================================================
function setPropertyType(type) {
    document.getElementById('property-type-input').value = type;

    // Actualizar estilos de todos los botones
    document.querySelectorAll('#property-type-buttons .prop-type-btn').forEach(btn => {
        const isSelected = btn.dataset.value === type;
        btn.className = 'prop-type-btn flex-1 min-w-[120px] py-3 px-4 rounded border-2 font-semibold transition-all '
            + (isSelected ? 'border-gold bg-gold/10 text-midnight'
                         : 'border-midnight/20 bg-white text-midnight hover:border-gold');
    });

    // Mapeo de valores de form_options a IDs de paneles
    const panelMap = {
        'departamento': 'department-details',
        'casa': 'house-details',
        'duplex': 'duplex-details',
        'penthouse': 'penthouse-details',
        'local_comercial': 'local-details'
    };
    const activePanel = panelMap[type] || '';

    // Mostrar/ocultar paneles de detalles
    ['department-details', 'house-details', 'duplex-details', 'penthouse-details', 'local-details'].forEach(p => {
        const panel = document.getElementById(p);
        if (panel) panel.classList.toggle('hidden', p !== activePanel);
    });

    // Coherencia: "Remodelación Integral" solo aplica a Casa; "Construir desde Cero" solo a Casa
    const opSelect = document.getElementById('operation-select');
    const isCasa = type === 'casa';

    if (isCasa) {
        if (!opSelect.querySelector('option[value="Construir desde Cero"]')) {
            const newOpt = new Option('Construir desde Cero', 'Construir desde Cero');
            opSelect.add(newOpt);
        }
    } else {
        const opt = [...opSelect.options].find(o => o.value === 'Construir desde Cero');
        if (opt) {
            if (opSelect.value === 'Construir desde Cero') opSelect.value = '';
            opt.remove();
        }
    }

    // Piscina Infinity: solo visible para Casa y cuando Piscina está checkeada
    const infinityPoolLabel = document.getElementById('infinity-pool-label');
    const infinityPoolCheckbox = document.getElementById('infinity-pool-checkbox');
    const poolCheckbox = document.getElementById('pool-checkbox');
    if (infinityPoolLabel && infinityPoolCheckbox) {
        if (isCasa && poolCheckbox && poolCheckbox.checked) {
            infinityPoolLabel.classList.remove('hidden', 'opacity-50', 'cursor-not-allowed');
            infinityPoolCheckbox.disabled = false;
        } else {
            infinityPoolLabel.classList.add('hidden', 'opacity-50', 'cursor-not-allowed');
            infinityPoolCheckbox.disabled = true;
            infinityPoolCheckbox.checked = false;
        }
    }
}

// ================================================================
// BARRIO PRIVADO: subpanel dentro de Casa
// ================================================================
function toggleGatedCommunity(checked) {
    document.getElementById('gated-community-details').classList.toggle('hidden', !checked);
}

// ================================================================
// CHIPS: selector de valor único con estado visual activo
// ================================================================
const CHIP_GROUPS = {
    parking:     { hidden: 'parking-input',     cls: 'parking-chip' },
    orientation: { hidden: 'orientation-input', cls: 'orientation-chip' },
    condition:   { hidden: 'condition-input',   cls: 'condition-chip' },
    age:         { hidden: 'age-input',         cls: 'age-chip' },
};

const CHIP_BASE = {
    parking:     'parking-chip px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    orientation: 'orientation-chip px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    condition:   'condition-chip w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    age:         'age-chip w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
};

function selectChip(group, value) {
    const g = CHIP_GROUPS[group];
    if (!g) return;
    document.getElementById(g.hidden).value = value;
    document.querySelectorAll('.' + g.cls).forEach(btn => {
        const active = btn.dataset.value === value;
        btn.className = CHIP_BASE[group] + ' '
            + (active
                ? 'border-midnight bg-midnight text-white'
                : 'border-midnight/20 text-midnight hover:border-gold');
    });

    // Coherencia Condition → Age
    if (group === 'condition') syncAgeToCondition(value);
}

// ================================================================
// COHERENCIA: Estado de Propiedad ↔ Antigüedad
// ================================================================
function syncAgeToCondition(condition) {
    const ageSection = document.getElementById('age-section');
    const ageChips   = document.querySelectorAll('.age-chip');

    if (condition === 'A estrenar') {
        // Auto-seleccionar "Hasta 5 años" y bloquear el resto
        selectChip('age', 'Hasta 5 años');
        ageChips.forEach(btn => {
            const isForced = btn.dataset.value === 'Hasta 5 años';
            btn.disabled = !isForced;
            btn.style.opacity = isForced ? '1' : '0.35';
            btn.style.cursor  = isForced ? 'default' : 'not-allowed';
        });
        if (ageSection) ageSection.classList.remove('hidden');

    } else if (condition === 'En construcción') {
        // Sin antigüedad aplicable → ocultar la sección
        selectChip('age', '');
        if (ageSection) ageSection.classList.add('hidden');

    } else if (condition === 'A reciclar') {
        // Sugerir "Más de 30 años" pero sin bloquear
        if (ageSection) ageSection.classList.remove('hidden');
        ageChips.forEach(btn => { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
        selectChip('age', 'Más de 30 años');

    } else {
        // Sin preferencia / Usado → todo desbloqueado
        if (ageSection) ageSection.classList.remove('hidden');
        ageChips.forEach(btn => { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
    }
}

// ================================================================
// STEPPERS: botones +/− para inputs numéricos
// ================================================================
function stepNum(fieldName, delta) {
    const inputMap = {
        ambientes: 'ambientes-input',
        bedrooms:  'bedrooms-input',
        bathrooms: 'bathrooms-input',
    };
    const el  = document.getElementById(inputMap[fieldName]);
    if (!el) return;
    const min  = parseInt(el.min) || 0;
    const max  = parseInt(el.max) || 99;
    const cur  = parseInt(el.value) || 0;
    const next = cur + delta;
    el.value   = next < min ? '' : Math.min(max, next);
}

// ================================================================
// INIT
// ================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Renderizar botones de tipo de propiedad dinámicamente
    foRenderPropertyTypeButtons('property-type-buttons', function(value) {
        setPropertyType(value);
    });

    // Inicializar en modo Departamento por defecto
    setPropertyType('departamento');

    // Toggle Piscina Infinity cuando cambia el checkbox de Piscina
    const poolCheckbox = document.getElementById('pool-checkbox');
    if (poolCheckbox) {
        poolCheckbox.addEventListener('change', function() {
            const infinityPoolLabel = document.getElementById('infinity-pool-label');
            const infinityPoolCheckbox = document.getElementById('infinity-pool-checkbox');
            if (infinityPoolLabel && infinityPoolCheckbox) {
                if (this.checked) {
                    infinityPoolLabel.classList.remove('hidden', 'opacity-50', 'cursor-not-allowed');
                    infinityPoolCheckbox.disabled = false;
                } else {
                    infinityPoolLabel.classList.add('hidden', 'opacity-50', 'cursor-not-allowed');
                    infinityPoolCheckbox.disabled = true;
                    infinityPoolCheckbox.checked = false;
                }
            }
        });
    }

    if (window.lucide) lucide.createIcons();
});

// ================================================================
// GUARDAR TELÉFONO EN PERFIL
// ================================================================
async function savePhoneToProfile() {
    const phoneInput = document.getElementById('phone-input');
    const countrySelect = document.getElementById('country-code-select');
    const errorMsg   = document.getElementById('phone-error-msg');
    const saveBtn    = document.getElementById('save-phone-btn');
    const phone      = phoneInput.value.trim();
    const countryCode = countrySelect.value;

    errorMsg.classList.add('hidden');

    if (!phone) {
        errorMsg.textContent = t('phone.enter_number_first');
        errorMsg.classList.remove('hidden');
        return;
    }

    let digits = phone.replace(/\D/g, '');
    const codeDigits = countryCode.replace('+', '');
    if (digits.startsWith(codeDigits) && digits.length > codeDigits.length) {
        digits = digits.substring(codeDigits.length);
    }
    const fullPhone = formatPhoneWithCountry(digits, countryCode);
    const national = fullPhone.replace(new RegExp('^\\' + countryCode + '\\s*'), '').replace(/\D/g, '');

    if (typeof PhoneSuggest !== 'undefined' && !PhoneSuggest.isPlausible(countryCode, national)) {
        onUserPhoneInput();
        errorMsg.textContent = t('phone.incomplete_autocomplete');
        errorMsg.classList.remove('hidden');
        return;
    }

    const originalContent = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> ' + t('action.saving');
    saveBtn.disabled  = true;
    if (window.lucide) lucide.createIcons();

    try {
        const res  = await fetch('/api/user/update-phone', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ phone: fullPhone })
        });
        const data = await res.json();

        if (res.ok) {
            saveBtn.innerHTML = '<i data-lucide="check" class="w-3 h-3"></i> ' + t('action.saved');
            saveBtn.classList.add('text-emerald-600');
            if (window.lucide) lucide.createIcons();
            if (typeof showToast === 'function') showToast(t('phone.saved_to_profile'));
            setTimeout(() => {
                saveBtn.innerHTML = originalContent;
                saveBtn.classList.remove('text-emerald-600');
                saveBtn.disabled  = false;
                if (window.lucide) lucide.createIcons();
            }, 3000);
        } else {
            errorMsg.textContent = data.error || t('error.phone_save');
            errorMsg.classList.remove('hidden');
            saveBtn.innerHTML = originalContent;
            saveBtn.disabled  = false;
            if (window.lucide) lucide.createIcons();
        }
    } catch (err) {
        errorMsg.textContent = t('error.connection_retry');
        errorMsg.classList.remove('hidden');
        saveBtn.innerHTML = originalContent;
        saveBtn.disabled  = false;
        if (window.lucide) lucide.createIcons();
    }
}

// ================================================================
// Selector de código de país
// ================================================================
function formatPhoneWithCountry(phone, countryCode) {
    const digits = phone.replace(/\D/g, '');
    const codeDigits = countryCode.replace('+', '');
    let national = digits;
    if (national.startsWith(codeDigits) && national.length > codeDigits.length) {
        national = national.substring(codeDigits.length);
    }
    if (typeof PhoneSuggest !== 'undefined') {
        return PhoneSuggest.formatNational(countryCode, national);
    }
    return (countryCode + ' ' + national.replace(/(\d{2,4})/g, '$1 ').trim()).trim();
}

function updateCountryCode() {
    const countryCode = document.getElementById('country-code-select').value;
    const provinceSelect = document.getElementById('phone-province');
    const phoneInput = document.getElementById('phone-input');

    if (typeof PhoneSuggest !== 'undefined') {
        PhoneSuggest.populateAreaSelect(provinceSelect, countryCode);
    }
    let totalOpts = 0;
    if (provinceSelect) {
        for (let i = 0; i < provinceSelect.options.length; i++) {
            if (provinceSelect.options[i].value !== 'other') totalOpts++;
        }
    }
    if (typeof showProvinceSearchToggle === 'function') {
        showProvinceSearchToggle(totalOpts > 20);
    }

    const currentPhone = phoneInput.value.trim();
    if (currentPhone) {
        const fullPhone = formatPhoneWithCountry(currentPhone, countryCode);
        phoneInput.value = fullPhone.replace(countryCode + ' ', '');
    }
    onUserPhoneInput();
}

function applyPhoneProvincePrefix() {
    const phoneInput = document.getElementById('phone-input');
    const provinceSelect = document.getElementById('phone-province');
    const prefix = provinceSelect.value;
    if (!prefix) return;
    let body = phoneInput.value.trim().replace(/\D/g, '');
    if (body.startsWith('54') && body.length > 9) body = body.substring(2);
    if (body.startsWith('0')) body = body.substring(1);
    const countryCode = document.getElementById('country-code-select').value;
    let mobile = '';
    if (countryCode === '+54') {
        if (body.startsWith('15')) body = body.substring(2);
        else if (body.startsWith('9')) body = body.substring(1);
        mobile = '9 ';
    }
    if (body.startsWith(prefix)) body = body.substring(prefix.length);
    else if (body.startsWith('0' + prefix)) body = body.substring(prefix.length + 1);
    phoneInput.value = mobile + prefix + ' ' + body.replace(/(\d{4})/g, '$1 ').trim();
    onUserPhoneInput();
}

let _lastUserPhoneSuggestion = '';

function onUserPhoneInput() {
    const phoneInput = document.getElementById('phone-input');
    const countrySelect = document.getElementById('country-code-select');
    const suggestionEl = document.getElementById('user-phone-suggestion');
    const previewEl = document.getElementById('user-correction-preview');
    _lastUserPhoneSuggestion = '';
    if (suggestionEl) suggestionEl.classList.add('hidden');
    if (previewEl) previewEl.classList.add('hidden');
    if (!phoneInput || !countrySelect || typeof PhoneSuggest === 'undefined') return;

    const raw = phoneInput.value.trim();
    if (!raw) return;
    const digits = raw.replace(/\D/g, '');
    const cc = countrySelect.value;
    const codeDigits = cc.replace('+', '');
    const national = (digits.startsWith(codeDigits) && digits.length > codeDigits.length)
        ? digits.substring(codeDigits.length) : digits;
    if (!national) return;

    const suggestion = PhoneSuggest.suggestNationalNumber(cc, national);
    if (!suggestion) return;
    const sugNational = suggestion.replace(/^(\+\d+)\s*/, '').replace(/\D/g, '');
    if (sugNational === national) return;
    _lastUserPhoneSuggestion = suggestion;
    if (suggestionEl) suggestionEl.classList.remove('hidden');
}

function showUserPhoneCorrection() {
    if (!_lastUserPhoneSuggestion) return;
    const input = document.getElementById('phone-input');
    const cc = document.getElementById('country-code-select').value;
    const fromEl = document.getElementById('user-correction-from');
    const toEl = document.getElementById('user-correction-to');
    const previewEl = document.getElementById('user-correction-preview');
    if (fromEl) fromEl.textContent = cc + ' ' + input.value.trim();
    if (toEl) toEl.textContent = _lastUserPhoneSuggestion;
    if (previewEl) previewEl.classList.remove('hidden');
}

function applyUserPhoneCorrection() {
    if (!_lastUserPhoneSuggestion) return;
    const input = document.getElementById('phone-input');
    const cc = document.getElementById('country-code-select').value;
    if (input) input.value = _lastUserPhoneSuggestion.replace(cc + ' ', '');
    _lastUserPhoneSuggestion = '';
    const suggestionEl = document.getElementById('user-phone-suggestion');
    const previewEl = document.getElementById('user-correction-preview');
    if (suggestionEl) suggestionEl.classList.add('hidden');
    if (previewEl) previewEl.classList.add('hidden');
}

function dismissUserPhoneCorrection() {
    _lastUserPhoneSuggestion = '';
    const suggestionEl = document.getElementById('user-phone-suggestion');
    const previewEl = document.getElementById('user-correction-preview');
    if (suggestionEl) suggestionEl.classList.add('hidden');
    if (previewEl) previewEl.classList.add('hidden');
}

// Inicializar selector de provincia según teléfono existente
(function() {
    var phoneInput = document.getElementById('phone-input');
    var countrySelect = document.getElementById('country-code-select');
    var provinceSelect = document.getElementById('phone-province');
    if (!phoneInput || !countrySelect || !provinceSelect) return;

    var currentPhone = phoneInput.value.trim();
    if (currentPhone) {
        var match = currentPhone.match(/^(\+\d+)/);
        if (match) {
            var code = match[1];
            var options = countrySelect.querySelectorAll('option');
            for (var i = 0; i < options.length; i++) {
                if (options[i].value === code) { options[i].selected = true; break; }
            }
            var digits = currentPhone.replace(/\D/g, '');
            var codeDigits = code.replace('+', '');
            var withoutCode = digits.substring(codeDigits.length);
            if (typeof PhoneSuggest !== 'undefined') {
                PhoneSuggest.populateAreaSelect(provinceSelect, code);
                var info = PhoneSuggest.getRegionInfo(code, withoutCode);
                if (info) {
                    for (var j = 0; j < provinceSelect.options.length; j++) {
                        if (provinceSelect.options[j].value === info.code) {
                            provinceSelect.options[j].selected = true;
                            break;
                        }
                    }
                }
                phoneInput.value = PhoneSuggest.formatNational(code, withoutCode).replace(code + ' ', '');
            } else {
                phoneInput.value = withoutCode;
            }
        }
    }
    var totalOpts = 0;
    for (var i = 0; i < provinceSelect.options.length; i++) {
        if (provinceSelect.options[i].value !== 'other') totalOpts++;
    }
    if (typeof showProvinceSearchToggle === 'function') {
        showProvinceSearchToggle(totalOpts > 20);
    }
})();

// (submit handler lives in main.js:DOMContentLoaded -> initUserForm)

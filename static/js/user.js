// ================================================================
// TIPO DE PROPIEDAD: toggle entre Departamento, Casa, Dúplex, Penthouse, Local
// ================================================================
function setPropertyType(type) {
    document.getElementById('property-type-input').value = type;

    const propertyTypes = ['department', 'house', 'duplex', 'penthouse', 'local'];
    const selectedTypes = {
        'departamento': 'department',
        'casa': 'house',
        'duplex': 'duplex',
        'penthouse': 'penthouse',
        'local_comercial': 'local'
    };
    const currentType = selectedTypes[type] || 'department';

    // Actualizar estilos de todos los botones
    propertyTypes.forEach(pt => {
        const btn = document.getElementById('btn-' + pt);
        if (btn) {
            const isSelected = pt === currentType;
            btn.className = 'flex-1 min-w-[120px] py-3 px-4 rounded border-2 font-semibold transition-all '
                + (isSelected ? 'border-midnight bg-midnight text-white'
                             : 'border-midnight/20 bg-white text-midnight hover:border-gold');
        }
    });

    // Mostrar/ocultar paneles de detalles
    const panels = ['department-details', 'house-details', 'duplex-details', 'penthouse-details', 'local-details'];
    panels.forEach(p => {
        const panel = document.getElementById(p);
        if (panel) {
            const expectedType = p.replace('-details', '');
            panel.classList.toggle('hidden', expectedType !== currentType);
        }
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
    const min  = parseInt(el.min) ?? 0;
    const max  = parseInt(el.max) || 99;
    const cur  = parseInt(el.value) || 0;
    const next = cur + delta;
    el.value   = next < min ? '' : Math.min(max, next);
}

// ================================================================
// INIT
// ================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar en modo Departamento por defecto
    setPropertyType('departamento');

    // Wiring botones de tipo de propiedad
    document.getElementById('btn-department').addEventListener('click', () => setPropertyType('departamento'));
    document.getElementById('btn-house').addEventListener('click',      () => setPropertyType('casa'));
    document.getElementById('btn-duplex').addEventListener('click',     () => setPropertyType('duplex'));
    document.getElementById('btn-penthouse').addEventListener('click',  () => setPropertyType('penthouse'));
    document.getElementById('btn-local').addEventListener('click',      () => setPropertyType('local_comercial'));

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
        errorMsg.textContent = 'Ingresá un número antes de guardar.';
        errorMsg.classList.remove('hidden');
        return;
    }

    const fullPhone = formatPhoneWithCountry(phone, countryCode);

    const originalContent = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> Guardando...';
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
            saveBtn.innerHTML = '<i data-lucide="check" class="w-3 h-3"></i> Guardado';
            saveBtn.classList.add('text-emerald-600');
            if (window.lucide) lucide.createIcons();
            if (typeof showToast === 'function') showToast('Teléfono guardado en tu perfil.');
            setTimeout(() => {
                saveBtn.innerHTML = originalContent;
                saveBtn.classList.remove('text-emerald-600');
                saveBtn.disabled  = false;
                if (window.lucide) lucide.createIcons();
            }, 3000);
        } else {
            errorMsg.textContent = data.error || 'Error al guardar el teléfono.';
            errorMsg.classList.remove('hidden');
            saveBtn.innerHTML = originalContent;
            saveBtn.disabled  = false;
            if (window.lucide) lucide.createIcons();
        }
    } catch (err) {
        errorMsg.textContent = 'Error de conexión. Intentá de nuevo.';
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
    const countryCodeDigits = countryCode.replace('+', '');

    let formatted = countryCode + ' ';
    const codeLen = countryCodeDigits.length;

    if (countryCode === '+54' && digits.length >= 2) {
        const mobilePrefix = digits.substring(0, 1);
        const areaCode = digits.substring(1, codeLen + 1);
        const rest = digits.substring(codeLen + 1);

        if (mobilePrefix === '9' || mobilePrefix === '15') {
            formatted += mobilePrefix + ' ' + (areaCode ? areaCode + ' ' : '') + rest.replace(/(\d{4})/g, '$1 ').trim();
        } else {
            formatted += (areaCode ? areaCode + ' ' : '') + rest.replace(/(\d{4})/g, '$1 ').trim();
        }
    } else if (countryCode === '+1' && digits.length >= 10) {
        formatted = countryCode + ' (' + digits.substring(0, 3) + ') ' + digits.substring(3, 6) + '-' + digits.substring(6);
    } else if (countryCode === '+34' && digits.length >= 9) {
        formatted += digits.substring(0, 2) + ' ' + digits.substring(2, 5) + ' ' + digits.substring(5, 7) + ' ' + digits.substring(7);
    } else if (digits.length > codeLen) {
        formatted += digits.substring(codeLen).replace(/(\d{2,4})/g, '$1 ').trim();
    } else {
        formatted += digits;
    }

    return formatted.trim();
}

function updateCountryCode() {
    const countryCode = document.getElementById('country-code-select').value;
    const provinceSelect = document.getElementById('phone-province');
    const phoneInput = document.getElementById('phone-input');

    if (countryCode === '+54') {
        provinceSelect.classList.remove('hidden');
    } else {
        provinceSelect.classList.add('hidden');
    }

    const currentPhone = phoneInput.value.trim();
    if (currentPhone) {
        const fullPhone = formatPhoneWithCountry(currentPhone, countryCode);
    }
}

function applyPhoneProvincePrefix() {
    const phoneInput = document.getElementById('phone-input');
    const provinceSelect = document.getElementById('phone-province');
    const prefix = provinceSelect.value;
    const raw = phoneInput.value.trim().replace(/\D/g, '');
    const prefixes = ['11','221','223','341','351','261','264','266','280','291','299','379','381','383','387','388','358','342','343','345','362','364','370','375','376','377','378','385'];
    const hasPrefix = prefixes.some(p => raw.startsWith(p));
    if (!hasPrefix && raw.length > 0) {
        phoneInput.value = prefix + ' ' + raw;
    } else if (raw.length > 0) {
        var cleaned = raw;
        for (var i = 0; i < prefixes.length; i++) {
            if (cleaned.startsWith(prefixes[i])) { cleaned = cleaned.substring(prefixes[i].length).replace(/^\s+/, ''); break; }
        }
        phoneInput.value = prefix + ' ' + cleaned;
    }
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
            if (code === '+54' && provinceSelect) {
                provinceSelect.classList.remove('hidden');
                var provincePrefix = '';
                for (var i = 0; i < provinceSelect.options.length; i++) {
                    if (withoutCode.startsWith(provinceSelect.options[i].value)) {
                        provinceSelect.options[i].selected = true;
                        provincePrefix = provinceSelect.options[i].value;
                        break;
                    }
                }
                phoneInput.value = provincePrefix ? withoutCode.substring(provincePrefix.length) : withoutCode;
            } else {
                phoneInput.value = withoutCode;
            }
        }
    } else if (countrySelect.value === '+54') {
        provinceSelect.classList.remove('hidden');
    }
})();

// Antes de enviar el formulario, combinar código de país + prefijo de provincia + teléfono
document.getElementById('userForm').addEventListener('submit', function(e) {
    const phoneInput = document.getElementById('phone-input');
    const countrySelect = document.getElementById('country-code-select');
    const provinceSelect = document.getElementById('phone-province');
    const phone = phoneInput ? phoneInput.value.trim() : '';
    const countryCode = countrySelect ? countrySelect.value : '+54';

    if (phone && countrySelect) {
        var digits = phone.replace(/\D/g, '');
        var provincePrefix = (countryCode === '+54' && provinceSelect && !provinceSelect.classList.contains('hidden')) ? provinceSelect.value : '';
        var fullNumber = countryCode + ' ';
        if (provincePrefix && !digits.startsWith(provincePrefix)) {
            fullNumber += provincePrefix + ' ' + digits;
        } else {
            fullNumber += digits;
        }
        phoneInput.value = fullNumber.trim();
    }
});

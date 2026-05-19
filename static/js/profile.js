function showSettingsTab(tabName) {
    document.querySelectorAll('.settings-panel').forEach(p => p.classList.add('hidden'));
    document.querySelectorAll('.settings-tab-btn').forEach(b => {
        b.classList.remove('active');
        b.classList.add('text-white/70');
    });

    const panel = document.getElementById('panel-' + tabName);
    if (panel) panel.classList.remove('hidden');

    const btn = document.getElementById('tab-' + tabName);
    if (btn) {
        btn.classList.add('active');
        btn.classList.remove('text-white/70');
    }

    if (tabName === 'solicitudes') {
        loadUserLeads();
    }

    if (window.lucide) lucide.createIcons();
}

function loadUserLeads() {
    const tbody = document.getElementById('leads-tbody');
    if (!tbody) return;

    fetch('/api/profile/leads')
        .then(r => r.json())
        .then(data => {
            if (!data.success || !data.leads || data.leads.length === 0) {
                tbody.innerHTML = '';
                const noMsg = document.getElementById('no-leads-msg');
                if (noMsg) noMsg.classList.remove('hidden');
                return;
            }

            const noMsg = document.getElementById('no-leads-msg');
            if (noMsg) noMsg.classList.add('hidden');

            tbody.innerHTML = data.leads.map(lead => {
                const budgetSymbol = lead.currency === 'USD' ? 'US$' : lead.currency === 'EUR' ? 'EUR' : '$';
                return `
                <tr class="border-b border-midnight/5 hover:bg-paper transition-colors">
                    <td class="p-4 text-sm font-semibold text-midnight">#${lead.id}</td>
                    <td class="p-4 text-sm text-midnight/70">${lead.type || '-'}</td>
                    <td class="p-4 text-sm text-midnight/70">${lead.zone || '-'}</td>
                    <td class="p-4 text-sm text-midnight/70">${budgetSymbol} ${lead.budget || '-'}</td>
                    <td class="p-4 text-sm text-midnight/40">${lead.timestamp || '-'}</td>
                    <td class="p-4">
                        <a href="/mi-perfil/lead/${lead.id}/editar"
                           class="inline-flex items-center gap-1 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all duration-300">
                            <i data-lucide="edit-3" class="w-3 h-3"></i>
                            Editar
                        </a>
                    </td>
                </tr>`;
            }).join('');

            if (window.lucide) lucide.createIcons();
        })
        .catch(() => {
            tbody.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-rose-500 text-sm">Error al cargar solicitudes</td></tr>';
        });
}

function saveUserProfile() {
    const btn = document.getElementById('save-profile-btn');
    const msg = document.getElementById('profile-save-msg');
    const err = document.getElementById('profile-error-msg');

    if (btn) {
        btn.classList.add('save-btn-saving');
        btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Guardando...';
    }
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    const phoneInput = document.getElementById('profile-phone');
    const countryCode = document.getElementById('profile-country-code').value;
    const rawPhone = phoneInput.value.trim();
    const fullPhone = rawPhone ? formatProfilePhone(rawPhone, countryCode) : '';

    const data = {
        email: document.getElementById('profile-email').value,
        phone: fullPhone,
        first_name: document.getElementById('profile-first-name').value,
        last_name: document.getElementById('profile-last-name').value,
        bio: document.getElementById('profile-bio').value,
    };

    fetch('/api/profile/user', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
        } else {
            if (msg) msg.classList.remove('hidden');
        }
    })
    .catch(() => {
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
    })
    .finally(() => {
        if (btn) {
            btn.classList.remove('save-btn-saving');
            btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Cambios';
            if (window.lucide) lucide.createIcons();
        }
    });
}

function formatProfilePhone(phone, countryCode) {
    const digits = phone.replace(/\D/g, '');
    const codeDigits = countryCode.replace('+', '');
    if (digits.startsWith(codeDigits)) return countryCode + ' ' + digits.substring(codeDigits.length);
    return countryCode + ' ' + digits;
}

function validateProfilePhone() {
    const phoneInput = document.getElementById('profile-phone');
    const hint = document.getElementById('profile-phone-hint');
    const valid = document.getElementById('profile-phone-valid');
    const invalid = document.getElementById('profile-phone-invalid');
    const raw = phoneInput.value.trim();

    if (!raw) {
        hint.classList.remove('hidden');
        valid.classList.add('hidden');
        invalid.classList.add('hidden');
        phoneInput.classList.remove('border-emerald-500', 'border-rose-500');
        phoneInput.classList.add('border-midnight/20');
        return;
    }

    const digits = raw.replace(/\D/g, '');
    if (digits.length >= 8 && digits.length <= 15) {
        hint.classList.add('hidden');
        valid.classList.remove('hidden');
        invalid.classList.add('hidden');
        phoneInput.classList.remove('border-midnight/20', 'border-rose-500');
        phoneInput.classList.add('border-emerald-500');
    } else {
        hint.classList.add('hidden');
        valid.classList.add('hidden');
        invalid.classList.remove('hidden');
        phoneInput.classList.remove('border-midnight/20', 'border-emerald-500');
        phoneInput.classList.add('border-rose-500');
    }
}

function updateProfilePhoneFormat() {
    const phoneInput = document.getElementById('profile-phone');
    const countryCode = document.getElementById('profile-country-code').value;
    const raw = phoneInput.value.trim();
    if (raw) {
        const digits = raw.replace(/\D/g, '');
        const codeDigits = countryCode.replace('+', '');
        if (digits.startsWith(codeDigits)) {
            phoneInput.value = digits.substring(codeDigits.length);
        }
        validateProfilePhone();
    }
}

function savePhoneFromProfile() {
    const btn = document.getElementById('save-phone-btn');
    const err = document.getElementById('profile-phone-error');
    const phoneInput = document.getElementById('profile-phone');
    const countryCode = document.getElementById('profile-country-code').value;
    const raw = phoneInput.value.trim();

    if (err) err.classList.add('hidden');

    if (!raw) {
        if (err) { err.textContent = 'Ingresa un numero de telefono.'; err.classList.remove('hidden'); }
        return;
    }

    const digits = raw.replace(/\D/g, '');
    if (digits.length < 8 || digits.length > 15) {
        if (err) { err.textContent = 'El telefono debe tener entre 8 y 15 digitos.'; err.classList.remove('hidden'); }
        return;
    }

    const fullPhone = formatProfilePhone(raw, countryCode);
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> Guardando...';
    btn.disabled = true;
    if (window.lucide) lucide.createIcons();

    fetch('/api/profile/user', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: fullPhone }),
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
        } else {
            btn.innerHTML = '<i data-lucide="check" class="w-3 h-3"></i> Guardado';
            btn.classList.add('text-emerald-600');
            if (window.lucide) lucide.createIcons();
            setTimeout(() => {
                btn.innerHTML = originalContent;
                btn.classList.remove('text-emerald-600');
                btn.disabled = false;
                if (window.lucide) lucide.createIcons();
            }, 3000);
        }
    })
    .catch(() => {
        if (err) { err.textContent = 'Error de conexion.'; err.classList.remove('hidden'); }
        btn.innerHTML = originalContent;
        btn.disabled = false;
        if (window.lucide) lucide.createIcons();
    });
}

function changePassword() {
    const btn = document.getElementById('save-password-btn');
    const msg = document.getElementById('password-save-msg');
    const err = document.getElementById('password-error-msg');

    if (btn) {
        btn.classList.add('save-btn-saving');
        btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Actualizando...';
    }
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    const current = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirm = document.getElementById('confirm-password').value;

    if (!current || !newPass || !confirm) {
        if (err) { err.textContent = 'Todos los campos son requeridos'; err.classList.remove('hidden'); }
        resetPasswordBtn();
        return;
    }

    if (newPass !== confirm) {
        if (err) { err.textContent = 'Las contrasenas no coinciden'; err.classList.remove('hidden'); }
        resetPasswordBtn();
        return;
    }

    fetch('/api/profile/user/password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: current, new_password: newPass }),
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
        } else {
            if (msg) msg.classList.remove('hidden');
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        }
    })
    .catch(() => {
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
    })
    .finally(() => {
        resetPasswordBtn();
    });

    function resetPasswordBtn() {
        if (btn) {
            btn.classList.remove('save-btn-saving');
            btn.innerHTML = '<i data-lucide="lock" class="w-4 h-4"></i> Cambiar Contrasena';
            if (window.lucide) lucide.createIcons();
        }
    }
}

function saveProfessionalData() {
    const btn = document.getElementById('save-prof-btn');
    const msg = document.getElementById('prof-save-msg');
    const err = document.getElementById('prof-error-msg');

    if (btn) {
        btn.classList.add('save-btn-saving');
        btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Guardando...';
    }
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    const data = {
        specialty: document.getElementById('prof-specialty').value,
        title: document.getElementById('prof-title').value,
    };

    fetch('/api/profile/professional', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
        } else {
            if (msg) msg.classList.remove('hidden');
        }
    })
    .catch(() => {
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
    })
    .finally(() => {
        if (btn) {
            btn.classList.remove('save-btn-saving');
            btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Cambios';
            if (window.lucide) lucide.createIcons();
        }
    });
}

function loadProfessionalData() {
    fetch('/api/profile/professional')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.professional) {
                const specialty = document.getElementById('prof-specialty');
                const title = document.getElementById('prof-title');
                if (specialty) specialty.value = data.professional.specialty || '';
                if (title) title.value = data.professional.title || '';
            }
        })
        .catch(() => {});
}

function initEditLeadForm(leadId) {
    const form = document.getElementById('editLeadForm');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const btn = document.getElementById('save-lead-btn');
        const msg = document.getElementById('lead-save-msg');
        const err = document.getElementById('lead-error-msg');

        if (btn) {
            btn.classList.add('save-btn-saving');
            btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Guardando...';
        }
        if (msg) msg.classList.add('hidden');
        if (err) err.classList.add('hidden');

        const checkedAmenities = [];
        document.querySelectorAll('.amenity-checkbox:checked').forEach(cb => {
            checkedAmenities.push(cb.value);
        });

        const landArea = parseFloat(document.getElementById('edit-land-area').value || '0');
        const builtArea = parseFloat(document.getElementById('edit-built-area').value || '0');
        if (landArea > 0 && builtArea > 0 && builtArea > landArea * 0.8) {
            if (err) { err.textContent = 'Los metros construidos no pueden superar el 80% del terreno.'; err.classList.remove('hidden'); }
            if (btn) {
                btn.classList.remove('save-btn-saving');
                btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Cambios';
                if (window.lucide) lucide.createIcons();
            }
            return;
        }

        const data = {
            zone: document.getElementById('edit-zone').value,
            budget: document.getElementById('edit-budget').value,
            currency: document.getElementById('edit-currency').value,
            floor_block: document.getElementById('edit-floor-block').value,
            usable_m2: document.getElementById('edit-usable-m2').value,
            elevator: document.getElementById('edit-elevator').value,
            land_area: document.getElementById('edit-land-area').value,
            built_area: document.getElementById('edit-built-area').value,
            pool: document.getElementById('edit-pool').value,
            architectural_style: document.getElementById('edit-architectural-style').value,
            bedrooms: document.getElementById('edit-bedrooms').value,
            bathrooms: document.getElementById('edit-bathrooms').value,
            total_area: document.getElementById('edit-total-area').value,
            amenities: checkedAmenities.join(', '),
            ambientes: document.getElementById('edit-ambientes').value,
            parking: document.getElementById('edit-parking').value,
            orientation: document.getElementById('edit-orientation').value,
            property_condition: document.getElementById('edit-property-condition').value,
            property_age: document.getElementById('edit-property-age').value,
        };

        fetch(`/api/profile/lead/${leadId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        })
        .then(r => r.json())
        .then(result => {
            if (result.error) {
                if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
            } else {
                if (msg) msg.classList.remove('hidden');
                setTimeout(() => {
                    window.location.href = '/mi-perfil';
                }, 1500);
            }
        })
        .catch(() => {
            if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
        })
        .finally(() => {
            if (btn) {
                btn.classList.remove('save-btn-saving');
                btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Cambios';
                if (window.lucide) lucide.createIcons();
            }
        });
    });
}

function stepEditNum(fieldId, delta) {
    const el = document.getElementById(fieldId);
    if (!el) return;
    const min = parseInt(el.min) ?? 0;
    const max = parseInt(el.max) || 99;
    const cur = parseInt(el.value) || 0;
    const next = cur + delta;
    el.value = next < min ? '' : Math.min(max, next);
}

const EDIT_CHIP_GROUPS = {
    parking:     { hidden: 'edit-parking',     cls: 'edit-parking-chip' },
    orientation: { hidden: 'edit-orientation', cls: 'edit-orientation-chip' },
    condition:   { hidden: 'edit-property-condition', cls: 'edit-condition-chip' },
    age:         { hidden: 'edit-property-age', cls: 'edit-age-chip' },
};

const EDIT_CHIP_BASE = {
    parking:     'edit-parking-chip px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    orientation: 'edit-orientation-chip px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    condition:   'edit-condition-chip w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    age:         'edit-age-chip w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
};

function selectEditChip(group, value) {
    const g = EDIT_CHIP_GROUPS[group];
    if (!g) return;
    document.getElementById(g.hidden).value = value;
    document.querySelectorAll('.' + g.cls).forEach(btn => {
        const active = btn.dataset.value === value;
        btn.className = EDIT_CHIP_BASE[group] + ' '
            + (active
                ? 'border-midnight bg-midnight text-white'
                : 'border-midnight/20 text-midnight hover:border-gold');
    });
    if (group === 'condition') syncEditAgeToCondition(value);
}

function syncEditAgeToCondition(condition) {
    const ageSection = document.getElementById('edit-age-section');
    const ageChips   = document.querySelectorAll('.edit-age-chip');

    if (condition === 'A estrenar') {
        selectEditChip('age', 'Hasta 5 anios');
        ageChips.forEach(btn => {
            const isForced = btn.dataset.value === 'Hasta 5 anios';
            btn.disabled = !isForced;
            btn.style.opacity = isForced ? '1' : '0.35';
            btn.style.cursor  = isForced ? 'default' : 'not-allowed';
        });
        if (ageSection) ageSection.classList.remove('hidden');
    } else if (condition === 'En construccion') {
        selectEditChip('age', '');
        if (ageSection) ageSection.classList.add('hidden');
    } else if (condition === 'A reciclar') {
        if (ageSection) ageSection.classList.remove('hidden');
        ageChips.forEach(btn => { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
        selectEditChip('age', 'Mas de 30 anios');
    } else {
        if (ageSection) ageSection.classList.remove('hidden');
        ageChips.forEach(btn => { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
    }
}

function initEditChips() {
    const lead = window.__leadData || {};

    if (lead.parking) selectEditChip('parking', lead.parking);
    if (lead.orientation) selectEditChip('orientation', lead.orientation);
    if (lead.property_condition) selectEditChip('condition', lead.property_condition);
    if (lead.property_age) selectEditChip('age', lead.property_age);

    initAreaValidation();

    if (window.lucide) lucide.createIcons();
}

function initAreaValidation() {
    const landInput = document.getElementById('edit-land-area');
    const builtInput = document.getElementById('edit-built-area');
    const warning = document.getElementById('edit-area-warning');
    const hint = document.getElementById('edit-area-hint');
    if (!landInput || !builtInput || !warning || !hint) return;

    function checkArea() {
        const land = parseFloat(landInput.value || '0');
        const built = parseFloat(builtInput.value || '0');
        if (land > 0 && built > 0 && built > land * 0.8) {
            warning.classList.remove('hidden');
            hint.classList.add('hidden');
            builtInput.classList.add('border-rose-500');
            builtInput.classList.remove('border-midnight/20');
        } else {
            warning.classList.add('hidden');
            hint.classList.remove('hidden');
            builtInput.classList.remove('border-rose-500');
            builtInput.classList.add('border-midnight/20');
        }
    }

    landInput.addEventListener('input', checkArea);
    builtInput.addEventListener('input', checkArea);
    checkArea();
}

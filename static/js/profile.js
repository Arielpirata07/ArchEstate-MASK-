// ============================================================
// PROFILE SETTINGS — ArchEstate
// ============================================================

function initSettingsPage() {
    loadUserLeads();
    loadUserSettings();
    initPhoneFromServer();
    validateProfileEmail();
    validateProfilePhone();
    loadPreferredChannel();
}

// ============================================================
// ACCESSIBLE TABS
// ============================================================
function showSettingsTab(tabName) {
    document.querySelectorAll('[role="tabpanel"]').forEach(p => p.hidden = true);
    document.querySelectorAll('[role="tab"]').forEach(t => {
        t.setAttribute('aria-selected', 'false');
        t.classList.remove('active');
        t.tabIndex = -1;
    });

    const panel = document.getElementById('panel-' + tabName);
    if (panel) {
        panel.hidden = false;
        panel.classList.remove('panel-enter');
        void panel.offsetWidth;
        panel.classList.add('panel-enter');
    }

    const tab = document.getElementById('tab-' + tabName);
    if (tab) {
        tab.setAttribute('aria-selected', 'true');
        tab.classList.add('active');
        tab.tabIndex = 0;
        tab.focus();
    }

    if (tabName === 'solicitudes') loadUserLeads();
    if (tabName === 'seguridad') loadUserSessions();
    if (tabName === 'actividad') loadUserActivity();
    if (tabName === 'profesional') { loadProfessionalFullProfile(); loadCoverage(); }

    if (window.lucide) lucide.createIcons();
}

// Keyboard nav for tabs
document.addEventListener('keydown', function(e) {
    const tabs = document.querySelectorAll('[role="tab"]');
    if (!tabs.length) return;
    const current = document.activeElement;
    if (!current || current.getAttribute('role') !== 'tab') return;

    const idx = Array.from(tabs).indexOf(current);
    if (idx < 0) return;

    let newIdx = -1;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') newIdx = (idx + 1) % tabs.length;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') newIdx = (idx - 1 + tabs.length) % tabs.length;
    if (e.key === 'Home') newIdx = 0;
    if (e.key === 'End') newIdx = tabs.length - 1;

    if (newIdx >= 0) {
        e.preventDefault();
        const tabName = tabs[newIdx].id.replace('tab-', '');
        showSettingsTab(tabName);
    }
});

// ============================================================
// USER PROFILE
// ============================================================
function saveUserProfile() {
    const btn = document.getElementById('save-profile-btn');
    const msg = document.getElementById('profile-save-msg');
    const err = document.getElementById('profile-error-msg');

    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> ' + t('action.saving');
    if (window.lucide) lucide.createIcons();
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
            setTimeout(() => msg.classList.add('hidden'), 3000);
            updatePhoneVerificationArea(fullPhone);
        }
    })
    .catch(() => {
        if (err) { err.textContent = t('error.connection'); err.classList.remove('hidden'); }
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> ' + t('action.save_changes');
        if (window.lucide) lucide.createIcons();
    });
}

function updatePhoneVerificationArea(phone) {
    const area = document.getElementById('phone-verification-area');
    if (!area) return;
    area.innerHTML = '<span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest bg-paper-dark text-midnight/60 inline-flex items-center gap-1">'
        + '<i data-lucide="phone-off" class="w-3 h-3"></i> ' + t('phone.not_verified') + '</span>'
        + '<button type="button" id="verify-phone-btn"'
        + ' class="text-[10px] uppercase tracking-widest font-bold text-gold hover:text-midnight transition-colors"'
        + ' onclick="openPhoneVerifyModal()">' + t('action.verify') + '</button>';
    if (window.lucide) lucide.createIcons();
}

// ============================================================
// AVATAR
// ============================================================
function uploadAvatar(input) {
    const file = input.files[0];
    if (!file) return;

    const status = document.getElementById('avatar-status');
    if (status) { status.textContent = t('action.uploading'); status.className = 'text-[9px] mt-1 text-amber-500'; }

    const formData = new FormData();
    formData.append('avatar', file);

    fetch('/api/profile/user/avatar', {
        method: 'POST',
        body: formData,
    })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
        if (ok && data.avatar_url) {
            const img = document.getElementById('avatar-preview');
            if (img) img.src = data.avatar_url;
            const ring = document.getElementById('avatar-ring');
            if (img && ring) {
                img.addEventListener('load', function() { extractAvatarColors(img, ring); });
            }
            if (status) { status.textContent = t('avatar.updated'); status.className = 'text-[9px] mt-1 text-emerald-600'; }
        } else {
            if (status) { status.textContent = data.error || t('error.avatar_upload'); status.className = 'text-[9px] mt-1 text-rose-500'; }
        }
        input.value = '';
    })
    .catch(() => {
        if (status) { status.textContent = t('error.connection'); status.className = 'text-[9px] mt-1 text-rose-500'; }
        input.value = '';
    });
}

function deleteAvatar() {
    var promise = typeof showConfirm === 'function' ? showConfirm(t('confirm.delete_avatar')) : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
        var status = document.getElementById('avatar-status');
        if (status) { status.textContent = t('action.deleting'); status.className = 'text-[9px] mt-1 text-amber-500'; }
        fetch('/api/profile/user/avatar', { method: 'DELETE' })
        .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
        .then(function (res) {
            if (res.ok) {
                var img = document.getElementById('avatar-preview');
                if (img) img.src = '/static/img/default-avatar.svg';
                var ring = document.getElementById('avatar-ring');
                if (ring) ring.classList.remove('visible');
                if (status) { status.textContent = t('avatar.deleted'); status.className = 'text-[9px] mt-1 text-emerald-600'; }
            } else {
                if (status) { status.textContent = t('error.avatar_delete'); status.className = 'text-[9px] mt-1 text-rose-500'; }
            }
        })
        .catch(function () {
            if (status) { status.textContent = t('error.connection'); status.className = 'text-[9px] mt-1 text-rose-500'; }
        });
    });
}

// ============================================================
// PHONE FORMAT
// ============================================================
function normalizeArgentineAreaCode(value) {
    const digits = String(value || '').replace(/\D/g, '');
    if (!digits) return '';
    return digits.replace(/^0(?=\d)/, '');
}

function getSelectedArgentineAreaCode() {
    const provinceSelect = document.getElementById('profile-province');
    const customAreaInput = document.getElementById('profile-custom-area');
    if (!provinceSelect) return '';
    if (provinceSelect.value === 'other') {
        return normalizeArgentineAreaCode(customAreaInput ? customAreaInput.value : '');
    }
    return normalizeArgentineAreaCode(provinceSelect.value);
}

function formatProfilePhone(phone, countryCode) {
    const digits = phone.replace(/\D/g, '');
    const provinceSelect = document.getElementById('profile-province');
    const customAreaInput = document.getElementById('profile-custom-area');

    const codeDigits = countryCode.replace('+', '');
    let localDigits = digits;
    if (localDigits.startsWith(codeDigits)) {
        localDigits = localDigits.substring(codeDigits.length);
    }

    const prefix = getSelectedArgentineAreaCode();
    if (prefix) {
        let local = localDigits;
        const prefixCandidates = [prefix, `0${prefix}`];
        const matchedPrefix = prefixCandidates.find(candidate => local.startsWith(candidate));
        if (matchedPrefix) {
            local = local.substring(matchedPrefix.length);
        }
        if (countryCode === '+54') {
            let mobilePrefix = '';
            if (local.startsWith('9')) { mobilePrefix = '9'; local = local.substring(1); }
            else if (local.startsWith('15')) { mobilePrefix = '15'; local = local.substring(2); }
            if (mobilePrefix !== '9') mobilePrefix = '9';
            return (countryCode + ' 9 ' + prefix + ' ' + local).trim();
        }
        return (countryCode + ' ' + prefix + ' ' + local).trim();
    }
    if (typeof PhoneSuggest !== 'undefined') {
        return PhoneSuggest.formatNational(countryCode, localDigits);
    }
    return (countryCode + ' ' + localDigits).trim();
}

function initPhoneFromServer() {
    const phoneInput = document.getElementById('profile-phone');
    const countrySelect = document.getElementById('profile-country-code');
    const provinceSelect = document.getElementById('profile-province');
    const customAreaInput = document.getElementById('profile-custom-area');
    if (!phoneInput || !countrySelect) return;

    const currentPhone = phoneInput.value.trim();
    if (currentPhone) {
        const match = currentPhone.match(/^(\+\d+)/);
        if (match) {
            const code = match[1];
            const options = countrySelect.querySelectorAll('option');
            for (const opt of options) {
                if (opt.value === code) { opt.selected = true; break; }
            }
            const digits = currentPhone.replace(/\D/g, '');
            const codeDigits = code.replace('+', '');
            const withoutCode = digits.substring(codeDigits.length);
            const info = (typeof PhoneSuggest !== 'undefined') ? PhoneSuggest.getRegionInfo(code, withoutCode) : null;
            if (info && provinceSelect) {
                let matched = false;
                for (const opt of provinceSelect.options) {
                    if (opt.value === 'other') continue;
                    if (opt.value === info.code) { opt.selected = true; matched = true; break; }
                }
                if (!matched) provinceSelect.value = 'other';
                let searchDigits = withoutCode;
                let mobilePrefix = '';
                if (code === '+54') {
                    if (searchDigits.startsWith('15')) { mobilePrefix = '15'; searchDigits = searchDigits.substring(2); }
                    else if (searchDigits.startsWith('9')) { mobilePrefix = '9'; searchDigits = searchDigits.substring(1); }
                }
                if (searchDigits.startsWith(info.code)) searchDigits = searchDigits.substring(info.code.length);
                else if (searchDigits.startsWith('0' + info.code)) searchDigits = searchDigits.substring(info.code.length + 1);
                if (matched && customAreaInput) {
                    customAreaInput.classList.add('hidden');
                } else if (customAreaInput) {
                    customAreaInput.classList.remove('hidden');
                    customAreaInput.value = info.code;
                }
                phoneInput.value = (mobilePrefix ? mobilePrefix + ' ' : '') + searchDigits;
            } else {
                phoneInput.value = withoutCode;
                if (customAreaInput) customAreaInput.classList.add('hidden');
            }
        }
    }
    updateProfilePhoneFormat();
}

function updateProfilePhoneFormat() {
    const phoneInput = document.getElementById('profile-phone');
    const countryCode = document.getElementById('profile-country-code').value;
    const provinceSelect = document.getElementById('profile-province');
    const customAreaInput = document.getElementById('profile-custom-area');
    if (typeof PhoneSuggest !== 'undefined') {
        PhoneSuggest.populateAreaSelect(provinceSelect, countryCode);
    }
    let totalOpts = 0;
    if (provinceSelect) {
        for (let i = 0; i < provinceSelect.options.length; i++) {
            if (provinceSelect.options[i].value !== 'other') totalOpts++;
        }
    }
    showProvinceSearchToggle(totalOpts > 20);
    if (customAreaInput) customAreaInput.classList.add('hidden');
    validateProfilePhone();
}

function applyProvincePrefix() {
    const phoneInput = document.getElementById('profile-phone');
    const provinceSelect = document.getElementById('profile-province');
    const customAreaInput = document.getElementById('profile-custom-area');
    const countryCode = document.getElementById('profile-country-code').value;
    const prefix = provinceSelect.value;
    if (customAreaInput) {
        customAreaInput.classList.toggle('hidden', prefix !== 'other');
    }
    let searchRaw = phoneInput.value.trim().replace(/\D/g, '');

    // El campo puede traer pegado un codigo de area (y su marcador movil) de
    // una seleccion de provincia anterior -- el usuario cambio de opcion mas
    // de una vez. Pelamos capas -- marcador movil o codigo de area conocido
    // para este pais, en cualquier orden -- hasta que no quede nada mas para
    // sacar, en vez de intentar sacar solo el codigo que se esta por aplicar
    // ahora (eso dejaba codigos viejos acumulados dentro del numero local).
    const knownCodes = (typeof PhoneSuggest !== 'undefined') ? PhoneSuggest.phoneAreaCodes(countryCode) : [];
    let mobilePrefix = '';
    for (let pass = 0; pass < 4; pass++) {
        let changed = false;
        if (countryCode === '+54') {
            if (searchRaw.startsWith('15')) { searchRaw = searchRaw.substring(2); mobilePrefix = '15'; changed = true; }
            else if (searchRaw.startsWith('9')) { searchRaw = searchRaw.substring(1); mobilePrefix = '9'; changed = true; }
        }
        for (const code of knownCodes) {
            if (searchRaw.startsWith(code)) { searchRaw = searchRaw.substring(code.length); changed = true; break; }
        }
        if (!changed) break;
    }

    const selectedPrefix = prefix === 'other'
        ? normalizeArgentineAreaCode(customAreaInput ? customAreaInput.value : '')
        : normalizeArgentineAreaCode(prefix);

    if (!selectedPrefix) {
        phoneInput.value = searchRaw.length > 0 ? (mobilePrefix ? mobilePrefix + ' ' : '') + searchRaw : '';
        validateProfilePhone();
        return;
    }

    phoneInput.value = (countryCode === '+54' ? selectedPrefix + ' 9 ' : selectedPrefix + ' ') + searchRaw;
    validateProfilePhone();
}

function validateProfileEmail() {
    const input = document.getElementById('profile-email');
    const hint = document.getElementById('profile-email-hint');
    const valid = document.getElementById('profile-email-valid');
    const invalid = document.getElementById('profile-email-invalid');
    const email = input.value.trim();
    if (!email) {
        if (hint) hint.classList.remove('hidden');
        if (valid) valid.classList.add('hidden');
        if (invalid) invalid.classList.add('hidden');
        return;
    }
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (re.test(email)) {
        if (hint) hint.classList.add('hidden');
        if (valid) valid.classList.remove('hidden');
        if (invalid) invalid.classList.add('hidden');
    } else {
        if (hint) hint.classList.add('hidden');
        if (valid) valid.classList.add('hidden');
        if (invalid) invalid.classList.remove('hidden');
    }
}

let _lastPhoneSuggestion = '';

function validateProfilePhone() {
    const input = document.getElementById('profile-phone');
    const hint = document.getElementById('profile-phone-hint');
    const valid = document.getElementById('profile-phone-valid');
    const invalid = document.getElementById('profile-phone-invalid');
    const suggestionEl = document.getElementById('profile-phone-suggestion');
    const previewEl = document.getElementById('phone-correction-preview');
    const cityEl = document.getElementById('profile-phone-city');
    _lastPhoneSuggestion = '';
    if (suggestionEl) suggestionEl.classList.add('hidden');
    if (previewEl) previewEl.classList.add('hidden');
    if (cityEl) { cityEl.classList.add('hidden'); cityEl.textContent = ''; }
    const raw = input.value.trim();
    if (!raw) {
        if (hint) hint.classList.remove('hidden');
        if (valid) valid.classList.add('hidden');
        if (invalid) invalid.classList.add('hidden');
        return;
    }
    const digits = raw.replace(/\D/g, '');
    const countryCode = document.getElementById('profile-country-code').value;
    const codeDigits = countryCode.replace('+', '');
    const localDigits = digits.startsWith(codeDigits) ? digits.substring(codeDigits.length) : digits;
    const isValid = (typeof PhoneSuggest !== 'undefined')
        ? PhoneSuggest.isPlausible(countryCode, localDigits)
        : (localDigits.length >= 6 && localDigits.length <= 12);
    if (isValid) {
        if (hint) hint.classList.add('hidden');
        if (valid) valid.classList.remove('hidden');
        if (invalid) invalid.classList.add('hidden');
    } else {
        if (hint) hint.classList.add('hidden');
        if (valid) valid.classList.add('hidden');
        if (invalid) invalid.classList.remove('hidden');
    }
    if (localDigits.length > 0) {
        const label = (typeof PhoneSuggest !== 'undefined') ? PhoneSuggest.getRegionLabel(countryCode, localDigits) : null;
        if (label && cityEl) {
            cityEl.textContent = label.city + ', ' + label.province;
            cityEl.classList.remove('hidden');
        }
        const suggestion = (typeof PhoneSuggest !== 'undefined') ? PhoneSuggest.suggestNationalNumber(countryCode, localDigits) : null;
        if (suggestion) {
            const sugNational = suggestion.replace(/^(\+\d+)\s*/, '').replace(/\D/g, '');
            if (sugNational !== localDigits) {
                _lastPhoneSuggestion = suggestion;
                if (suggestionEl) suggestionEl.classList.remove('hidden');
            }
        }
    }
}

function showPhoneCorrection() {
    if (!_lastPhoneSuggestion) return;
    const input = document.getElementById('profile-phone');
    const countryCode = document.getElementById('profile-country-code').value;
    const fromEl = document.getElementById('correction-from');
    const toEl = document.getElementById('correction-to');
    const previewEl = document.getElementById('phone-correction-preview');
    const from = countryCode + ' ' + input.value.trim();
    if (fromEl) fromEl.textContent = from;
    if (toEl) toEl.textContent = _lastPhoneSuggestion;
    if (previewEl) previewEl.classList.remove('hidden');
}

function applyPhoneCorrection() {
    if (!_lastPhoneSuggestion) return;
    const phoneInput = document.getElementById('profile-phone');
    const countrySelect = document.getElementById('profile-country-code');
    const provinceSelect = document.getElementById('profile-province');
    const customAreaInput = document.getElementById('profile-custom-area');
    const previewEl = document.getElementById('phone-correction-preview');
    const suggestion = _lastPhoneSuggestion;
    const match = suggestion.match(/^(\+\d+)\s+(.*)$/);
    if (!match) return;
    const code = match[1];
    for (const opt of countrySelect.options) {
        if (opt.value === code) { opt.selected = true; break; }
    }
    if (code === '+54') {
        const parts = match[2].split(/\s+/);
        let mobile = '';
        let area = '';
        let local = [];
        if (parts.length >= 2 && (parts[0] === '9' || parts[0] === '15')) {
            mobile = parts[0];
            area = parts[1];
            local = parts.slice(2);
        } else if (parts.length > 0) {
            area = parts[0];
            local = parts.slice(1);
        }
        if (provinceSelect) {
            let matched = false;
            for (const opt of provinceSelect.options) {
                if (opt.value === area) { opt.selected = true; matched = true; break; }
            }
            if (!matched) {
                provinceSelect.value = 'other';
                if (customAreaInput) {
                    customAreaInput.classList.remove('hidden');
                    customAreaInput.value = area;
                }
            } else if (customAreaInput) {
                customAreaInput.classList.add('hidden');
                customAreaInput.value = '';
            }
        }
        phoneInput.value = (mobile ? mobile + ' ' : '') + area + ' ' + local.join(' ');
    } else {
        phoneInput.value = match[2];
        if (customAreaInput) customAreaInput.classList.add('hidden');
        if (provinceSelect) provinceSelect.value = 'other';
    }
    if (previewEl) previewEl.classList.add('hidden');
    updateProfilePhoneFormat();
}

function dismissPhoneCorrection() {
    const previewEl = document.getElementById('phone-correction-preview');
    if (previewEl) previewEl.classList.add('hidden');
}

function loadPreferredChannel() {
    const select = document.getElementById('preferred-channel-select');
    if (!select) return;
    fetch('/api/profile/settings')
        .then(r => r.json())
        .then(data => {
            if (data.settings && data.settings.preferred_channel) {
                select.value = data.settings.preferred_channel;
            }
            toggleWhatsappHint();
        })
        .catch(() => {});
}

function toggleWhatsappHint() {
    const select = document.getElementById('preferred-channel-select');
    const hint = document.getElementById('whatsapp-hint');
    const modalHint = document.getElementById('modal-whatsapp-hint');
    const isWhatsapp = select && select.value === 'whatsapp';
    if (hint) hint.classList.toggle('hidden', !isWhatsapp);
    if (modalHint) modalHint.classList.toggle('hidden', !isWhatsapp);
}


function savePreferredChannel() {
    const select = document.getElementById('preferred-channel-select');
    if (!select) return;
    fetch('/api/profile/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferred_channel: select.value })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            if (typeof showToast === 'function') showToast(data.error, 'error');
        }
    })
    .catch(() => {});
}

function filterProvinceSelect(selectId, query) {
    var sel = document.getElementById(selectId);
    if (!sel) return;
    
    if (!sel._allOptions) {
        // Guardar copia de las opciones originales la primera vez que se filtra
        sel._allOptions = Array.from(sel.options).map(o => ({ value: o.value, text: o.text }));
    }
    
    var currentVal = sel.value;
    var q = (query || '').toLowerCase().trim();
    
    sel.innerHTML = '';
    
    sel._allOptions.forEach(function(item) {
        if (item.value === 'other' || !q || item.text.toLowerCase().indexOf(q) !== -1 || String(item.value).toLowerCase().indexOf(q) !== -1) {
            var opt = document.createElement('option');
            opt.value = item.value;
            opt.textContent = item.text;
            if (item.value === currentVal) opt.selected = true;
            sel.appendChild(opt);
        }
    });
}

function toggleProvinceSearch(selectId, btn) {
    var wrapper = document.getElementById('province-search-wrapper');
    if (!wrapper) return;
    var isOpen = !wrapper.classList.contains('hidden');
    if (isOpen) {
        wrapper.classList.add('hidden');
        if (btn) btn.setAttribute('aria-expanded', 'false');
    } else {
        wrapper.classList.remove('hidden');
        if (btn) btn.setAttribute('aria-expanded', 'true');
        var input = document.getElementById('province-search');
        if (input) {
            input.focus();
            input.select();
            onProvinceSearchInput(selectId, input);
        }
    }
}

function provinceNormalize(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function getProvinceOptions(selectId) {
    var sel = document.getElementById(selectId);
    if (!sel) return [];
    if (!sel._allOptions) {
        sel._allOptions = Array.from(sel.options).map(function(o) {
            return { value: o.value, text: o.textContent, state: o.getAttribute('data-state') || '' };
        });
    }
    return sel._allOptions;
}

function provinceApplyFunction(selectId) {
    if (selectId === 'profile-province' && typeof applyProvincePrefix === 'function') return applyProvincePrefix;
    if (typeof applyPhoneProvincePrefix === 'function') return applyPhoneProvincePrefix;
    return null;
}

function onProvinceSearchInput(selectId, input) {
    var list = document.getElementById('province-search-list');
    if (!list) return;
    var q = provinceNormalize(input.value);
    var matches = [];
    getProvinceOptions(selectId).forEach(function(o) {
        if (o.value === 'other') return;
        if (!q || provinceNormalize(o.text).indexOf(q) !== -1) matches.push(o);
    });
    list.innerHTML = '';
    var hasOther = getProvinceOptions(selectId).some(function(o) { return o.value === 'other'; });
    if (!matches.length && !hasOther) {
        list.innerHTML = '<li role="status" class="px-4 py-3 text-sm text-midnight/60">' + escapeHtml(window.t('autocomplete.no_matches')) + '</li>';
    } else {
        var html = '';
        if (hasOther) {
            html += '<li role="option" class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="other"><strong class="text-midnight">Otra (código manual)...</strong></li>';
        }
        html += matches.slice(0, 50).map(function(o) {
            var stateInfo = o.state ? '<span class="ml-2 text-[11px] text-midnight/60">' + escapeHtml(o.state) + '</span>' : '';
            return '<li role="option" class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="' + escapeHtml(o.value) + '">' +
                '<strong class="text-midnight">' + escapeHtml(o.text) + '</strong>' + stateInfo + '</li>';
        }).join('');
        list.innerHTML = html;
    }
    list.classList.remove('hidden');
    list.setAttribute('data-select-id', selectId);
}

function provinceSelectCity(selectId, value) {
    var sel = document.getElementById(selectId);
    if (!sel) return;
    sel.value = value;
    var opt = sel.options[sel.selectedIndex];
    var label = document.getElementById('province-search-label');
    if (label) {
        if (opt && opt.textContent) {
            label.textContent = opt.textContent;
            label.classList.remove('text-midnight/70');
        } else {
            label.textContent = 'Buscar ciudad';
            label.classList.add('text-midnight/70');
        }
    }
    var apply = provinceApplyFunction(selectId);
    if (apply) apply();
    var wrapper = document.getElementById('province-search-wrapper');
    if (wrapper) wrapper.classList.add('hidden');
    var btn = document.getElementById('province-search-toggle');
    if (btn) btn.setAttribute('aria-expanded', 'false');
    var input = document.getElementById('province-search');
    if (input) input.value = '';
    var list = document.getElementById('province-search-list');
    if (list) {
        list.classList.add('hidden');
        list.innerHTML = '';
    }
}

function onProvinceSearchKeydown(selectId, e) {
    var list = document.getElementById('province-search-list');
    if (!list || list.classList.contains('hidden')) return;
    var items = list.querySelectorAll('li[data-value]');
    if (!items.length) return;
    var highlighted = list.querySelector('li.highlighted');
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        var current = Array.prototype.indexOf.call(items, highlighted);
        var next;
        if (current === -1) {
            next = e.key === 'ArrowDown' ? 0 : items.length - 1;
        } else {
            next = e.key === 'ArrowDown'
                ? (current + 1) % items.length
                : (current - 1 + items.length) % items.length;
        }
        if (highlighted) highlighted.classList.remove('highlighted');
        items[next].classList.add('highlighted');
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (highlighted) {
            provinceSelectCity(selectId, highlighted.dataset.value);
        }
    } else if (e.key === 'Escape') {
        list.classList.add('hidden');
    }
}

function showProvinceSearchToggle(show) {
    var btn = document.getElementById('province-search-toggle');
    if (!btn) return;
    if (show) {
        btn.classList.remove('hidden');
        btn.classList.add('flex');
    } else {
        btn.classList.add('hidden');
        btn.classList.remove('flex');
        btn.setAttribute('aria-expanded', 'false');
        var wrapper = document.getElementById('province-search-wrapper');
        if (wrapper) wrapper.classList.add('hidden');
    }
}

document.addEventListener('click', function(e) {
    var wrap = document.getElementById('province-search-wrap');
    var wrapper = document.getElementById('province-search-wrapper');
    if (!wrap || !wrapper || wrapper.classList.contains('hidden')) return;
    if (wrap.contains(e.target)) return;
    wrapper.classList.add('hidden');
    var btn = document.getElementById('province-search-toggle');
    if (btn) btn.setAttribute('aria-expanded', 'false');
});

document.addEventListener('click', function(e) {
    var list = document.getElementById('province-search-list');
    if (!list || list.classList.contains('hidden')) return;
    var target = e.target.closest ? e.target.closest('li[data-value]') : null;
    if (!target || !list.contains(target)) return;
    provinceSelectCity(list.getAttribute('data-select-id'), target.getAttribute('data-value'));
});

(function() {
    var label = document.getElementById('province-search-label');
    if (!label) return;
    var sel = document.getElementById('phone-province') || document.getElementById('profile-province');
    if (!sel) return;
    var opt = sel.options[sel.selectedIndex];
    if (opt && opt.value) {
        label.textContent = opt.textContent;
        label.classList.remove('text-midnight/70');
    }
})();

function detectArgAreaCode(digits) {
    if (typeof PhoneSuggest === 'undefined') return null;
    return PhoneSuggest.getRegionLabel('+54', digits);
}

function suggestArgPhone(digits) {
    if (typeof PhoneSuggest === 'undefined') return null;
    return PhoneSuggest.suggestNationalNumber('+54', digits);
}

// ============================================================
// SETTINGS (Theme + Language)
// ============================================================
function loadUserSettings() {
    fetch('/api/profile/settings')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.preferences) return;
        const p = data.preferences;

        // Theme
        setThemeUI(p.theme || 'light');

        // Language
        const langEl = document.getElementById('settings-language');
        if (langEl) langEl.value = p.language || 'es';

        // Notifications
        setToggle('notif-email', p.email_notifications);
        setToggle('notif-sms', p.sms_notifications);
        setToggle('notif-leads', p.lead_alerts);
    })
    .catch(() => {});
}

function setToggle(id, value) {
    const el = document.getElementById(id);
    if (el) el.checked = !!value;
}

function setTheme(theme) {
    const html = document.documentElement;
    if (theme === 'dark') {
        html.classList.add('dark');
    } else {
        html.classList.remove('dark');
    }
    setThemeUI(theme);
    saveSettings();
}

function setThemeUI(theme) {
    // Update theme option buttons
    document.querySelectorAll('.theme-option').forEach(btn => {
        const isActive = btn.dataset.theme === theme;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-pressed', isActive);
    });
    // El CSS maneja la visibilidad de sun/moon via .dark
}

function saveSettings() {
    const langEl = document.getElementById('settings-language');
    const themeBtn = document.querySelector('.theme-option.active');
    const currentLang = document.documentElement.lang || 'es';
    const data = {
        theme: themeBtn ? themeBtn.dataset.theme : 'light',
        language: langEl ? langEl.value : 'es',
        email_notifications: document.getElementById('notif-email')?.checked ? 1 : 0,
        sms_notifications: document.getElementById('notif-sms')?.checked ? 1 : 0,
        lead_alerts: document.getElementById('notif-leads')?.checked ? 1 : 0,
    };

    const msg = document.getElementById('settings-save-msg');
    const err = document.getElementById('settings-error-msg');

    fetch('/api/profile/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(r => r.json())
    .then(result => {
        if (result.error) {
            if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
        } else {
            if (msg) { msg.classList.remove('hidden'); setTimeout(() => msg.classList.add('hidden'), 3000); }
            // Recargar si cambió el idioma
            if (data.language !== currentLang) {
                setTimeout(() => window.location.reload(), 500);
            }
        }
    })
    .catch(() => {
        if (err) { err.textContent = t('error.connection'); err.classList.remove('hidden'); }
    });
}

// ============================================================
// PASSWORD
// ============================================================
function changePassword() {
    const btn = document.getElementById('save-password-btn');
    const msg = document.getElementById('password-save-msg');
    const err = document.getElementById('password-error-msg');

    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> ' + t('action.updating');
    if (window.lucide) lucide.createIcons();
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    const current = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirm = document.getElementById('confirm-password').value;

    if (!current || !newPass || !confirm) {
        if (err) { err.textContent = t('password.all_fields_required'); err.classList.remove('hidden'); }
        resetBtn(btn, '<i data-lucide="lock" class="w-4 h-4"></i> ' + t('action.change_password'));
        return;
    }
    if (newPass !== confirm) {
        if (err) { err.textContent = t('password.mismatch'); err.classList.remove('hidden'); }
        resetBtn(btn, '<i data-lucide="lock" class="w-4 h-4"></i> ' + t('action.change_password'));
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
            setTimeout(() => msg.classList.add('hidden'), 3000);
        }
    })
    .catch(() => {
        if (err) { err.textContent = t('error.connection'); err.classList.remove('hidden'); }
    })
    .finally(() => {
        resetBtn(btn, '<i data-lucide="lock" class="w-4 h-4"></i> ' + t('action.change_password'));
    });
}

function resetBtn(btn, html) {
    if (!btn) return;
    btn.disabled = false;
    btn.innerHTML = html;
    if (window.lucide) lucide.createIcons();
}

// ============================================================
// SESSIONS
// ============================================================
function loadUserSessions() {
    const container = document.getElementById('sessions-container');
    if (!container) return;
    container.innerHTML = '<div class="text-sm hint-text">' + t('sessions.loading') + '</div>';

    fetch('/api/profile/sessions')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.sessions || data.sessions.length === 0) {
            container.innerHTML = '<p class="text-sm hint-text">' + t('sessions.empty') + '</p>';
            return;
        }
        let html = '<table class="sessions-table"><thead><tr><th>#</th><th>IP</th><th>' + t('sessions.device') + '</th><th>' + t('sessions.last_activity') + '</th><th></th></tr></thead><tbody>';
        data.sessions.forEach((s, i) => {
            const ua = s.user_agent ? s.user_agent.substring(0, 60) : '-';
            html += `<tr>
                <td>${i + 1}</td>
                <td class="font-mono text-[10px]">${s.ip_address || '-'}</td>
                <td class="text-[11px]">${escapeHtml(ua)}</td>
                <td class="text-[11px]">${s.last_active || s.created_at || '-'}</td>
                <td><button onclick="terminateSession(${s.id})" class="text-[9px] uppercase tracking-widest font-bold hover:text-rose-500 transition-colors" style="color:var(--text-secondary)">${t('action.close')}</button></td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    })
    .catch(() => {
        container.innerHTML = '<p class="text-sm text-rose-600">' + t('error.sessions_load') + '</p>';
    });
}

function terminateSession(entryId) {
    var promise = typeof showConfirm === 'function' ? showConfirm(t('confirm.close_session')) : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
        fetch('/api/profile/sessions/' + entryId, { method: 'DELETE' })
        .then(function (r) { return r.json(); })
        .then(function (result) {
            if (result.success) loadUserSessions();
        })
        .catch(function () {});
    });
}

// ============================================================
// ACTIVITY
// ============================================================
function loadUserActivity() {
    const container = document.getElementById('activity-container');
    if (!container) return;
    container.innerHTML = '<div class="text-sm hint-text">' + t('activity.loading') + '</div>';

    fetch('/api/profile/activity')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.activity || data.activity.length === 0) {
            container.innerHTML = '<p class="text-sm hint-text">' + t('activity.empty') + '</p>';
            return;
        }
        let html = '<div class="activity-timeline">';
        data.activity.forEach(entry => {
            html += `<div class="activity-item">
                <div class="activity-dot"></div>
                <div class="activity-action">${escapeHtml(entry.action)}</div>
                <div class="activity-time">${entry.target ? escapeHtml(entry.target) + ' · ' : ''}${entry.timestamp || ''}</div>
            </div>`;
        });
        html += '</div>';
        container.innerHTML = html;
    })
    .catch(() => {
        container.innerHTML = '<p class="text-sm text-rose-600">' + t('error.activity_load') + '</p>';
    });
}

// ============================================================
// LEADS
// ============================================================
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
            const sym = lead.currency === 'USD' ? 'US$' : lead.currency === 'EUR' ? 'EUR' : '$';
            const seenCount = lead.seen_count || 0;
            const contactedCount = lead.contacted_count || 0;
            const contactNames = lead.contact_names || '';
            let trackingHtml;
            if (contactedCount > 0 && contactNames) {
                const names = contactNames.split(', ').map(n => escapeHtml(n)).join(', ');
                trackingHtml = `<span class="tracking-badge tracking-contacted" title="${names}">
                    <i data-lucide="check-circle" class="w-3 h-3 tracking-eye"></i>
                    ${t('leads.contact_names', { names })}
                </span>`;
            } else if (seenCount > 0) {
                trackingHtml = `<span class="tracking-badge" title="${seenCount} ${seenCount === 1 ? t('leads.seen_by_singular') : t('leads.seen_by_plural')} tu solicitud">
                    <i data-lucide="eye" class="w-3 h-3 tracking-eye"></i>
                    ${seenCount} ${seenCount === 1 ? t('leads.view_singular') : t('leads.view_plural')}
                </span>`;
            } else {
                trackingHtml = `<span class="tracking-empty">
                    <i data-lucide="hourglass" class="w-3 h-3"></i>
                    ${t('leads.under_review')}
                </span>`;
            }
            return `<tr style="border-bottom:1px solid var(--border)">
                <td class="px-4 py-3 text-[13px] font-semibold" style="color:var(--text-primary)">#${lead.id}</td>
                <td class="px-4 py-3 text-[13px]" style="color:var(--text-secondary)">${escapeHtml(lead.type || '-')}</td>
                <td class="px-4 py-3 text-[13px]" style="color:var(--text-secondary)">${escapeHtml(lead.zone || '-')}</td>
                <td class="px-4 py-3 text-[13px]" style="color:var(--text-secondary)">${escapeHtml(sym)} ${escapeHtml(lead.budget || '-')}</td>
                <td class="px-4 py-3 text-[13px]" style="color:var(--text-secondary)">${escapeHtml(lead.timestamp || '-')}</td>
                <td class="px-4 py-3">${trackingHtml}</td>
                <td class="px-4 py-3">
                    <a href="/mi-perfil/lead/${lead.id}/editar" class="inline-flex items-center gap-1 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest transition-all" style="background:var(--accent);color:white">
                        <i data-lucide="edit-3" class="w-3 h-3"></i>
                        Editar
                    </a>
                </td>
            </tr>`;
        }).join('');
        initTableStagger(tbody);
        if (window.lucide) lucide.createIcons();
    })
    .catch(() => {
        tbody.innerHTML = '<tr><td colspan="7" class="p-8 text-center text-rose-600">' + t('error.leads_load') + '</td></tr>';
    });
}

// ============================================================
// PROFESSIONAL FULL PROFILE
// ============================================================
function loadProfessionalFullProfile() {
    // Load basic data (license, status)
    fetch('/api/profile/professional')
    .then(r => r.json())
    .then(data => {
        if (data.success && data.professional) {
            const p = data.professional;
            const licenseEl = document.getElementById('pro-license');
            const statusEl = document.getElementById('pro-status');
            const licenseStatusEl = document.getElementById('pro-license-status');
            if (licenseEl) licenseEl.textContent = p.license || '-';
            if (statusEl) {
                const labels = { pending: t('status.pending'), approved: t('status.approved'), rejected: t('status.rejected') };
                statusEl.textContent = labels[p.status] || p.status;
                statusEl.className = 'text-sm font-medium ' + ({ pending: 'text-amber-600', approved: 'text-emerald-600', rejected: 'text-rose-600' }[p.status] || 'text-midnight/60');
            }
            if (licenseStatusEl) {
                if (p.license_verified) {
                    licenseStatusEl.textContent = t('license.verified');
                    licenseStatusEl.className = 'text-sm font-medium text-emerald-600';
                } else {
                    licenseStatusEl.textContent = t('license.not_verified');
                    licenseStatusEl.className = 'text-sm font-medium text-amber-600';
                }
            }
        }
    })
    .catch(() => {});

    // Load extended profile data
    fetch('/api/profile/professional/full')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.professional) return;
        const p = data.professional;

        // Photo
        if (p.photo_path) {
            const img = document.getElementById('pro-photo-preview');
            if (img) {
                img.src = '/static/' + p.photo_path;
                const ring = document.getElementById('pro-photo-ring');
                if (ring) {
                    img.addEventListener('load', function() { extractAvatarColors(img, ring); });
                }
            }
        }

        // Fields
        setVal('pro-bio', p.bio_pro);
        setVal('pro-experience', p.experience_years);
        setVal('pro-address', p.professional_address);
        setVal('pro-country', p.country || '');
        var proCountry = document.getElementById('pro-country');
        if (proCountry && p.country) {
            proCountry.value = p.country;
            proCountry.dispatchEvent(new Event('change'));
        }
        setVal('pro-province', p.province || '');
        setVal('pro-zone', p.zone || '');
        setVal('pro-fee-min', p.fee_range_min);
        setVal('pro-fee-max', p.fee_range_max);

        var social = {};
        if (p.social_links) {
            try { social = JSON.parse(p.social_links); } catch(e) {}
        }
        setVal('pro-linkedin', social.linkedin || '');
        setVal('pro-instagram', social.instagram || '');
        setVal('pro-website', social.website || '');

        // Services
        if (p.services_offered) {
            try {
                const services = JSON.parse(p.services_offered);
                document.querySelectorAll('#services-container input[type="checkbox"]').forEach(cb => {
                    cb.checked = services.includes(cb.value);
                });
            } catch(e) {}
        }

        // Availability
        if (p.availability) {
            try {
                const avail = JSON.parse(p.availability);
                document.querySelectorAll('#availability-container input[type="checkbox"]').forEach(cb => {
                    cb.checked = !!avail[cb.value];
                });
            } catch(e) {}
        }
    })
    .catch(() => {});
}

function setVal(id, val) {
    const el = document.getElementById(id);
    if (el && val !== undefined && val !== null) el.value = val;
}

var _coverageZones = [];
// Debe coincidir con models.MAX_COVERAGE_VALUES en el backend.
var COVERAGE_MAX_ZONES = 20;

function loadCoverage() {
    return fetch('/api/profile/professional/coverage')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.coverage) return;
        _coverageZones = Array.isArray(data.coverage.zones) ? data.coverage.zones.slice() : [];
        renderCoverageZones();

        const specialties = Array.isArray(data.coverage.specialties) ? data.coverage.specialties : [];
        document.querySelectorAll('.coverage-specialty-checkbox').forEach(cb => {
            cb.checked = specialties.includes(cb.value);
        });

        const hint = document.getElementById('coverage-fallback-hint');
        if (hint) hint.classList.toggle('hidden', data.coverage.configured !== false);
    })
    .catch(() => {});
}

function renderCoverageZones() {
    const list = document.getElementById('coverage-zones-list');
    if (list) {
        list.innerHTML = _coverageZones.map((zone, i) =>
            '<span class="coverage-zone-tag">' + escapeHtml(zone) +
            '<button type="button" onclick="removeCoverageZone(' + i + ')" aria-label="' + t('profile.coverage_remove') + '">' +
            '<i data-lucide="x" class="w-3 h-3" aria-hidden="true"></i></button></span>'
        ).join('');
        if (window.lucide) lucide.createIcons();
    }

    const count = document.getElementById('coverage-zones-count');
    if (count) count.textContent = _coverageZones.length + '/' + COVERAGE_MAX_ZONES;

    const addBtn = document.getElementById('coverage-zone-add-btn');
    const zoneInput = document.getElementById('coverage-zone-input');
    const atLimit = _coverageZones.length >= COVERAGE_MAX_ZONES;
    if (addBtn) addBtn.disabled = atLimit;
    if (zoneInput) zoneInput.disabled = atLimit;
}

function showCoverageZoneError(message) {
    const errEl = document.getElementById('coverage-zone-error');
    if (!errEl) return;
    if (!message) { errEl.classList.add('hidden'); return; }
    errEl.textContent = message;
    errEl.classList.remove('hidden');
}

function addCoverageZone() {
    const input = document.getElementById('coverage-zone-input');
    if (!input) return;
    showCoverageZoneError('');

    const value = input.value.trim();
    if (!value) return;

    if (_coverageZones.length >= COVERAGE_MAX_ZONES) {
        showCoverageZoneError(t('profile.coverage_zone_limit'));
        return;
    }
    if (_coverageZones.some(z => z.toLowerCase() === value.toLowerCase())) {
        showCoverageZoneError(t('profile.coverage_zone_duplicate'));
        input.value = '';
        return;
    }
    _coverageZones.push(value);
    input.value = '';
    renderCoverageZones();
}

function removeCoverageZone(index) {
    _coverageZones.splice(index, 1);
    showCoverageZoneError('');
    renderCoverageZones();
}

function saveCoverage() {
    const msg = document.getElementById('coverage-save-msg');
    const errEl = document.getElementById('coverage-save-error');
    const saveBtn = document.getElementById('coverage-save-btn');
    const saveBtnLabel = document.getElementById('coverage-save-btn-label');
    if (msg) msg.classList.add('hidden');
    if (errEl) errEl.classList.add('hidden');
    if (saveBtn) saveBtn.disabled = true;
    if (saveBtnLabel) saveBtnLabel.textContent = t('profile.saving');

    const specialties = Array.from(document.querySelectorAll('.coverage-specialty-checkbox:checked')).map(cb => cb.value);

    return fetch('/api/profile/professional/coverage', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zones: _coverageZones, specialties: specialties })
    })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
        if (ok && data.success) {
            if (msg) { msg.classList.remove('hidden'); setTimeout(() => msg.classList.add('hidden'), 3000); }
            const hint = document.getElementById('coverage-fallback-hint');
            if (hint) hint.classList.add('hidden');
        } else if (errEl) {
            errEl.textContent = data.error || t('error.process_request');
            errEl.classList.remove('hidden');
        }
    })
    .catch(() => {
        if (errEl) { errEl.textContent = t('error.process_request'); errEl.classList.remove('hidden'); }
    })
    .finally(() => {
        if (saveBtn) saveBtn.disabled = false;
        if (saveBtnLabel) saveBtnLabel.textContent = t('profile.coverage_save');
    });
}

function saveProfessionalFullProfile() {
    const btn = document.querySelector('#panel-profesional .btn-primary');
    const msg = document.getElementById('pro-full-save-msg');
    const err = document.getElementById('pro-full-error-msg');

    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> ' + t('action.saving');
    if (window.lucide) lucide.createIcons();
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    // Build social links JSON
    const social = {
        linkedin: document.getElementById('pro-linkedin')?.value || '',
        instagram: document.getElementById('pro-instagram')?.value || '',
        website: document.getElementById('pro-website')?.value || '',
    };

    // Build services array
    const services = [];
    document.querySelectorAll('#services-container input[type="checkbox"]:checked').forEach(cb => {
        services.push(cb.value);
    });

    // Build availability object
    const avail = {};
    document.querySelectorAll('#availability-container input[type="checkbox"]').forEach(cb => {
        avail[cb.value] = cb.checked;
    });

    const data = {
        bio_pro: document.getElementById('pro-bio')?.value || '',
        experience_years: parseInt(document.getElementById('pro-experience')?.value) || 0,
        professional_address: document.getElementById('pro-address')?.value || '',
        province: document.getElementById('pro-province')?.value || '',
        zone: document.getElementById('pro-zone')?.value || '',
        country: document.getElementById('pro-country')?.value || '',
        services_offered: JSON.stringify(services),
        availability: JSON.stringify(avail),
        social_links: JSON.stringify(social),
        fee_range_min: parseFloat(document.getElementById('pro-fee-min')?.value) || 0,
        fee_range_max: parseFloat(document.getElementById('pro-fee-max')?.value) || 0,
    };

    fetch('/api/profile/professional/full', {
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
            setTimeout(() => msg.classList.add('hidden'), 3000);
        }
    })
    .catch(() => {
        if (err) { err.textContent = t('error.connection'); err.classList.remove('hidden'); }
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> ' + t('action.save_pro_profile');
        if (window.lucide) lucide.createIcons();
    });
}

// ============================================================
// PROFESSIONAL PHOTO
// ============================================================
function uploadProfessionalPhoto(input) {
    const file = input.files[0];
    if (!file) return;

    const status = document.getElementById('pro-photo-status');
    if (status) { status.textContent = t('action.uploading'); status.className = 'text-[9px] mt-1 text-amber-500'; }

    const formData = new FormData();
    formData.append('photo', file);

    fetch('/api/profile/professional/photo', {
        method: 'POST',
        body: formData,
    })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
        if (ok && data.photo_url) {
            const img = document.getElementById('pro-photo-preview');
            if (img) img.src = data.photo_url;
            const ring = document.getElementById('pro-photo-ring');
            if (img && ring) {
                img.addEventListener('load', function() { extractAvatarColors(img, ring); });
            }
            if (status) { status.textContent = t('avatar.updated'); status.className = 'text-[9px] mt-1 text-emerald-600'; }
        } else {
            if (status) { status.textContent = data.error || t('error.avatar_upload'); status.className = 'text-[9px] mt-1 text-rose-500'; }
        }
        input.value = '';
    })
    .catch(() => {
        if (status) { status.textContent = t('error.connection'); status.className = 'text-[9px] mt-1 text-rose-500'; }
        input.value = '';
    });
}

function deleteProfessionalPhoto() {
    var promise = typeof showConfirm === 'function' ? showConfirm(t('confirm.delete_pro_photo')) : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
        var status = document.getElementById('pro-photo-status');
        if (status) { status.textContent = t('action.deleting'); status.className = 'text-[9px] mt-1 text-amber-500'; }
        fetch('/api/profile/professional/photo', { method: 'DELETE' })
        .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
        .then(function (res) {
            if (res.ok) {
                var img = document.getElementById('pro-photo-preview');
                if (img) img.src = '/static/img/default-avatar.svg';
                var ring = document.getElementById('pro-photo-ring');
                if (ring) ring.classList.remove('visible');
                if (status) { status.textContent = t('avatar.deleted'); status.className = 'text-[9px] mt-1 text-emerald-600'; }
            } else {
                if (status) { status.textContent = t('error.avatar_delete'); status.className = 'text-[9px] mt-1 text-rose-500'; }
            }
        })
        .catch(function () {
            if (status) { status.textContent = t('error.connection'); status.className = 'text-[9px] mt-1 text-rose-500'; }
        });
    });
}

// ============================================================
// SERVICES / AVAILABILITY CHIPS (auto-save placeholders)
// ============================================================
function updateServicesOffered() {
    // Datos se sincronizan al guardar el perfil completo
}

function updateAvailability() {
    // Datos se sincronizan al guardar el perfil completo
}

// ============================================================
// HELPERS
// ============================================================

// ============================================================
// AVATAR COLOR RING
// ============================================================
function extractAvatarColors(img, ring) {
    if (!img || !ring) return;
    if (!img.complete || !img.naturalWidth || img.naturalWidth < 10) {
        ring.classList.remove('visible');
        return;
    }
    if (img.src.includes('default-avatar.svg')) {
        ring.classList.remove('visible');
        return;
    }
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const size = 8;
    canvas.width = size;
    canvas.height = size;
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(img, 0, 0, size, size);
    const d = ctx.getImageData(0, 0, size, size).data;
    const colorMap = {};
    for (let i = 0; i < d.length; i += 4) {
        const r = Math.round(d[i] / 48) * 48;
        const g = Math.round(d[i + 1] / 48) * 48;
        const b = Math.round(d[i + 2] / 48) * 48;
        const key = r + ',' + g + ',' + b;
        colorMap[key] = (colorMap[key] || 0) + 1;
    }
    const sorted = Object.entries(colorMap).sort(function(a, b) { return b[1] - a[1]; }).slice(0, 5);
    var fallbacks = ['#3D2B1F', '#735A3A', '#A68A64', '#D4AF37', '#E8D5B7'];
    sorted.forEach(function(item, i) {
        ring.style.setProperty('--ac' + i, 'rgb(' + item[0] + ')');
    });
    for (var i = sorted.length; i < 5; i++) {
        ring.style.setProperty('--ac' + i, fallbacks[i]);
    }
    ring.classList.add('visible');
}

function setupAvatarRing(imgId, ringId) {
    var img = document.getElementById(imgId);
    var ring = document.getElementById(ringId);
    if (!img || !ring) return;
    if (img.complete) {
        extractAvatarColors(img, ring);
    } else {
        img.addEventListener('load', function() { extractAvatarColors(img, ring); });
    }
}

// Load data when professional tab is shown via visibility
const observer = new MutationObserver(() => {
    const proPanel = document.getElementById('panel-profesional');
    if (proPanel && !proPanel.hidden && !proPanel.dataset.loaded) {
        proPanel.dataset.loaded = 'true';
        loadProfessionalFullProfile();
    }
});
document.addEventListener('DOMContentLoaded', () => {
    const proPanel = document.getElementById('panel-profesional');
    if (proPanel) {
        observer.observe(proPanel, { attributes: true, attributeFilter: ['hidden'] });
    }
    setupAvatarRing('avatar-preview', 'avatar-ring');
    setupAvatarRing('pro-photo-preview', 'pro-photo-ring');
    initCountrySelector('pro-province', 'pro-country');

    // Auto-focus y navegación entre dígitos del modal
    const digits = document.querySelectorAll('.verify-digit');
    digits.forEach((input, i) => {
        input.addEventListener('input', function () {
            this.value = this.value.replace(/\D/g, '').slice(0, 1);
            if (this.value && i < digits.length - 1) {
                digits[i + 1].focus();
            }
            if (i === digits.length - 1 && this.value) {
                submitVerificationCode();
            }
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Backspace' && !this.value && i > 0) {
                digits[i - 1].focus();
            }
            if (e.key === 'Escape') {
                closePhoneVerifyModal();
            }
        });
        input.addEventListener('focus', function () { this.select(); });
    });

    // Cerrar modal al hacer clic fuera del panel
    const modal = document.getElementById('verify-phone-modal');
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === this) closePhoneVerifyModal();
        });
    }
});

// ================================================================
// VERIFICACIÓN SMS
// ================================================================

function openPhoneVerifyModal() {
    const modal = document.getElementById('verify-phone-modal');
    if (modal) {
        modal.classList.add('flex');
        openModalAnim(modal);
        document.querySelectorAll('.verify-digit').forEach(inp => inp.value = '');
        document.getElementById('verify-error').classList.add('hidden');
        document.getElementById('verify-success').classList.add('hidden');
        document.querySelector('.verify-digit').focus();
        toggleWhatsappHint();
        autoSendVerificationCode();
    }
}

async function autoSendVerificationCode() {
    const errorEl = document.getElementById('verify-error');
    const submitBtn = document.getElementById('verify-submit-btn');
    errorEl.classList.add('hidden');
    submitBtn.disabled = true;

    const select = document.getElementById('preferred-channel-select');
    const preferredChannel = select ? select.value : 'auto';

    try {
        const res = await fetch('/api/phone/send-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preferred_channel: preferredChannel })
        });
        const data = await res.json();
        if (!res.ok) {
            errorEl.textContent = data.error || t('error.code_send');
            errorEl.classList.remove('hidden');
        }
    } catch {
        errorEl.textContent = t('error.connection_retry');
        errorEl.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
    }
}

function closePhoneVerifyModal() {
    const modal = document.getElementById('verify-phone-modal');
    if (modal) {
        closeModalAnim(modal);
    }
}

function getVerificationCode() {
    const digits = document.querySelectorAll('.verify-digit');
    return Array.from(digits).map(inp => inp.value || '').join('');
}

async function submitVerificationCode() {
    const code = getVerificationCode();
    const errorEl = document.getElementById('verify-error');
    const successEl = document.getElementById('verify-success');
    const submitBtn = document.getElementById('verify-submit-btn');

    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');

    if (code.length !== 6) {
        errorEl.textContent = t('verification.enter_full_code');
        errorEl.classList.remove('hidden');
        return;
    }

    const originalContent = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin inline"></i> ' + t('action.verifying');
    submitBtn.disabled = true;
    if (window.lucide) lucide.createIcons();

    try {
        const res = await fetch('/api/phone/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await res.json();

        if (res.ok) {
            successEl.classList.remove('hidden');
            if (typeof showToast === 'function') showToast(t('verification.success'), 'success');
            setTimeout(() => {
                closePhoneVerifyModal();
                const area = document.getElementById('phone-verification-area');
                if (area) {
                    const channel = data.channel || 'sms';
                    const icon = channel === 'whatsapp' ? 'message-circle' : 'smartphone';
                    const label = channel === 'whatsapp' ? 'WhatsApp' : 'SMS';
                    area.innerHTML = '<span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest bg-emerald-50 text-emerald-700 inline-flex items-center gap-1">'
                        + '<i data-lucide="' + icon + '" class="w-3 h-3"></i> Verificado por ' + label + '</span>';
                    if (window.lucide) lucide.createIcons();
                }
            }, 1500);
        } else if (res.status === 410) {
            errorEl.textContent = data.error || t('verification.expired');
            errorEl.classList.remove('hidden');
        } else {
            errorEl.textContent = data.error || t('verification.incorrect');
            errorEl.classList.remove('hidden');
        }
    } catch (err) {
        errorEl.textContent = t('error.connection_retry');
        errorEl.classList.remove('hidden');
    } finally {
        submitBtn.innerHTML = originalContent;
        submitBtn.disabled = false;
        if (window.lucide) lucide.createIcons();
    }
}

async function resendVerificationCode() {
    const btn = document.getElementById('resend-code-btn');
    const cooldown = document.getElementById('resend-cooldown');
    const errorEl = document.getElementById('verify-error');

    errorEl.classList.add('hidden');
    btn.disabled = true;
    btn.classList.add('opacity-50');

    const select = document.getElementById('preferred-channel-select');
    const preferredChannel = select ? select.value : 'auto';

    try {
        const res = await fetch('/api/phone/send-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preferred_channel: preferredChannel })
        });
        const data = await res.json();

        if (res.ok) {
            if (typeof showToast === 'function') showToast(t('verification.resent'), 'info');
            // Cooldown 60s
            let remaining = 60;
            cooldown.classList.remove('hidden');
            cooldown.textContent = `(${remaining}s)`;
            const interval = setInterval(() => {
                remaining--;
                cooldown.textContent = `(${remaining}s)`;
                if (remaining <= 0) {
                    clearInterval(interval);
                    cooldown.classList.add('hidden');
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                }
            }, 1000);
        } else {
            errorEl.textContent = data.error || t('error.code_send');
            errorEl.classList.remove('hidden');
            btn.disabled = false;
            btn.classList.remove('opacity-50');
        }
    } catch (err) {
        errorEl.textContent = t('error.connection');
        errorEl.classList.remove('hidden');
        btn.disabled = false;
        btn.classList.remove('opacity-50');
    }
}

// ---- Contactar Administración ----
async function contactAdmin() {
    const subject = document.getElementById('contact-admin-subject').value.trim();
    const message = document.getElementById('contact-admin-message').value.trim();
    const msgEl   = document.getElementById('contact-admin-msg');
    const errEl   = document.getElementById('contact-admin-error');

    msgEl.classList.add('hidden');
    errEl.classList.add('hidden');

    if (!subject || !message) {
        errEl.textContent = t('error.required_fields');
        errEl.classList.remove('hidden');
        return;
    }

    try {
        const res = await fetch('/api/profile/contact-admin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject: subject, message: message })
        });
        const data = await res.json();

        if (res.ok) {
            document.getElementById('contact-admin-subject').value = '';
            document.getElementById('contact-admin-message').value = '';
            msgEl.textContent = data.message || t('profile.contact_admin_sent');
            msgEl.classList.remove('hidden');
            if (typeof showToast === 'function') showToast(data.message);
        } else {
            errEl.textContent = data.error || t('error.process_request');
            errEl.classList.remove('hidden');
        }
    } catch (err) {
        errEl.textContent = t('error.connection');
        errEl.classList.remove('hidden');
    }
}

// ============================================================
// PROFILE SETTINGS — ArchEstate
// ============================================================

function initSettingsPage() {
    loadUserLeads();
    loadUserSettings();
    if (document.getElementById('panel-profesional')) {
        loadProfessionalFullProfile();
    }
    initPhoneFromServer();
    validateProfileEmail();
    validateProfilePhone();
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
    if (panel) panel.hidden = false;

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
    if (tabName === 'profesional') loadProfessionalFullProfile();

    if (window.lucide) lucide.createIcons();
}

// Keyboard nav for tabs
document.addEventListener('keydown', function(e) {
    const tabs = document.querySelectorAll('[role="tab"]');
    if (!tabs.length) return;
    const current = document.activeElement;
    if (!current || !current.getAttribute('role') === 'tab') return;

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
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Guardando...';
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
        }
    })
    .catch(() => {
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Cambios';
        if (window.lucide) lucide.createIcons();
    });
}

// ============================================================
// AVATAR
// ============================================================
function uploadAvatar(input) {
    const file = input.files[0];
    if (!file) return;

    const status = document.getElementById('avatar-status');
    if (status) { status.textContent = 'Subiendo...'; status.className = 'text-[9px] mt-1 text-amber-500'; }

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
            if (status) { status.textContent = 'Foto actualizada'; status.className = 'text-[9px] mt-1 text-green-600'; }
        } else {
            if (status) { status.textContent = data.error || 'Error al subir foto'; status.className = 'text-[9px] mt-1 text-rose-500'; }
        }
        input.value = '';
    })
    .catch(() => {
        if (status) { status.textContent = 'Error de conexion'; status.className = 'text-[9px] mt-1 text-rose-500'; }
        input.value = '';
    });
}

function deleteAvatar() {
    if (!confirm('¿Eliminar foto de perfil?')) return;

    const status = document.getElementById('avatar-status');
    if (status) { status.textContent = 'Eliminando...'; status.className = 'text-[9px] mt-1 text-amber-500'; }

    fetch('/api/profile/user/avatar', { method: 'DELETE' })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok }) => {
        if (ok) {
            const img = document.getElementById('avatar-preview');
            if (img) img.src = '/static/img/default-avatar.svg';
            if (status) { status.textContent = 'Foto eliminada'; status.className = 'text-[9px] mt-1 text-green-600'; }
        } else {
            if (status) { status.textContent = 'Error al eliminar foto'; status.className = 'text-[9px] mt-1 text-rose-500'; }
        }
    })
    .catch(() => {
        if (status) { status.textContent = 'Error de conexion'; status.className = 'text-[9px] mt-1 text-rose-500'; }
    });
}

// ============================================================
// PHONE FORMAT
// ============================================================
function formatProfilePhone(phone, countryCode) {
    const digits = phone.replace(/\D/g, '');
    const provinceSelect = document.getElementById('profile-province');
    const prefix = provinceSelect && !provinceSelect.classList.contains('hidden') ? provinceSelect.value : '';
    let fullNumber = countryCode + ' ';
    if (prefix && !digits.startsWith(prefix)) {
        fullNumber += prefix + ' ' + digits;
    } else {
        fullNumber += digits;
    }
    return fullNumber.trim();
}

function initPhoneFromServer() {
    const phoneInput = document.getElementById('profile-phone');
    const countrySelect = document.getElementById('profile-country-code');
    const provinceSelect = document.getElementById('profile-province');
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
            if (code === '+54' && provinceSelect) {
                provinceSelect.classList.remove('hidden');
                for (const opt of provinceSelect.options) {
                    if (withoutCode.startsWith(opt.value)) { opt.selected = true; break; }
                }
                phoneInput.value = withoutCode;
            } else {
                phoneInput.value = withoutCode;
            }
        }
    }
    updateProfilePhoneFormat();
}

function updateProfilePhoneFormat() {
    const phoneInput = document.getElementById('profile-phone');
    const countryCode = document.getElementById('profile-country-code').value;
    const provinceSelect = document.getElementById('profile-province');
    if (countryCode === '+54') {
        provinceSelect.classList.remove('hidden');
    } else {
        provinceSelect.classList.add('hidden');
    }
    validateProfilePhone();
}

function applyProvincePrefix() {
    const phoneInput = document.getElementById('profile-phone');
    const provinceSelect = document.getElementById('profile-province');
    const prefix = provinceSelect.value;
    const raw = phoneInput.value.trim().replace(/\D/g, '');
    const prefixes = ['11','221','223','341','351','261','264','266','280','291','299','379','381','383','387','388','358','342','343','345','362','364','370','375','376','377','378','385'];
    const hasPrefix = prefixes.some(p => raw.startsWith(p));
    if (!hasPrefix && raw.length > 0) {
        phoneInput.value = prefix + ' ' + raw;
    } else if (raw.length > 0) {
        let cleaned = raw;
        for (const p of prefixes) {
            if (cleaned.startsWith(p)) { cleaned = cleaned.substring(p.length).replace(/^\s+/, ''); break; }
        }
        phoneInput.value = prefix + ' ' + cleaned;
    }
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

function validateProfilePhone() {
    const input = document.getElementById('profile-phone');
    const hint = document.getElementById('profile-phone-hint');
    const valid = document.getElementById('profile-phone-valid');
    const invalid = document.getElementById('profile-phone-invalid');
    const raw = input.value.trim();
    if (!raw) {
        if (hint) hint.classList.remove('hidden');
        if (valid) valid.classList.add('hidden');
        if (invalid) invalid.classList.add('hidden');
        return;
    }
    const digits = raw.replace(/\D/g, '');
    if (digits.length >= 8 && digits.length <= 15) {
        if (hint) hint.classList.add('hidden');
        if (valid) valid.classList.remove('hidden');
        if (invalid) invalid.classList.add('hidden');
    } else {
        if (hint) hint.classList.add('hidden');
        if (valid) valid.classList.add('hidden');
        if (invalid) invalid.classList.remove('hidden');
    }
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
        html.classList.add('dark-mode');
    } else {
        html.classList.remove('dark-mode');
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
    // Update navbar theme toggle icons
    const sunIcon = document.querySelector('.theme-sun');
    const moonIcon = document.querySelector('.theme-moon');
    if (sunIcon) sunIcon.style.display = theme === 'dark' ? 'none' : 'block';
    if (moonIcon) moonIcon.style.display = theme === 'dark' ? 'block' : 'none';
}

function saveSettings() {
    const langEl = document.getElementById('settings-language');
    const themeBtn = document.querySelector('.theme-option.active');
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
        }
    })
    .catch(() => {
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
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
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Actualizando...';
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    const current = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirm = document.getElementById('confirm-password').value;

    if (!current || !newPass || !confirm) {
        if (err) { err.textContent = 'Todos los campos son requeridos'; err.classList.remove('hidden'); }
        resetBtn(btn, '<i data-lucide="lock" class="w-4 h-4"></i> Cambiar Contrasena');
        return;
    }
    if (newPass !== confirm) {
        if (err) { err.textContent = 'Las contrasenas no coinciden'; err.classList.remove('hidden'); }
        resetBtn(btn, '<i data-lucide="lock" class="w-4 h-4"></i> Cambiar Contrasena');
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
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
    })
    .finally(() => {
        resetBtn(btn, '<i data-lucide="lock" class="w-4 h-4"></i> Cambiar Contrasena');
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
    container.innerHTML = '<div class="text-sm hint-text">Cargando sesiones...</div>';

    fetch('/api/profile/sessions')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.sessions || data.sessions.length === 0) {
            container.innerHTML = '<p class="text-sm hint-text">No hay sesiones registradas.</p>';
            return;
        }
        let html = '<table class="sessions-table"><thead><tr><th>#</th><th>IP</th><th>Dispositivo</th><th>Ultima actividad</th><th></th></tr></thead><tbody>';
        data.sessions.forEach((s, i) => {
            const ua = s.user_agent ? s.user_agent.substring(0, 60) : '-';
            html += `<tr>
                <td>${i + 1}</td>
                <td class="font-mono text-[10px]">${s.ip_address || '-'}</td>
                <td class="text-[11px]">${escapeHtml(ua)}</td>
                <td class="text-[11px]">${s.last_active || s.created_at || '-'}</td>
                <td><button onclick="terminateSession(${s.id})" class="text-[9px] uppercase tracking-widest font-bold hover:text-rose-500 transition-colors" style="color:var(--text-secondary)">Cerrar</button></td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    })
    .catch(() => {
        container.innerHTML = '<p class="text-sm" style="color:#e11d48">Error al cargar sesiones</p>';
    });
}

function terminateSession(entryId) {
    if (!confirm('¿Cerrar esta sesion?')) return;
    fetch(`/api/profile/sessions/${entryId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(result => {
        if (result.status === 'success') loadUserSessions();
    })
    .catch(() => {});
}

// ============================================================
// ACTIVITY
// ============================================================
function loadUserActivity() {
    const container = document.getElementById('activity-container');
    if (!container) return;
    container.innerHTML = '<div class="text-sm hint-text">Cargando actividad...</div>';

    fetch('/api/profile/activity')
    .then(r => r.json())
    .then(data => {
        if (!data.success || !data.activity || data.activity.length === 0) {
            container.innerHTML = '<p class="text-sm hint-text">No hay actividad registrada aun.</p>';
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
        container.innerHTML = '<p class="text-sm" style="color:#e11d48">Error al cargar actividad</p>';
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
            return `<tr style="border-bottom:1px solid var(--border)">
                <td class="p-4 text-sm font-semibold" style="color:var(--text-primary)">#${lead.id}</td>
                <td class="p-4 text-sm" style="color:var(--text-secondary)">${lead.type || '-'}</td>
                <td class="p-4 text-sm" style="color:var(--text-secondary)">${lead.zone || '-'}</td>
                <td class="p-4 text-sm" style="color:var(--text-secondary)">${sym} ${lead.budget || '-'}</td>
                <td class="p-4 text-sm" style="color:var(--text-secondary)">${lead.timestamp || '-'}</td>
                <td class="p-4">
                    <a href="/mi-perfil/lead/${lead.id}/editar" class="inline-flex items-center gap-1 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest transition-all" style="background:var(--accent);color:white">
                        <i data-lucide="edit-3" class="w-3 h-3"></i>
                        Editar
                    </a>
                </td>
            </tr>`;
        }).join('');
        if (window.lucide) lucide.createIcons();
    })
    .catch(() => {
        tbody.innerHTML = '<tr><td colspan="6" class="p-8 text-center" style="color:#e11d48">Error al cargar solicitudes</td></tr>';
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
                const labels = { pending: 'Pendiente', approved: 'Aprobado', rejected: 'Rechazado' };
                statusEl.textContent = labels[p.status] || p.status;
                const colors = { pending: '#d97706', approved: '#059669', rejected: '#e11d48' };
                statusEl.style.color = colors[p.status] || 'var(--text-secondary)';
            }
            if (licenseStatusEl) {
                if (p.license_verified) {
                    licenseStatusEl.textContent = '✓ Verificada';
                    licenseStatusEl.style.color = '#059669';
                } else {
                    licenseStatusEl.textContent = 'No verificada';
                    licenseStatusEl.style.color = '#d97706';
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
            if (img) img.src = '/static/' + p.photo_path;
        }

        // Fields
        setVal('pro-bio', p.bio_pro);
        setVal('pro-experience', p.experience_years);
        setVal('pro-address', p.professional_address);
        setVal('pro-fee-min', p.fee_range_min);
        setVal('pro-fee-max', p.fee_range_max);
        setVal('pro-linkedin', p.social_links ? JSON.parse(p.social_links).linkedin || '' : '');
        setVal('pro-instagram', p.social_links ? JSON.parse(p.social_links).instagram || '' : '');
        setVal('pro-website', p.social_links ? JSON.parse(p.social_links).website || '' : '');

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

function saveProfessionalFullProfile() {
    const btn = document.querySelector('#panel-profesional .btn-primary');
    const msg = document.getElementById('pro-full-save-msg');
    const err = document.getElementById('pro-full-error-msg');

    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Guardando...';
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
        if (err) { err.textContent = 'Error de conexion'; err.classList.remove('hidden'); }
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Perfil Profesional';
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
    if (status) { status.textContent = 'Subiendo...'; status.className = 'text-[9px] mt-1 text-amber-500'; }

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
            if (status) { status.textContent = 'Foto actualizada'; status.className = 'text-[9px] mt-1 text-green-600'; }
        } else {
            if (status) { status.textContent = data.error || 'Error al subir foto'; status.className = 'text-[9px] mt-1 text-rose-500'; }
        }
        input.value = '';
    })
    .catch(() => {
        if (status) { status.textContent = 'Error de conexion'; status.className = 'text-[9px] mt-1 text-rose-500'; }
        input.value = '';
    });
}

function deleteProfessionalPhoto() {
    if (!confirm('¿Eliminar foto profesional?')) return;

    const status = document.getElementById('pro-photo-status');
    if (status) { status.textContent = 'Eliminando...'; status.className = 'text-[9px] mt-1 text-amber-500'; }

    fetch('/api/profile/professional/photo', { method: 'DELETE' })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok }) => {
        if (ok) {
            const img = document.getElementById('pro-photo-preview');
            if (img) img.src = '/static/img/default-avatar.svg';
            if (status) { status.textContent = 'Foto eliminada'; status.className = 'text-[9px] mt-1 text-green-600'; }
        } else {
            if (status) { status.textContent = 'Error al eliminar foto'; status.className = 'text-[9px] mt-1 text-rose-500'; }
        }
    })
    .catch(() => {
        if (status) { status.textContent = 'Error de conexion'; status.className = 'text-[9px] mt-1 text-rose-500'; }
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
function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
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
});

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

    const data = {
        email: document.getElementById('profile-email').value,
        phone: document.getElementById('profile-phone').value,
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

        const data = {
            zone: document.getElementById('edit-zone').value,
            budget: document.getElementById('edit-budget').value,
            currency: document.getElementById('edit-currency').value,
            phone: document.getElementById('edit-phone').value,
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
            amenities: document.getElementById('edit-amenities').value,
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

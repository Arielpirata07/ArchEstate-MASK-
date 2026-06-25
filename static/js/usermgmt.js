// ---- Estado ----
let targetUserId   = null;
let targetUsername = null;
let disableTargetId   = null;
let disableTargetName = null;
let enableTargetId    = null;
let enableTargetName  = null;
let searchTimeout  = null;

// ---- Carga y render de usuarios ----

async function loadUsers() {
    const search = document.getElementById('userSearchInput').value.trim();
    const role   = document.getElementById('roleFilter').value;

    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (role)   params.set('role', role);

    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="p-8 text-center text-midnight/40">
                <div class="flex justify-center items-center gap-2">
                    <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gold"></div>
                    Cargando...
                </div>
            </td>
        </tr>`;

    try {
        const res  = await fetch(`/api/admin/users?${params}`);
        const data = await res.json();

        if (data.success) {
            renderUsers(data.users);
            document.getElementById('usersCount').textContent = data.total;
        } else {
            showTableError(data.error || 'Error al cargar usuarios.');
        }
    } catch (err) {
        showTableError('Error de conexión.');
    }
}

const ROLE_LABELS = {
    admin:        { text: 'Admin',        cls: 'bg-midnight text-white' },
    professional: { text: 'Profesional',  cls: 'bg-gold/20 text-gold' },
    client:       { text: 'Cliente',      cls: 'bg-paper-dark text-midnight/60' },
};

function renderUsers(users) {
    const tbody = document.getElementById('usersTableBody');

    if (!users.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="p-8 text-center text-midnight/40">
                    <i data-lucide="search" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
                    <p>No se encontraron usuarios.</p>
                </td>
            </tr>`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = users.map(u => {
        const badge = ROLE_LABELS[u.role] || { text: u.role, cls: 'bg-paper-dark text-midnight' };
        const phoneVerified = u.phone_verified === 1;
        const phone = u.phone
            ? (phoneVerified
                ? `<span class="inline-flex items-center gap-1"><i data-lucide="smartphone" class="w-3 h-3 text-emerald-600"></i> ${escapeHtml(u.phone)}</span>`
                : `<span class="inline-flex items-center gap-1"><i data-lucide="phone-off" class="w-3 h-3 text-midnight/30"></i> ${escapeHtml(u.phone)}</span>`)
            : '<span class="text-midnight/25 italic">Sin teléfono</span>';

        const isAdmin = u.role === 'admin';
        const resetBtn = isAdmin
            ? `<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest">Protegida</span>`
            : `<button
                onclick="openResetModal(${u.id}, '${escapeHtml(u.username)}')"
                class="inline-flex items-center gap-2 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                    <i data-lucide="key-round" class="w-3 h-3"></i> Reset Pass
               </button>`;

        const isActive = u.is_active === 1;
        const statusBadge = isActive
            ? '<span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest bg-emerald-50 text-emerald-700 inline-flex items-center gap-1"><i data-lucide="check" class="w-3 h-3"></i> Activo</span>'
            : '<span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest bg-rose-50 text-rose-700 inline-flex items-center gap-1"><i data-lucide="x" class="w-3 h-3"></i> Baja</span>';

        const toggleBtn = isAdmin
            ? '<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest">Protegida</span>'
            : (isActive
                ? `<button onclick="openDisableModal(${u.id}, '${escapeHtml(u.username)}')"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-rose-50 text-rose-600 rounded text-[9px] font-bold uppercase tracking-widest hover:bg-rose-600 hover:text-white transition-all">
                    <i data-lucide="user-x" class="w-3 h-3"></i> Bajar
                   </button>`
                : `<button onclick="openEnableModal(${u.id}, '${escapeHtml(u.username)}')"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-50 text-emerald-600 rounded text-[9px] font-bold uppercase tracking-widest hover:bg-emerald-600 hover:text-white transition-all">
                    <i data-lucide="user-check" class="w-3 h-3"></i> Activar
                   </button>`);

        return `
            <tr class="border-b border-midnight/[0.03] hover:bg-paper transition-colors">
                <td class="px-4 py-3 font-mono text-[11px] text-midnight/40">#${u.id}</td>
                <td class="px-4 py-3 text-[13px]">
                    <div class="font-medium text-midnight">${escapeHtml(u.username)}</div>
                </td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${escapeHtml(u.email) || '<span class="text-midnight/25 italic">Sin email</span>'}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${phone}</td>
                <td class="px-4 py-3">
                    <span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest ${badge.cls}">
                        ${badge.text}
                    </span>
                </td>
                <td class="px-4 py-3">
                    <div class="flex flex-col gap-1.5">
                        ${statusBadge}
                        ${toggleBtn}
                    </div>
                </td>
                <td class="px-4 py-3 text-right">${resetBtn}</td>
            </tr>`;
    }).join('');

    initTableStagger(tbody);
    if (window.lucide) lucide.createIcons();
}

function showTableError(msg) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="p-8 text-center text-rose-500">
                <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2"></i>
                <p class="text-[13px]">${msg}</p>
            </td>
        </tr>`;
    if (window.lucide) lucide.createIcons();
}

// ---- Modal ----

function openResetModal(userId, username) {
    targetUserId   = userId;
    targetUsername = username;

    document.getElementById('modal-username').textContent = username;
    document.getElementById('newPasswordInput').value     = '';
    document.getElementById('confirmPasswordInput').value = '';
    document.getElementById('passwordMatchError').classList.add('hidden');
    document.getElementById('strengthBar').classList.add('hidden');

    document.getElementById('resetModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    setTimeout(() => document.getElementById('newPasswordInput').focus(), 100);
}

function closeModal() {
    document.getElementById('resetModal').classList.add('hidden');
    document.body.style.overflow = '';
    targetUserId   = null;
    targetUsername = null;
}

// Cerrar con Escape + focus trap con Tab
document.addEventListener('keydown', function(e) {
    var modal = document.getElementById('resetModal');
    if (modal.classList.contains('hidden')) return;

    if (e.key === 'Escape') {
        closeModal();
        return;
    }

    if (e.key === 'Tab') {
        var focusable = modal.querySelectorAll('button, [href], input:not([type="hidden"]), select, textarea, [tabindex]:not([tabindex="-1"])');
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey) {
            if (document.activeElement === first) { e.preventDefault(); last.focus(); }
        } else {
            if (document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
    }
});

// ---- Validación en tiempo real ----

function validatePasswordModal() {
    const pwd     = document.getElementById('newPasswordInput').value;
    const confirm = document.getElementById('confirmPasswordInput').value;
    const errEl   = document.getElementById('passwordMatchError');
    const bar     = document.getElementById('strengthBar');

    // Mostrar barra de fortaleza
    if (pwd.length > 0) {
        bar.classList.remove('hidden');
        updateStrengthBar(pwd);
    } else {
        bar.classList.add('hidden');
    }

    // Validar coincidencia solo si el campo de confirmación tiene algo
    if (confirm.length > 0) {
        if (pwd !== confirm) {
            errEl.textContent = 'Las contraseñas no coinciden.';
            errEl.classList.remove('hidden');
        } else {
            errEl.classList.add('hidden');
        }
    } else {
        errEl.classList.add('hidden');
    }
}

function updateStrengthBar(pwd) {
    let strength = 0;
    if (pwd.length >= 6)  strength++;
    if (pwd.length >= 10) strength++;
    if (/[A-Z]/.test(pwd) && /[0-9]/.test(pwd)) strength++;
    if (/[^A-Za-z0-9]/.test(pwd)) strength++;

    const colors  = ['bg-rose-400', 'bg-amber-400', 'bg-yellow-400', 'bg-emerald-500'];
    const labels  = ['Muy débil', 'Débil', 'Aceptable', 'Fuerte'];
    const filled  = colors[strength - 1] || 'bg-midnight/10';

    for (let i = 1; i <= 4; i++) {
        const bar = document.getElementById(`s${i}`);
        bar.className = `h-1 flex-1 rounded transition-colors ${i <= strength ? filled : 'bg-midnight/10'}`;
    }
    document.getElementById('strengthLabel').textContent = strength > 0 ? labels[strength - 1] : '';
}

// ---- Confirmación del reset ----

async function confirmReset() {
    const pwd     = document.getElementById('newPasswordInput').value.trim();
    const confirm = document.getElementById('confirmPasswordInput').value.trim();
    const errEl   = document.getElementById('passwordMatchError');
    const btn     = document.getElementById('confirmResetBtn');

    errEl.classList.add('hidden');

    if (!pwd || pwd.length < 6) {
        errEl.textContent = 'La contraseña debe tener al menos 6 caracteres.';
        errEl.classList.remove('hidden');
        return;
    }

    if (pwd !== confirm) {
        errEl.textContent = 'Las contraseñas no coinciden.';
        errEl.classList.remove('hidden');
        return;
    }

    // Estado de carga
    const original = btn.innerHTML;
    btn.innerHTML  = '<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div> Procesando...';
    btn.disabled   = true;

    try {
        const res  = await fetch(`/api/admin/user/${targetUserId}/reset-password`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ password: pwd })
        });
        const data = await res.json();

        if (res.ok) {
            closeModal();
            if (typeof showToast === 'function') showToast(data.message);
        } else {
            errEl.textContent = data.error || 'Error al resetear la contraseña.';
            errEl.classList.remove('hidden');
            btn.innerHTML  = original;
            btn.disabled   = false;
        }
    } catch (err) {
        errEl.textContent = 'Error de conexión. Intentá de nuevo.';
        errEl.classList.remove('hidden');
        btn.innerHTML  = original;
        btn.disabled   = false;
    }
}

// ---- Init ----

document.addEventListener('DOMContentLoaded', () => {
    loadUsers();

    // Búsqueda en tiempo real
    document.getElementById('userSearchInput').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(loadUsers, 400);
    });

    // Filtro por rol
    document.getElementById('roleFilter').addEventListener('change', loadUsers);
});

// ---- Disable Modal ----

function openDisableModal(userId, username) {
    disableTargetId   = userId;
    disableTargetName = username;
    document.getElementById('disable-username').textContent = username;
    document.getElementById('disableReason').value = '';
    document.getElementById('disableModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    setTimeout(() => document.getElementById('disableReason').focus(), 100);
}

function closeDisableModal() {
    document.getElementById('disableModal').classList.add('hidden');
    document.body.style.overflow = '';
    disableTargetId   = null;
    disableTargetName = null;
}

async function confirmDisable() {
    if (!disableTargetId) return;
    const btn = document.getElementById('confirmDisableBtn');
    const original = btn.innerHTML;
    btn.innerHTML = '<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div> Procesando...';
    btn.disabled = true;

    try {
        const res  = await fetch(`/api/admin/user/${disableTargetId}/set-active`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ is_active: false, ...(document.getElementById('disableReason').value.trim() && { reason: document.getElementById('disableReason').value.trim() }) })
        });
        const data = await res.json();

        if (res.ok) {
            closeDisableModal();
            if (typeof showToast === 'function') showToast(data.message);
            loadUsers();
        } else {
            if (typeof showToast === 'function') showToast(data.error || 'Error al dar de baja.', 'error');
        }
    } catch (err) {
        if (typeof showToast === 'function') showToast('Error de conexión.', 'error');
    } finally {
        btn.innerHTML = original;
        btn.disabled = false;
    }
}

// ---- Enable Modal ----

function openEnableModal(userId, username) {
    enableTargetId   = userId;
    enableTargetName = username;
    document.getElementById('enable-username').textContent = username;
    document.getElementById('enableModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeEnableModal() {
    document.getElementById('enableModal').classList.add('hidden');
    document.body.style.overflow = '';
    enableTargetId   = null;
    enableTargetName = null;
}

async function confirmEnable() {
    if (!enableTargetId) return;
    const btn = document.getElementById('confirmEnableBtn');
    const original = btn.innerHTML;
    btn.innerHTML = '<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div> Procesando...';
    btn.disabled = true;

    try {
        const res  = await fetch(`/api/admin/user/${enableTargetId}/set-active`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ is_active: true })
        });
        const data = await res.json();

        if (res.ok) {
            closeEnableModal();
            if (typeof showToast === 'function') showToast(data.message);
            loadUsers();
        } else {
            if (typeof showToast === 'function') showToast(data.error || 'Error al reactivar.', 'error');
        }
    } catch (err) {
        if (typeof showToast === 'function') showToast('Error de conexión.', 'error');
    } finally {
        btn.innerHTML = original;
        btn.disabled = false;
    }
}

// Cerrar modales con Escape
document.addEventListener('keydown', function(e) {
    if (e.key !== 'Escape') return;
    if (!document.getElementById('disableModal').classList.contains('hidden')) {
        closeDisableModal();
    } else if (!document.getElementById('enableModal').classList.contains('hidden')) {
        closeEnableModal();
    }
});

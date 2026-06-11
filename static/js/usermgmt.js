// ---- Estado ----
let targetUserId   = null;
let targetUsername = null;
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
            <td colspan="6" class="p-8 text-center text-midnight/40">
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
                <td colspan="6" class="p-8 text-center text-midnight/40">
                    <i data-lucide="search" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
                    <p>No se encontraron usuarios.</p>
                </td>
            </tr>`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = users.map(u => {
        const badge = ROLE_LABELS[u.role] || { text: u.role, cls: 'bg-paper-dark text-midnight' };
        const phone = u.phone
            ? escapeHtml(u.phone)
            : '<span class="text-midnight/25 italic">Sin teléfono</span>';

        // El admin no puede resetear su propia cuenta desde aquí
        // ni resetear a otros admins (protegido también en el backend)
        const isAdmin = u.role === 'admin';
        const resetBtn = isAdmin
            ? `<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest">Protegida</span>`
            : `<button
                onclick="openResetModal(${u.id}, '${escapeHtml(u.username)}')"
                class="inline-flex items-center gap-2 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                    <i data-lucide="key-round" class="w-3 h-3"></i> Reset Pass
               </button>`;

        return `
            <tr class="border-b border-midnight/5 hover:bg-paper transition-colors">
                <td class="p-4 font-mono text-xs text-midnight/40">#${u.id}</td>
                <td class="p-4">
                    <div class="font-medium text-midnight">${escapeHtml(u.username)}</div>
                </td>
                <td class="p-4 text-sm text-midnight/60">${escapeHtml(u.email) || '<span class="text-midnight/25 italic">Sin email</span>'}</td>
                <td class="p-4 text-sm text-midnight/60">${phone}</td>
                <td class="p-4">
                    <span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest ${badge.cls}">
                        ${badge.text}
                    </span>
                </td>
                <td class="p-4 text-right">${resetBtn}</td>
            </tr>`;
    }).join('');

    if (window.lucide) lucide.createIcons();
}

function showTableError(msg) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="p-8 text-center text-rose-500">
                <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2"></i>
                <p class="text-sm">${msg}</p>
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

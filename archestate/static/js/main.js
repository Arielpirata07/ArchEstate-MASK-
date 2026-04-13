/**
 * LOGICA PRINCIPAL - ARCHESTATE
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar iconos de Lucide al cargar la página
    if (window.lucide) {
        lucide.createIcons();
    }

    // Inicializar lógica específica de la vista de Usuario
    initUserForm();
});

/**
 * Sistema de Notificaciones Toast
 */
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-8 right-8 z-[100] flex flex-col gap-3';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-emerald-600' : type === 'error' ? 'bg-rose-600' : 'bg-midnight';
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info';

    toast.className = `${bgColor} text-white px-6 py-4 rounded shadow-2xl flex items-center gap-4 transform transition-all duration-500 translate-y-10 opacity-0 border border-white/10`;
    toast.style.minWidth = '300px';
    
    toast.innerHTML = `
        <div class="flex-shrink-0">
            <i data-lucide="${icon}" class="w-5 h-5"></i>
        </div>
        <div class="flex-grow">
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] leading-tight">${message}</p>
        </div>
    `;

    container.appendChild(toast);
    if (window.lucide) {
        lucide.createIcons({
            attrs: { class: 'lucide' },
            nameAttr: 'data-lucide',
            icons: window.lucide.icons
        });
    }

    // Animación de entrada
    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-10', 'opacity-0');
    });

    // Auto-eliminación
    setTimeout(() => {
        toast.classList.add('opacity-0', '-translate-y-2');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

/**
 * Validación de Email (Feedback visual en tiempo real)
 * Nota: La validación real y final ocurre en Python (app.py)
 */
function validateEmail(val) {
    const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    const errorEl = document.getElementById('email-error');
    const inputEl = document.getElementById('email-input');
    const iconEl = document.getElementById('mail-icon');

    if (!errorEl || !inputEl || !iconEl) return isValid;

    if (!isValid && val.length > 0) {
        errorEl.classList.remove('hidden');
        inputEl.classList.add('border-rose-300');
        iconEl.classList.add('text-rose-500');
    } else {
        errorEl.classList.add('hidden');
        inputEl.classList.remove('border-rose-300');
        iconEl.classList.remove('text-rose-500');
    }
    return isValid;
}

/**
 * Inicialización del formulario de usuario
 */
function initUserForm() {
    const form = document.getElementById('userForm');
    const emailInput = document.getElementById('email-input');

    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateEmail(this.value);
        });
    }

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Validación rápida en cliente
            if (!validateEmail(data.email)) return;

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalBtnContent = submitBtn.innerHTML;
            
            // Estado de carga
            submitBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Procesando...`;
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-70');

            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    showToast("¡Solicitud enviada! Los profesionales se contactarán contigo.");
                    setTimeout(() => {
                        window.location.href = "/";
                    }, 1500);
                } else {
                    // Manejar errores devueltos por Python
                    submitBtn.innerHTML = originalBtnContent;
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-70');
                    showToast(result.message, 'error');
                }
            } catch (error) {
                submitBtn.innerHTML = originalBtnContent;
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-70');
                console.error("Error al enviar el formulario:", error);
                showToast("Error de conexión con el servidor", 'error');
            }
        });
    }
}

/**
 * Alternar visibilidad del teléfono (Lógica de seguridad en Python)
 * Permite mostrar y ocultar el teléfono una vez obtenido.
 */
async function togglePhone(btn, leadId) {
    const isRevealed = btn.getAttribute('data-revealed') === 'true';

    if (isRevealed) {
        // Ocultar de nuevo
        btn.innerHTML = `<i data-lucide="eye" class="w-3 h-3"></i> Ver Teléfono`;
        btn.setAttribute('data-revealed', 'false');
        btn.classList.remove('bg-gold');
        btn.classList.add('bg-midnight');
    } else {
        // Mostrar (usar caché si ya se pidió)
        const cachedPhone = btn.getAttribute('data-phone');
        
        if (cachedPhone) {
            btn.innerHTML = `<i data-lucide="eye-off" class="w-3 h-3"></i> ${cachedPhone}`;
            btn.setAttribute('data-revealed', 'true');
            btn.classList.remove('bg-midnight');
            btn.classList.add('bg-gold');
        } else {
            // Estado de carga
            const originalContent = btn.innerHTML;
            btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> Cargando...`;
            btn.disabled = true;
            btn.classList.add('opacity-70');

            try {
                const response = await fetch(`/api/lead/${leadId}/phone`);
                const data = await response.json();
                
                if (data.phone) {
                    btn.setAttribute('data-phone', data.phone);
                    btn.innerHTML = `<i data-lucide="eye-off" class="w-3 h-3"></i> ${data.phone}`;
                    btn.setAttribute('data-revealed', 'true');
                    btn.classList.remove('bg-midnight');
                    btn.classList.add('bg-gold');
                } else {
                    btn.innerHTML = originalContent;
                    showToast("No se pudo obtener el teléfono", 'error');
                }
            } catch (error) {
                btn.innerHTML = originalContent;
                console.error("Error al obtener teléfono:", error);
                showToast("Error de red al consultar teléfono", 'error');
            } finally {
                btn.disabled = false;
                btn.classList.remove('opacity-70');
            }
        }
    }
    
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Actualizar estado de un profesional (Aprobar/Rechazar)
 */
async function updateProStatus(proId, status, btn) {
    const isRejection = status === 'rejected';
    const message = isRejection 
        ? "¡ADVERTENCIA! Está a punto de RECHAZAR a este profesional. Esta acción es crítica y quedará registrada permanentemente en el log de auditoría. ¿Está completamente seguro?"
        : "¿Desea aprobar a este profesional para que pueda acceder a la plataforma?";

    if (!confirm(message)) {
        return;
    }

    // Estado de carga
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>`;
    btn.disabled = true;
    btn.classList.add('opacity-50');

    try {
        const response = await fetch(`/api/admin/professional/${proId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        });

        const result = await response.json();

        if (response.ok) {
            // Animación de éxito: Escalado y cambio de color
            btn.classList.remove('opacity-50', 'text-emerald-600', 'text-rose-600');
            btn.classList.add('scale-150', 'text-emerald-500', 'transition-all', 'duration-500', 'ease-out');
            btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i>`;
            
            if (window.lucide) lucide.createIcons();
            
            showToast(result.message);
            
            // Desvanecer la fila antes de recargar
            const row = btn.closest('tr');
            if (row) {
                // Actualizar visualmente el estado en la tabla
                const statusCell = row.cells[2];
                if (statusCell) {
                    const label = status === 'approved' 
                        ? '<span class="px-2 py-1 bg-emerald-50 text-emerald-700 text-[9px] font-bold uppercase tracking-widest rounded">Aprobado</span>'
                        : '<span class="px-2 py-1 bg-rose-50 text-rose-700 text-[9px] font-bold uppercase tracking-widest rounded">Rechazado</span>';
                    statusCell.innerHTML = label;
                }

                // Ocultar botones de acción
                const actionCell = row.cells[3];
                if (actionCell) {
                    actionCell.innerHTML = '<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest animate-pulse">Procesado</span>';
                }

                row.classList.add('transition-opacity', 'duration-1000', 'opacity-30', 'pointer-events-none');
            }

            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            btn.innerHTML = originalContent;
            btn.disabled = false;
            btn.classList.remove('opacity-50');
            showToast(result.error, 'error');
        }
    } catch (error) {
        btn.innerHTML = originalContent;
        btn.disabled = false;
        btn.classList.remove('opacity-50');
        console.error("Error al actualizar estado:", error);
        showToast("Error al conectar con el servidor", 'error');
    }
}

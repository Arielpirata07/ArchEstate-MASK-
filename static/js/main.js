/* FASE 5.1: IIFE — solo window.* es público. */
(function () {

/**
 * LOGICA PRINCIPAL - ARCHESTATE
 */

function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function csrfSafeMethod(method) {
    return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

(function() {
    var origFetch = window.fetch;
    window.fetch = function(input, init) {
        init = init || {};
        var method = init.method;
        if (!method && input && typeof input.method === 'string') {
            method = input.method;
        }
        if (!csrfSafeMethod((method || 'GET').toUpperCase())) {
            var token = getCsrfToken();
            if (token) {
                var headers = init.headers || {};
                if (headers instanceof Headers) {
                    if (!headers.has('X-CSRFToken')) {
                        headers.set('X-CSRFToken', token);
                    }
                } else {
                    headers['X-CSRFToken'] = token;
                    init.headers = headers;
                }
            }
        }
        return origFetch.call(this, input, init);
    };
})();

document.documentElement.classList.add('js');

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}
// Fuente única para todos los módulos (auth.js, admin.js, ...).
window.escapeHtml = escapeHtml;

/**
 * Delegación de eventos por data-action (FASE 5.9, reemplazo de on* inline).
 * Uso: delegateActions({ 'mi-accion': function(el, e) { ... } }, 'click');
 * En el HTML: <button data-action="mi-accion" data-id="123">.
 * eventName: 'click' (default), 'change', 'input', 'keydown', 'keyup', etc.
 * Funciona también con nodos agregados dinámicamente.
 */
function delegateActions(handlers, eventName) {
    document.addEventListener(eventName || 'click', function(e) {
        var el = e.target.closest ? e.target.closest('[data-action]') : null;
        if (!el || !document.contains(el)) return;
        var fn = handlers[el.dataset.action];
        if (typeof fn === 'function') fn(el, e);
    });
}
window.delegateActions = delegateActions;

/**
 * Detecta la preferencia de movimiento reducido del sistema.
 */
function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Contador animado compartido (dashboards admin/profesional).
 */
function animateCounter(el, target) {
    if (!el) return;
    if (prefersReducedMotion()) {
        el.textContent = target;
        return;
    }
    const duration = 700;
    const start = performance.now();
    const from = 0;
    const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const val = Math.round(from + (target - from) * (1 - Math.pow(1 - progress, 3)));
        el.textContent = val;
        if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

/**
 * Configuración de animación para Chart.js que respeta prefers-reduced-motion.
 */
function chartAnim(duration, easing) {
    if (prefersReducedMotion()) return false;
    return { duration: duration || 500, easing: easing || 'easeOutQuart' };
}

async function togglePhone(btn, leadId) {
    const isRevealed = btn.getAttribute('data-revealed') === 'true';

    if (isRevealed) {
        btn.innerHTML = `<i data-lucide="eye" class="w-3 h-3"></i> ${t('action.view_phone')}`;
        btn.setAttribute('data-revealed', 'false');
        btn.classList.remove('bg-gold');
        btn.classList.add('bg-midnight');
    } else {
        fetch('/api/lead/' + leadId + '/whatsapp-event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event: 'phone_button_clicked' })
        }).catch(function(err) { console.error('whatsapp-event telemetry failed:', err); });

        const cachedPhone = btn.getAttribute('data-phone');

        if (cachedPhone) {
            btn.innerHTML = `<i data-lucide="eye-off" class="w-3 h-3"></i> ${escapeHtml(cachedPhone)}`;
            btn.setAttribute('data-revealed', 'true');
            btn.classList.remove('bg-midnight');
            btn.classList.add('bg-gold');
        } else {
            const originalContent = btn.innerHTML;
            btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> ${t('action.loading')}`;
            btn.disabled = true;
            btn.classList.add('opacity-70');

            try {
                const response = await fetch(`/api/lead/${leadId}/phone`);
                const data = await response.json();

                if (data.phone) {
                    btn.setAttribute('data-phone', data.phone);
                    btn.innerHTML = `<i data-lucide="eye-off" class="w-3 h-3"></i> ${escapeHtml(data.phone)}`;
                    btn.setAttribute('data-revealed', 'true');
                    btn.classList.remove('bg-midnight');
                    btn.classList.add('bg-gold');
                } else {
                    btn.innerHTML = originalContent;
                    showToast(t('error.phone_fetch_failed'), 'error');
                }
            } catch (error) {
                btn.innerHTML = originalContent;
                console.error("Error al obtener telefono:", error);
                showToast(t('error.phone_network'), 'error');
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
    var isRejection = status === 'rejected';
    var confirmMsg = isRejection
        ? t('confirm.reject_professional_warning')
        : t('confirm.approve_professional');

    if (!(await showConfirm(confirmMsg))) {
        return;
    }

    const originalContent = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>`;
    if (window.lucide) lucide.createIcons();
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
            btn.classList.remove('opacity-50', 'text-emerald-600', 'text-rose-600');
            btn.classList.add('scale-150', 'text-emerald-500', 'transition-all', 'duration-500', 'ease-out');
            btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i>`;

            if (window.lucide) lucide.createIcons();

            showToast(result.message);

            const row = btn.closest('tr');
            if (row) {
                const statusCell = row.cells[2];
                if (statusCell) {
                    const label = status === 'approved'
                        ? '<span class="px-2 py-1 bg-emerald-50 text-emerald-700 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.approved') + '</span>'
                        : '<span class="px-2 py-1 bg-rose-50 text-rose-700 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.rejected') + '</span>';
                    statusCell.innerHTML = label;
                }

                const actionCell = row.cells[3];
                if (actionCell) {
                    actionCell.innerHTML = '<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest animate-pulse">' + t('status.processed') + '</span>';
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
        showToast(t('error.server_connection'), 'error');
    }
}

/**
 * LÓGICA DINÁMICA PARA EL REGISTRO (license field toggle)
 */
document.addEventListener('DOMContentLoaded', function() {
    const roleSelect = document.querySelector('select[name="role"]');
    const licenseContainer = document.getElementById('license-container');
    const licenseInput = document.getElementById('license-input');

    if (roleSelect && licenseContainer && licenseInput) {
        roleSelect.addEventListener('change', function() {
            if (this.value === 'professional') {
                licenseContainer.classList.remove('hidden');
                licenseContainer.classList.add('block');
                licenseInput.setAttribute('required', 'required');
                licenseInput.focus();

                if (window.lucide) lucide.createIcons();
            } else {
                licenseContainer.classList.add('hidden');
                licenseContainer.classList.remove('block');
                licenseInput.removeAttribute('required');
                licenseInput.value = '';
            }
        });

        // Trigger on load in case professional was pre-selected
        roleSelect.dispatchEvent(new Event('change'));
    }
});

function initMobileMenu() {
    var menuBtn = document.getElementById('mobile-menu-btn');
    var mobileMenu = document.getElementById('mobile-menu');

    if (!menuBtn || !mobileMenu) return;

    var focusableSelector = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function getFocusable() {
        return Array.prototype.slice.call(mobileMenu.querySelectorAll(focusableSelector));
    }

    function openMenu() {
        openModalAnim(mobileMenu);
        menuBtn.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';

        var icon = document.getElementById('mobile-menu-icon');
        if (icon) {
            icon.setAttribute('data-lucide', 'x');
            if (window.lucide) lucide.createIcons();
        }

        var first = getFocusable()[0];
        if (first) setTimeout(function() { first.focus(); }, 50);
    }

    function closeMenu() {
        closeModalAnim(mobileMenu);
        menuBtn.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';

        var icon = document.getElementById('mobile-menu-icon');
        if (icon) {
            icon.setAttribute('data-lucide', 'menu');
            if (window.lucide) lucide.createIcons();
        }

        menuBtn.focus();
    }

    function isOpen() {
        return !mobileMenu.classList.contains('hidden');
    }

    menuBtn.addEventListener('click', function() {
        if (isOpen()) {
            closeMenu();
        } else {
            openMenu();
        }
    });

    // Close menu when clicking a link
    mobileMenu.querySelectorAll('.mobile-menu-link').forEach(function(link) {
        link.addEventListener('click', closeMenu);
    });

    // Focus trap: intercept Tab and Shift+Tab inside the menu
    mobileMenu.addEventListener('keydown', function(e) {
        if (e.key !== 'Tab') return;
        var focusable = getFocusable();
        if (!focusable.length) return;

        var first = focusable[0];
        var last = focusable[focusable.length - 1];

        if (e.shiftKey) {
            if (document.activeElement === first) {
                e.preventDefault();
                last.focus();
            }
        } else {
            if (document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    });

    // Close menu on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isOpen()) {
            closeMenu();
        }
    });

    // Close menu on click outside (click on the overlay background)
    mobileMenu.addEventListener('click', function(e) {
        if (e.target === mobileMenu) {
            closeMenu();
        }
    });
}

(function() {
    var spotlight = document.querySelector('.cursor-spotlight');
    if (!spotlight) return;
    var ticking = false;
    document.addEventListener('mousemove', function(e) {
        if (!ticking) {
            requestAnimationFrame(function() {
                spotlight.style.left = e.clientX + 'px';
                spotlight.style.top = e.clientY + 'px';
                ticking = false;
            });
            ticking = true;
        }
    });
    document.addEventListener('mouseleave', function() {
        spotlight.style.opacity = '0';
    });
    document.addEventListener('mouseenter', function() {
        spotlight.style.opacity = '1';
    });
})();

/* API pública (usada por otros archivos/templates) */
window.animateCounter = animateCounter;
window.chartAnim = chartAnim;
window.prefersReducedMotion = prefersReducedMotion;
window.togglePhone = togglePhone;
window.updateProStatus = updateProStatus;
window.initMobileMenu = initMobileMenu;

})();

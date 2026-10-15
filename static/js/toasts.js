/* toasts.js — extraído de main.js (FASE 5.2). Carga después de main.js. */
(function () {

function showConfirm(message) {
    return new Promise(function (resolve) {
        var overlay = document.createElement('div');
        overlay.className = 'modal-anim fixed inset-0 z-50 bg-midnight/60 backdrop-blur-sm flex items-center justify-center';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', message);

        var modal = document.createElement('div');
        modal.className = 'modal-panel bg-white rounded-lg shadow-2xl border-t-4 border-gold overflow-hidden w-full max-w-md mx-4';

        modal.innerHTML =
            '<div class="p-6"><p class="text-sm text-midnight leading-relaxed">' +
            escapeHtml(message) +
            '</p></div>' +
            '<div class="flex border-t border-midnight/10">' +
            '<button class="confirm-cancel flex-1 p-4 text-[10px] uppercase tracking-widest font-bold text-midnight/60 hover:text-midnight transition-colors">' + t('confirm.cancel') + '</button>' +
            '<button class="confirm-ok flex-1 p-4 text-[10px] uppercase tracking-widest font-bold text-gold hover:text-midnight transition-colors border-l border-midnight/10">' + t('confirm.accept') + '</button>' +
            '</div>';

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        openModalAnim(overlay);

        function onKeydown(e) {
            if (e.key === 'Escape') { cleanup(); resolve(false); }
        }
        document.addEventListener('keydown', onKeydown);

        function cleanup() {
            document.removeEventListener('keydown', onKeydown);
            closeModalAnim(overlay, function() { overlay.remove(); });
        }

        setTimeout(function () { modal.querySelector('.confirm-ok').focus(); }, 50);

        modal.querySelector('.confirm-cancel').onclick = function () { cleanup(); resolve(false); };
        modal.querySelector('.confirm-ok').onclick = function () { cleanup(); resolve(true); };
        overlay.onclick = function (e) {
            if (e.target === overlay) { cleanup(); resolve(false); }
        };
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar iconos de Lucide al cargar la pagina
    if (window.lucide) {
        lucide.createIcons();
    }

    // Inicializar logica especifica de la vista de Usuario
    if (document.getElementById('userForm')) initUserForm();

    // Inicializar menu mobile
    initMobileMenu();

    // Inicializar scroll animations
    initScrollObserver();

    // Inicializar ripple effect en botones
    initRippleEffect();

    // Inicializar navbar scroll effect
    initNavbarScroll();

    // Inicializar back to top
    initBackToTop();

    // Page entrance fade
    initPageEntrance();

    // Table row stagger
    initTableStagger();
});

/**
 * Sistema de Notificaciones Toast
 */


function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-4 right-4 md:bottom-8 md:right-8 z-50 flex flex-col gap-3 w-full md:w-auto';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-emerald-600' : type === 'error' ? 'bg-rose-600' : 'bg-midnight';
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info';

    const reducedMotion = prefersReducedMotion();

    toast.className = `${bgColor} text-white px-6 py-4 rounded shadow-2xl flex items-center gap-4 transform transition-all duration-500 ${reducedMotion ? '' : 'translate-y-10 opacity-0'} border border-white/10 relative overflow-hidden`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.style.minWidth = '300px';

    toast.innerHTML = `
        <div class="flex-shrink-0">
            <i data-lucide="${icon}" class="w-5 h-5"></i>
        </div>
        <div class="flex-grow">
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] leading-tight">${escapeHtml(message)}</p>
        </div>
        <div class="toast-progress"></div>
    `;

    container.appendChild(toast);
    if (window.lucide) {
        lucide.createIcons({
            attrs: { class: 'lucide' },
            nameAttr: 'data-lucide',
            icons: window.lucide.icons
        });
    }

    // Animacion de entrada
    if (!reducedMotion) {
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-10', 'opacity-0');
        });
    }

    // Auto-eliminacion
    setTimeout(() => {
        if (!reducedMotion) {
            toast.classList.add('opacity-0', '-translate-y-2');
            setTimeout(() => toast.remove(), 500);
        } else {
            toast.remove();
        }
    }, 4000);
}

/**
 * Validacion de Email (Feedback visual en tiempo real)
 */


/* API pública */
window.showConfirm = showConfirm;
window.showToast = showToast;

})();

/* scroll.js — extraído de main.js (FASE 5.2). Carga después de main.js. */
(function () {

function initScrollObserver() {
    if (!('IntersectionObserver' in window)) {
        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            el.classList.add('animate-in');
        });
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

/**
 * Button Ripple Effect
 */


function initRippleEffect() {
    if (prefersReducedMotion()) return;
    document.querySelectorAll('.btn-ripple').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';

            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });
    });
}

/**
 * Modal Animations
 * openModalAnim / closeModalAnim: animan cualquier overlay con la clase
 * "modal-anim" (fade del overlay + scale del panel). Patrón de dos pasos:
 * quitar hidden → reflow → añadir modal-open para disparar la transición.
 */


function smoothScrollTo(target) {
    const el = typeof target === 'string' ? document.querySelector(target) : target;
    if (el) {
        el.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' });
    }
}

/**
 * Navbar Scroll Effect
 */


function initNavbarScroll() {
    const navbar = document.getElementById('main-navbar');
    if (!navbar) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                if (window.pageYOffset > 80) {
                    navbar.classList.add('navbar-shrunk');
                } else {
                    navbar.classList.remove('navbar-shrunk');
                }
                ticking = false;
            });
            ticking = true;
        }
    });
}

/**
 * Back to Top Button
 */


function initBackToTop() {
    const btn = document.getElementById('back-to-top');
    if (!btn) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                if (window.pageYOffset > 400) {
                    btn.classList.add('visible');
                } else {
                    btn.classList.remove('visible');
                }
                ticking = false;
            });
            ticking = true;
        }
    });

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    });
}

/**
 * Page Entrance Fade
 */


function initPageEntrance() {
    var main = document.querySelector('.page-entrance');
    if (!main) return;
    requestAnimationFrame(function() {
        main.classList.add('page-loaded');
        main.addEventListener('animationend', function() {
            main.style.animation = 'none';
            main.style.opacity = '1';
            main.style.transform = 'none';
        }, { once: true });
    });
}

/**
 * Table Row Stagger
 * Adds staggered animation to rows inside containers with class "stagger-rows".
 * Automatically applies animation-delay to each row for a cascade effect.
 * Call with a specific container to animate its rows, or without args for all.
 */


function initTableStagger(container) {
    var targets = container ? [container] : document.querySelectorAll('.stagger-rows');
    targets.forEach(function(el) {
        var rows = el.querySelectorAll('tr');
        rows.forEach(function(row, index) {
            if (!row.classList.contains('table-row-animate')) {
                row.classList.add('table-row-animate');
            }
            row.style.animationDelay = (index * 0.06) + 's';
        });
    });
}

/**
 * Button Loading State Helper
 * Usage: setLoading(buttonElement, true/false, 'Guardando...')
 */


/* API pública */
window.initScrollObserver = initScrollObserver;
window.initRippleEffect = initRippleEffect;
window.smoothScrollTo = smoothScrollTo;
window.initNavbarScroll = initNavbarScroll;
window.initBackToTop = initBackToTop;
window.initPageEntrance = initPageEntrance;
window.initTableStagger = initTableStagger;

})();

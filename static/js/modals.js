/* modals.js — extraído de main.js (FASE 5.2). Carga después de main.js. */
(function () {

function openModalAnim(el) {
    if (!el) return;
    el.classList.remove('hidden');
    void el.offsetWidth;
    requestAnimationFrame(function() {
        el.classList.add('modal-open');
    });
}


function closeModalAnim(el, done) {
    if (!el) return;
    el.classList.remove('modal-open');
    setTimeout(function() {
        el.classList.add('hidden');
        if (typeof done === 'function') done();
    }, 300);
}

/**
 * Smooth Scroll to element
 */


function setLoading(btn, loading, loadingText) {
    if (!btn) return;
    if (loading) {
        btn.setAttribute('data-original-content', btn.innerHTML);
        var text = loadingText || btn.getAttribute('data-loading-text') || t('action.processing');
        btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin inline-block align-middle"></i> ' + text;
        btn.disabled = true;
        btn.classList.add('is-submitting');
        if (window.lucide) lucide.createIcons();
    } else {
        var original = btn.getAttribute('data-original-content');
        if (original) btn.innerHTML = original;
        btn.disabled = false;
        btn.classList.remove('is-submitting');
        if (window.lucide) lucide.createIcons();
    }
}

/* API pública */
window.openModalAnim = openModalAnim;
window.closeModalAnim = closeModalAnim;
window.setLoading = setLoading;

})();

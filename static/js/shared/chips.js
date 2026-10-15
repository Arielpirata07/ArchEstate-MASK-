/* FASE 5.1: IIFE — solo window.* es público. */
(function () {

/**
 * shared/chips.js — selector de chips de valor único (user.js + edit_lead.js).
 *
 * Lógica única parametrizada por ids/clases. Los llamadores exponen wrappers
 * globales (selectChip / selectEditChip) porque los templates los invocan
 * vía onclick. Ver FASE 5.9 (migración a addEventListener) y 5.1 (IIFE).
 */

function createChipSelector(opts) {
    var groups = opts.groups;
    var base = opts.base;
    var ageSectionId = opts.ageSection;
    var ageCls = opts.ageCls;

    function select(field, value) {
        var g = groups[field];
        if (!g) return;
        var hidden = document.getElementById(g.hidden);
        if (hidden) hidden.value = value;
        document.querySelectorAll('.' + g.cls).forEach(function(btn) {
            var active = btn.dataset.value === value;
            btn.className = base[field] + ' '
                + (active
                    ? 'border-midnight bg-midnight text-white'
                    : 'border-midnight/20 text-midnight hover:border-gold');
        });
        if (field === 'condition') syncAge(value);
    }

    function syncAge(condition) {
        var ageSection = document.getElementById(ageSectionId);
        var ageChips = document.querySelectorAll('.' + ageCls);

        if (condition === 'A estrenar') {
            // Auto-seleccionar "Hasta 5 años" y bloquear el resto
            select('age', 'Hasta 5 años');
            ageChips.forEach(function(btn) {
                var isForced = btn.dataset.value === 'Hasta 5 años';
                btn.disabled = !isForced;
                btn.style.opacity = isForced ? '1' : '0.35';
                btn.style.cursor = isForced ? 'default' : 'not-allowed';
            });
            if (ageSection) ageSection.classList.remove('hidden');
        } else if (condition === 'En construcción') {
            // Sin antigüedad aplicable → ocultar la sección
            select('age', '');
            if (ageSection) ageSection.classList.add('hidden');
        } else if (condition === 'A reciclar') {
            // Sugerir "Más de 30 años" pero sin bloquear
            if (ageSection) ageSection.classList.remove('hidden');
            ageChips.forEach(function(btn) { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
            select('age', 'Más de 30 años');
        } else {
            // Sin preferencia / Usado → todo desbloqueado
            if (ageSection) ageSection.classList.remove('hidden');
            ageChips.forEach(function(btn) { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
        }
    }

    return { select: select, syncAge: syncAge };
}

window.createChipSelector = createChipSelector;

/* API pública (usada por otros archivos/templates) */
window.createChipSelector = createChipSelector;

})();

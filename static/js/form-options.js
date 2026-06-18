/* ================================================================
   form-options.js — Dynamic form option rendering
   Reads from window.__FORM_OPTIONS (injected by Jinja)
   ================================================================ */

function foGetPropertyTypes() {
    return (window.__FORM_OPTIONS && window.__FORM_OPTIONS.property_type) || [];
}

function foGetOptions(category) {
    return (window.__FORM_OPTIONS && window.__FORM_OPTIONS[category]) || [];
}

function foRenderPropertyTypeButtons(containerId, onSelect) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var options = foGetPropertyTypes();
    container.innerHTML = options.map(function(o) {
        var iconHtml = o.icon ? '<i data-lucide="' + o.icon + '" class="w-4 h-4 inline mr-2"></i>' : '';
        return '<button type="button" data-value="' + escapeHtml(o.value) + '" ' +
            'class="prop-type-btn flex-1 min-w-[120px] py-3 px-4 rounded border-2 border-midnight/20 bg-white text-midnight font-semibold transition-all hover:border-gold">' +
            iconHtml + escapeHtml(o.label) + '</button>';
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();

    container.querySelectorAll('.prop-type-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (onSelect) onSelect(btn.dataset.value);
        });
    });
}

function foRenderChips(containerId, options, chipClass, onSelect) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = options.map(function(o) {
        var iconHtml = o.icon ? '<i data-lucide="' + o.icon + '" class="w-3 h-3"></i> ' : '';
        return '<button type="button" data-value="' + escapeHtml(o.value) + '" ' +
            'class="' + chipClass + ' flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold border border-midnight/10 transition-all">' +
            iconHtml + escapeHtml(o.label) + '</button>';
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();

    container.querySelectorAll('[data-value]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            if (onSelect) onSelect(btn.dataset.value);
        });
    });
}

function foRenderSelect(selectId, options, placeholder) {
    var select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">' + (placeholder || 'Seleccionar') + '</option>' +
        options.map(function(o) {
            return '<option value="' + escapeHtml(o.value) + '">' + escapeHtml(o.label) + '</option>';
        }).join('');
}

function foSetActiveButton(containerId, value) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.querySelectorAll('[data-value]').forEach(function(btn) {
        if (btn.dataset.value === value) {
            btn.classList.add('border-gold', 'bg-gold/10', 'text-midnight');
            btn.classList.remove('border-midnight/10', 'text-midnight/60');
        } else {
            btn.classList.remove('border-gold', 'bg-gold/10', 'text-midnight');
            btn.classList.add('border-midnight/10', 'text-midnight/60');
        }
    });
}

function foSetActiveChip(containerId, value) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.querySelectorAll('[data-value]').forEach(function(btn) {
        if (btn.dataset.value === value) {
            btn.classList.add('border-gold', 'bg-gold/10', 'text-midnight');
            btn.classList.remove('border-midnight/10', 'text-midnight/60');
        } else {
            btn.classList.remove('border-gold', 'bg-gold/10', 'text-midnight');
            btn.classList.add('border-midnight/10', 'text-midnight/60');
        }
    });
}

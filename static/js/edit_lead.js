/* FASE 5.1: IIFE — solo window.* es público. */
(function () {

// ============================================================
// EDIT LEAD FORM — ArchEstate
// ============================================================

var EDIT_LEAD_ID = null;

function initEditLeadForm(leadId) {
    EDIT_LEAD_ID = leadId;
    var form = document.getElementById('editLeadForm');
    if (!form) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitEditLead();
    });

    var builtInput = document.getElementById('edit-built-area');
    var landInput = document.getElementById('edit-land-area');
    if (builtInput && landInput) {
        builtInput.addEventListener('input', checkAreaRatio);
        landInput.addEventListener('input', checkAreaRatio);
        checkAreaRatio();
    }
}

function checkAreaRatio() {
    var built = parseFloat(document.getElementById('edit-built-area').value) || 0;
    var land = parseFloat(document.getElementById('edit-land-area').value) || 0;
    var warning = document.getElementById('edit-area-warning');
    var hint = document.getElementById('edit-area-hint');
    if (!warning || !hint) return;

    if (land > 0 && built > land * 0.8) {
        warning.classList.remove('hidden');
        hint.classList.add('hidden');
    } else {
        warning.classList.add('hidden');
        hint.classList.remove('hidden');
    }
}

// ============================================================
// CHIPS — vía shared/chips.js (misma lógica que user.js)
// ============================================================
var EDIT_CHIP_GROUPS = {
    parking:     { hidden: 'edit-parking',     cls: 'edit-parking-chip' },
    orientation: { hidden: 'edit-orientation', cls: 'edit-orientation-chip' },
    condition:   { hidden: 'edit-property-condition', cls: 'edit-condition-chip' },
    age:         { hidden: 'edit-property-age',       cls: 'edit-age-chip' },
};

var EDIT_CHIP_BASE = {
    parking:     'edit-parking-chip px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    orientation: 'edit-orientation-chip px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    condition:   'edit-condition-chip w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
    age:         'edit-age-chip w-full text-left px-3 py-2 rounded border-2 text-[10px] font-bold uppercase tracking-widest transition-all',
};

var editChips = createChipSelector({
    groups: EDIT_CHIP_GROUPS, base: EDIT_CHIP_BASE, ageSection: 'edit-age-section', ageCls: 'edit-age-chip',
});

// Wrappers globales: los templates los invocan vía onclick.
function selectEditChip(field, value) {
    editChips.select(field, value);
}

function syncEditAgeToCondition(condition) {
    editChips.syncAge(condition);
}

function initEditChips() {
    if (!window.__leadData) return;
    var d = window.__leadData;
    if (d.parking) selectEditChip('parking', d.parking);
    if (d.orientation) selectEditChip('orientation', d.orientation);
    if (d.property_condition) selectEditChip('condition', d.property_condition);
    if (d.property_age) selectEditChip('age', d.property_age);
}

// ============================================================
// STEPPERS
// ============================================================
function stepEditNum(inputId, delta) {
    var el = document.getElementById(inputId);
    if (!el) return;
    var min = parseInt(el.min) || 0;
    var max = parseInt(el.max) || 99;
    var cur = parseInt(el.value) || 0;
    var next = cur + delta;
    el.value = next < min ? '' : Math.min(max, next);
}

// ============================================================
// FORM SUBMIT
// ============================================================
function submitEditLead() {
    var btn = document.getElementById('save-lead-btn');
    var msg = document.getElementById('lead-save-msg');
    var err = document.getElementById('lead-error-msg');

    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> ' + t('action.saving');
    if (window.lucide) lucide.createIcons();
    if (msg) msg.classList.add('hidden');
    if (err) err.classList.add('hidden');

    var data = {
        zone: document.getElementById('edit-zone').value,
        province: document.getElementById('edit-province').value,
        budget: document.getElementById('edit-budget').value,
        currency: document.getElementById('edit-currency').value,
        architectural_style: document.getElementById('edit-architectural-style').value,
        ambientes: parseInt(document.getElementById('edit-ambientes').value) || 0,
        bedrooms: parseInt(document.getElementById('edit-bedrooms').value) || 0,
        bathrooms: parseInt(document.getElementById('edit-bathrooms').value) || 0,
        usable_m2: parseFloat(document.getElementById('edit-usable-m2').value) || 0,
        total_area: parseFloat(document.getElementById('edit-total-area').value) || 0,
        land_area: parseFloat(document.getElementById('edit-land-area').value) || 0,
        built_area: parseFloat(document.getElementById('edit-built-area').value) || 0,
        floor_block: document.getElementById('edit-floor-block').value,
        elevator: document.getElementById('edit-elevator').value,
        pool: document.getElementById('edit-pool').value,
        parking: document.getElementById('edit-parking').value,
        orientation: document.getElementById('edit-orientation').value,
        property_condition: document.getElementById('edit-property-condition').value,
        property_age: document.getElementById('edit-property-age').value,
    };

    var amenities = [];
    document.querySelectorAll('.amenity-checkbox:checked').forEach(function(cb) {
        amenities.push(cb.value);
    });
    data.amenities = amenities.join(', ');

    fetch('/api/profile/lead/' + EDIT_LEAD_ID, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    })
    .then(function(r) { return r.json(); })
    .then(function(result) {
        if (result.error) {
            if (err) { err.textContent = result.error; err.classList.remove('hidden'); }
        } else {
            if (msg) msg.classList.remove('hidden');
            setTimeout(function() { if (msg) msg.classList.add('hidden'); }, 3000);
        }
    })
    .catch(function() {
        if (err) { err.textContent = t('error.connection'); err.classList.remove('hidden'); }
    })
    .finally(function() {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> ' + t('action.save_changes');
        if (window.lucide) lucide.createIcons();
    });
}

/* Delegación data-action (FASE 5.9): reemplaza onclick inline */
delegateActions({
    'edit-chip': function(el) { selectEditChip(el.dataset.group, el.dataset.value); },
    'edit-step': function(el) { stepEditNum(el.dataset.field, parseInt(el.dataset.delta, 10)); }
});

/* API pública (usada por otros archivos/templates) */
window.initEditLeadForm = initEditLeadForm;
window.initEditChips = initEditChips;

})();

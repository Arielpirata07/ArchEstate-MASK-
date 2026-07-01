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
// CHIPS — same pattern as user.js but with edit- prefixes
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

function initEditChips() {
    if (!window.__leadData) return;
    var d = window.__leadData;
    if (d.parking) selectEditChip('parking', d.parking);
    if (d.orientation) selectEditChip('orientation', d.orientation);
    if (d.property_condition) selectEditChip('condition', d.property_condition);
    if (d.property_age) selectEditChip('age', d.property_age);
}

function selectEditChip(field, value) {
    var g = EDIT_CHIP_GROUPS[field];
    if (!g) return;
    var hidden = document.getElementById(g.hidden);
    if (hidden) hidden.value = value;

    document.querySelectorAll('.' + g.cls).forEach(function(btn) {
        var active = btn.dataset.value === value;
        btn.className = EDIT_CHIP_BASE[field] + ' '
            + (active
                ? 'border-midnight bg-midnight text-white'
                : 'border-midnight/20 text-midnight hover:border-gold');
    });

    if (field === 'condition') syncEditAgeToCondition(value);
}

function syncEditAgeToCondition(condition) {
    var ageSection = document.getElementById('edit-age-section');
    var ageChips = document.querySelectorAll('.edit-age-chip');

    if (condition === 'A estrenar') {
        selectEditChip('age', 'Hasta 5 años');
        ageChips.forEach(function(btn) {
            var isForced = btn.dataset.value === 'Hasta 5 años';
            btn.disabled = !isForced;
            btn.style.opacity = isForced ? '1' : '0.35';
            btn.style.cursor = isForced ? 'default' : 'not-allowed';
        });
        if (ageSection) ageSection.classList.remove('hidden');
    } else if (condition === 'En construcción') {
        selectEditChip('age', '');
        if (ageSection) ageSection.classList.add('hidden');
    } else if (condition === 'A reciclar') {
        if (ageSection) ageSection.classList.remove('hidden');
        ageChips.forEach(function(btn) { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
        selectEditChip('age', 'Más de 30 años');
    } else {
        if (ageSection) ageSection.classList.remove('hidden');
        ageChips.forEach(function(btn) { btn.disabled = false; btn.style.opacity = '1'; btn.style.cursor = ''; });
    }
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
    btn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin"></i> Guardando...';
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
        if (err) { err.textContent = 'Error de conexión'; err.classList.remove('hidden'); }
    })
    .finally(function() {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Guardar Cambios';
        if (window.lucide) lucide.createIcons();
    });
}

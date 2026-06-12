// ================================================================
// UPLOAD WIDGET
// ================================================================
const IS_PENDING = document.querySelector('[data-pending]')?.dataset.pending === 'true';
const ALLOWED_EXT = ['.pdf', '.jpg', '.jpeg', '.png'];
const MAX_MB      = 10;
let   selectedFiles = {};

function renderUploadWidget(cid) {
    const container = document.getElementById(cid);
    if (!container) return;

    container.innerHTML = `
        <div class="space-y-4">

            <!-- Zona drag & drop -->
            <div id="dropzone-${cid}"
                 class="relative border-2 border-dashed border-midnight/20 rounded-lg p-8 text-center transition-all duration-200 cursor-pointer hover:border-gold hover:bg-paper group"
                 onclick="document.getElementById('fileInput-${cid}').click()"
                 ondragover="handleDragOver(event,'${cid}')"
                 ondragleave="handleDragLeave(event,'${cid}')"
                 ondrop="handleDrop(event,'${cid}')">

                <input type="file" id="fileInput-${cid}" accept=".pdf,.jpg,.jpeg,.png"
                       class="hidden" onchange="handleFileSelect(event,'${cid}')">

                <div class="w-14 h-14 mx-auto rounded-full bg-paper-dark group-hover:bg-gold/10 flex items-center justify-center mb-4 transition-colors">
                    <i data-lucide="upload-cloud" class="w-7 h-7 text-midnight/30 group-hover:text-gold transition-colors"></i>
                </div>
                <p class="text-sm font-semibold text-midnight/70 group-hover:text-midnight transition-colors">Arrastrá tu archivo aquí</p>
                <p class="text-[10px] text-midnight/40 mt-1 uppercase tracking-widest font-bold">o hacé clic para seleccionar</p>
                <p class="text-[9px] text-midnight/30 mt-3 uppercase tracking-widest">PDF · JPG · PNG &nbsp;·&nbsp; Máx. ${MAX_MB} MB</p>
            </div>

            <!-- Preview del archivo seleccionado -->
            <div id="filePreview-${cid}" class="hidden">
                <div class="flex items-center gap-4 p-4 bg-paper-dark rounded-lg border border-midnight/10">
                    <div id="fileIcon-${cid}" class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-gold/10">
                        <i data-lucide="file" class="w-5 h-5 text-gold"></i>
                    </div>
                    <div class="flex-grow min-w-0">
                        <p id="fileName-${cid}" class="text-sm font-semibold text-midnight truncate"></p>
                        <p id="fileSize-${cid}" class="text-[10px] text-midnight/40 mt-0.5 uppercase tracking-widest font-bold"></p>
                    </div>
                    <button onclick="clearFile('${cid}')" class="p-2 text-midnight/30 hover:text-rose-500 transition-colors flex-shrink-0" title="Quitar archivo">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- Barra de progreso -->
            <div id="progressWrapper-${cid}" class="hidden space-y-2">
                <div class="flex justify-between items-center">
                    <p class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">Subiendo documento...</p>
                    <span id="progressPct-${cid}" class="text-[10px] font-bold text-gold">0%</span>
                </div>
                <div class="h-1.5 bg-midnight/10 rounded-full overflow-hidden">
                    <div id="progressBar-${cid}" class="h-full bg-gold rounded-full transition-all duration-300" style="width:0%"></div>
                </div>
            </div>

            <!-- Estado: documento ya cargado -->
            <div id="docStatus-${cid}" class="hidden space-y-2">
                <div class="flex items-center gap-3 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
                    <i data-lucide="check-circle" class="w-4 h-4 text-emerald-600 flex-shrink-0"></i>
                    <div class="flex-grow min-w-0">
                        <p class="text-[10px] font-bold uppercase tracking-widest text-emerald-700">Documento cargado</p>
                        <p id="docStatusName-${cid}" class="text-xs text-emerald-600 mt-0.5 truncate font-medium"></p>
                    </div>
                    <a href="${(document.getElementById('docApproved') || {}).dataset ? document.getElementById('docApproved').dataset.downloadUrl : '#'}"
                       class="flex-shrink-0 flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-[9px] font-bold uppercase tracking-widest hover:bg-emerald-200 transition-colors">
                        <i data-lucide="download" class="w-3 h-3"></i> Descargar
                    </a>
                </div>
                <button onclick="replaceDoc('${cid}')"
                    class="w-full text-[10px] text-midnight/40 hover:text-gold transition-colors font-bold uppercase tracking-widest py-1 flex items-center justify-center gap-1">
                    <i data-lucide="refresh-cw" class="w-3 h-3"></i> Reemplazar documento
                </button>
            </div>

            <!-- Botón de envío -->
            <div id="submitWrapper-${cid}" class="hidden">
                <button id="uploadBtn-${cid}" onclick="uploadFile('${cid}')"
                    class="w-full py-3 bg-midnight text-white rounded font-bold uppercase tracking-widest text-[10px] hover:bg-gold transition-all flex items-center justify-center gap-2">
                    <i data-lucide="upload" class="w-4 h-4"></i>
                    Subir Documentación
                </button>
            </div>

        </div>
    `;

    if (window.lucide) lucide.createIcons();
    loadDocStatus(cid);
}

// ---- Carga estado existente desde la API ----
async function loadDocStatus(cid) {
    try {
        const res  = await fetch('/api/professional/doc-status');
        const data = await res.json();
        if (data.has_doc) markDocLoaded(cid, data.display_name);
    } catch (e) { console.warn('loadDocStatus fetch failed:', e); }
}

function markDocLoaded(cid, name) {
    document.getElementById(`dropzone-${cid}`)?.classList.add('hidden');
    document.getElementById(`submitWrapper-${cid}`)?.classList.add('hidden');
    document.getElementById(`docStatus-${cid}`)?.classList.remove('hidden');
    const nameEl = document.getElementById(`docStatusName-${cid}`);
    if (nameEl) nameEl.textContent = name || 'Documento cargado';

    // Actualizar paso 2 en el sidebar (solo estado pendiente)
    const icon  = document.getElementById('step2-icon');
    const label = document.getElementById('step2-label');
    const sub   = document.getElementById('step2-sub');
    if (icon) {
        icon.className = 'w-6 h-6 rounded-full bg-gold flex items-center justify-center flex-shrink-0 mt-0.5';
        icon.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-white"></i>';
        label.className   = 'text-white text-xs font-bold uppercase tracking-widest';
        label.textContent = 'Documentación enviada';
        sub.textContent   = name || '';
        if (window.lucide) lucide.createIcons();
    }
}

// ---- Drag & drop ----
function handleDragOver(e, cid) {
    e.preventDefault();
    document.getElementById(`dropzone-${cid}`).classList.add('border-gold', 'bg-paper');
}
function handleDragLeave(e, cid) {
    document.getElementById(`dropzone-${cid}`).classList.remove('border-gold', 'bg-paper');
}
function handleDrop(e, cid) {
    e.preventDefault();
    handleDragLeave(e, cid);
    if (e.dataTransfer.files[0]) processFile(e.dataTransfer.files[0], cid);
}
function handleFileSelect(e, cid) {
    if (e.target.files[0]) processFile(e.target.files[0], cid);
}

// ---- Procesar archivo ----
function processFile(file, cid) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXT.includes(ext)) {
        if (typeof showToast === 'function') showToast(`Tipo no permitido. Usá: PDF, JPG o PNG.`, 'error');
        return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
        if (typeof showToast === 'function') showToast(`El archivo supera los ${MAX_MB} MB.`, 'error');
        return;
    }

    selectedFiles[cid] = file;

    // Ícono por tipo MIME
    const iconEl = document.getElementById(`fileIcon-${cid}`);
    if (file.type === 'application/pdf') {
        iconEl.className = 'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-rose-50';
        iconEl.innerHTML = '<i data-lucide="file-text" class="w-5 h-5 text-rose-500"></i>';
    } else {
        iconEl.className = 'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-blue-50';
        iconEl.innerHTML = '<i data-lucide="image" class="w-5 h-5 text-blue-500"></i>';
    }

    document.getElementById(`fileName-${cid}`).textContent = file.name;
    document.getElementById(`fileSize-${cid}`).textContent = formatBytes(file.size);

    document.getElementById(`dropzone-${cid}`).classList.add('hidden');
    document.getElementById(`docStatus-${cid}`).classList.add('hidden');
    document.getElementById(`filePreview-${cid}`).classList.remove('hidden');
    document.getElementById(`submitWrapper-${cid}`).classList.remove('hidden');

    if (window.lucide) lucide.createIcons();
}

function clearFile(cid) {
    selectedFiles[cid] = null;
    const input = document.getElementById(`fileInput-${cid}`);
    if (input) input.value = '';
    document.getElementById(`filePreview-${cid}`).classList.add('hidden');
    document.getElementById(`submitWrapper-${cid}`).classList.add('hidden');
    document.getElementById(`dropzone-${cid}`).classList.remove('hidden');
}

function replaceDoc(cid) {
    document.getElementById(`docStatus-${cid}`).classList.add('hidden');
    document.getElementById(`dropzone-${cid}`).classList.remove('hidden');
}

// ---- Subida con barra de progreso ----
async function uploadFile(cid) {
    const file = selectedFiles[cid];
    if (!file) return;

    const btn = document.getElementById(`uploadBtn-${cid}`);
    btn.disabled = true;

    document.getElementById(`filePreview-${cid}`).classList.add('hidden');
    document.getElementById(`submitWrapper-${cid}`).classList.add('hidden');
    document.getElementById(`progressWrapper-${cid}`).classList.remove('hidden');

    // Progreso animado (simulado, ya que fetch no expone upload progress)
    let pct = 0;
    const bar   = document.getElementById(`progressBar-${cid}`);
    const pctEl = document.getElementById(`progressPct-${cid}`);
    const tick  = setInterval(() => {
        pct = Math.min(pct + Math.random() * 18, 88);
        bar.style.width   = pct + '%';
        pctEl.textContent = Math.round(pct) + '%';
    }, 180);

    const formData = new FormData();
    formData.append('document', file);

    try {
        const res  = await fetch('/api/professional/upload', { method: 'POST', body: formData });
        const data = await res.json();

        clearInterval(tick);
        bar.style.width   = '100%';
        pctEl.textContent = '100%';

        // Pequeña pausa para que se vea el 100%
        await new Promise(r => setTimeout(r, 350));
        document.getElementById(`progressWrapper-${cid}`).classList.add('hidden');

        if (res.ok) {
            markDocLoaded(cid, data.display_name);
            if (typeof showToast === 'function') showToast(data.message);
        } else {
            document.getElementById(`dropzone-${cid}`).classList.remove('hidden');
            if (typeof showToast === 'function') showToast(data.error || 'Error al subir el archivo.', 'error');
        }
    } catch (err) {
        clearInterval(tick);
        document.getElementById(`progressWrapper-${cid}`).classList.add('hidden');
        document.getElementById(`dropzone-${cid}`).classList.remove('hidden');
        if (typeof showToast === 'function') showToast('Error de conexión al subir el archivo.', 'error');
    }

    btn.disabled       = false;
    selectedFiles[cid] = null;
}

// ---- Toggle panel doc (aprobado) ----
let docPanelInitialized = false;
function toggleDocPanel() {
    const panel   = document.getElementById('docPanel');
    const chevron = document.getElementById('docChevron');
    const isHidden = panel.classList.contains('hidden');

    panel.classList.toggle('hidden', !isHidden);
    chevron.style.transform = isHidden ? 'rotate(180deg)' : '';

    // Inicializar widget solo la primera vez que se abre
    if (isHidden && !docPanelInitialized) {
        docPanelInitialized = true;
        renderUploadWidget('docApproved');
    }
}

// ---- Helpers ----
function formatBytes(bytes) {
    if (bytes < 1024)         return bytes + ' B';
    if (bytes < 1024 * 1024)  return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ================================================================
// INIT
// ================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Widget en estado pendiente
    if (document.getElementById('uploadWidgetPending')) {
        renderUploadWidget('uploadWidgetPending');
    }

    if (!IS_PENDING) {
    loadLeads();
    setupLeadEventListeners();
    }
});

// ================================================================
// LEADS (solo si está aprobado)
// ================================================================
if (!IS_PENDING) {
let currentFilters = {
    search: '', type: '', property_type: '', zone: '',
    min_budget: '', max_budget: '', budget_range: '',
    currency: '', sort: 'timestamp', order: 'desc'
};

// ---- Labels legibles para los filtros activos ----
const PROP_LABELS = {
    departamento: 'Departamento', casa: 'Casa', duplex: 'Dúplex',
    penthouse: 'Penthouse', local_comercial: 'Local Comercial',
};
const BUDGET_LABELS = {
    hasta_200k: 'Hasta $200k', '200k_500k': '$200k–$500k',
    '500k_1m': '$500k–$1M', '1m_2m': '$1M–$2M', mas_2m: 'Más de $2M',
};

// ---- Íconos por tipo de propiedad ----
const PROP_ICONS = {
    departamento: 'building', casa: 'home', duplex: 'layers',
    penthouse: 'crown', local_comercial: 'store',
};

function setupLeadEventListeners() {
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('clearFilters').addEventListener('click', clearFilters);
    document.getElementById('sortSelect').addEventListener('change', updateSort);
    document.getElementById('sortOrder').addEventListener('click', toggleSortOrder);

    // Búsqueda en tiempo real con debounce
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 400);
    });

    // Aplicar al presionar Enter en zona
    document.getElementById('zoneFilter').addEventListener('keydown', e => {
        if (e.key === 'Enter') applyFilters();
    });
}

// ---- Chips: Tipo de Vivienda ----
function setPropType(value) {
    currentFilters.property_type = value;
    document.querySelectorAll('.prop-chip').forEach(btn => {
        const active = btn.dataset.value === value;
        btn.className = 'prop-chip px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all '
            + (active
                ? 'border-midnight bg-midnight text-white'
                : 'border-midnight/20 text-midnight/60 hover:border-gold hover:text-gold');
    });
    applyFilters();
}

// ---- Chips: Rango de Inversión ----
function setBudgetRange(range) {
    currentFilters.budget_range = range;
    document.querySelectorAll('.budget-chip').forEach(btn => {
        const active = btn.dataset.range === range;
        btn.className = 'budget-chip px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all '
            + (active
                ? 'border-midnight bg-midnight text-white'
                : 'border-midnight/20 text-midnight/60 hover:border-gold hover:text-gold');
    });
    applyFilters();
}

// ---- Barra de filtros activos ----
function renderActiveTags() {
    const container = document.getElementById('activeFilterTags');
    const countEl   = document.getElementById('activeFiltersCount');
    const tags = [];

    if (currentFilters.search)        tags.push({ key: 'search',       label: `"${currentFilters.search}"` });
    if (currentFilters.type)          tags.push({ key: 'type',         label: currentFilters.type });
    if (currentFilters.property_type) tags.push({ key: 'property_type',label: PROP_LABELS[currentFilters.property_type] || currentFilters.property_type });
    if (currentFilters.zone)          tags.push({ key: 'zone',         label: `Zona: ${currentFilters.zone}` });
    if (currentFilters.budget_range)  tags.push({ key: 'budget_range', label: BUDGET_LABELS[currentFilters.budget_range] || currentFilters.budget_range });

    if (tags.length === 0) {
        container.innerHTML = '';
        countEl.classList.add('hidden');
        return;
    }

    countEl.textContent = `${tags.length} activo${tags.length > 1 ? 's' : ''}`;
    countEl.classList.remove('hidden');

    container.innerHTML = tags.map(t => `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gold/10 text-gold border border-gold/20 rounded-full text-[9px] font-bold uppercase tracking-widest">
            ${t.label}
            <button onclick="removeFilter('${t.key}')" class="hover:text-rose-500 transition-colors">
                <i data-lucide="x" class="w-2.5 h-2.5"></i>
            </button>
        </span>
    `).join('');
    if (window.lucide) lucide.createIcons();
}

function removeFilter(key) {
    currentFilters[key] = '';
    if (key === 'property_type') setPropType('');
    if (key === 'budget_range')  setBudgetRange('');
    if (key === 'search')  document.getElementById('searchInput').value = '';
    if (key === 'type')    { document.getElementById('typeFilter').value = ''; }
    if (key === 'zone')    document.getElementById('zoneFilter').value = '';
    applyFilters();
}

// ---- Cargar y renderizar leads ----
async function loadLeads() {
    const params = new URLSearchParams();
    Object.entries(currentFilters).forEach(([k, v]) => { if (v) params.set(k, v); });

    const tbody = document.getElementById('leadsTableBody');
    tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-midnight/60">
        <div class="flex justify-center items-center gap-2">
            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gold"></div>
            Buscando leads...
        </div></td></tr>`;

    try {
        const res  = await fetch(`/api/leads?${params}`);
        const data = await res.json();
        if (data.success) {
            renderLeads(data.leads);
            document.getElementById('leadsCount').textContent = data.total;
            renderActiveTags();
        } else {
            showLeadError(data.error || 'Error al cargar leads');
        }
    } catch (err) {
        showLeadError('Error de conexión');
    }
}

function formatBudget(value) {
    if (!value) return '0';
    const cleaned = String(value).replace(/[^\d.,]/g, '');
    if (!cleaned) return value;
    const num = parseFloat(cleaned.replace(/,/g, '').replace(/\./g, ''));
    if (isNaN(num)) return value;
    if (num >= 1000000) return (num / 1000000).toFixed(1).replace('.0', '') + 'M';
    if (num >= 1000) return (num / 1000).toFixed(0) + 'k';
    return num.toLocaleString('es-AR');
}

function renderLeads(leads) {
    const tbody = document.getElementById('leadsTableBody');
    if (!leads.length) {
        tbody.innerHTML = `
            <tr><td colspan="8" class="p-12 text-center text-midnight/60">
                <i data-lucide="search-x" class="w-10 h-10 mx-auto mb-3 text-midnight/20"></i>
                <p class="font-semibold text-midnight/40">Sin resultados para estos filtros</p>
                <p class="text-xs text-midnight/30 mt-1">Probá ajustando el tipo de vivienda o el rango de inversión</p>
            </td></tr>`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = leads.map(lead => {
        const sym      = lead.currency === 'USD' ? 'US$' : lead.currency === 'EUR' ? '€' : '$';
        const propType = lead.property_type || '';
        const propIcon = PROP_ICONS[propType.toLowerCase()] || 'home';
        const propLabel = PROP_LABELS[propType.toLowerCase()] || propType;
        const propBadge = propType
            ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-paper-dark text-midnight/60 rounded text-[9px] font-bold uppercase tracking-widest">
                   <i data-lucide="${propIcon}" class="w-2.5 h-2.5"></i>${propLabel}
               </span>`
            : '<span class="text-midnight/25 text-xs italic">—</span>';

        // Detalles técnicos compactos
        const specs = [];
        if (lead.ambientes)          specs.push(`${lead.ambientes} amb.`);
        if (lead.bedrooms)           specs.push(`${lead.bedrooms} hab.`);
        if (lead.bathrooms)          specs.push(`${lead.bathrooms} baños`);
        if (lead.usable_m2 > 0)      specs.push(`${lead.usable_m2} m²`);
        if (lead.land_area > 0)      specs.push(`${lead.land_area} m² terreno`);

        const specLine = specs.length
            ? `<div class="text-[9px] text-midnight/40 font-bold uppercase tracking-widest mt-0.5">${specs.join(' · ')}</div>`
            : '';

        // Badges extra
        const parkingLabels = { sin_cochera:'Sin cochera', simple_cubierta:'Coch. simple', doble_cubierta:'Coch. doble', descubierta:'Desc.', garage:'Garage' };
        const conditionColors = { 'A estrenar':'bg-emerald-50 text-emerald-700', 'Usado':'bg-paper-dark text-midnight/60', 'A reciclar':'bg-amber-50 text-amber-700', 'En construcción':'bg-blue-50 text-blue-700' };

        const extraBadges = [];
        if (lead.parking && lead.parking !== '' && parkingLabels[lead.parking]) {
            extraBadges.push(`<span class="px-1.5 py-0.5 bg-paper-dark text-midnight/50 rounded text-[8px] font-bold uppercase tracking-widest">${parkingLabels[lead.parking]}</span>`);
        }
        if (lead.orientation && lead.orientation !== '') {
            extraBadges.push(`<span class="px-1.5 py-0.5 bg-paper-dark text-midnight/50 rounded text-[8px] font-bold uppercase tracking-widest">${escapeHtml(lead.orientation)}</span>`);
        }
        if (lead.property_condition && lead.property_condition !== '') {
            const cls = conditionColors[lead.property_condition] || 'bg-paper-dark text-midnight/50';
            extraBadges.push(`<span class="px-1.5 py-0.5 ${cls} rounded text-[8px] font-bold uppercase tracking-widest">${escapeHtml(lead.property_condition)}</span>`);
        }
        if (lead.property_age && lead.property_age !== '') {
            extraBadges.push(`<span class="px-1.5 py-0.5 bg-paper-dark text-midnight/50 rounded text-[8px] font-bold uppercase tracking-widest">${escapeHtml(lead.property_age)}</span>`);
        }
        const extrasLine = extraBadges.length
            ? `<div class="flex flex-wrap gap-1 mt-1">${extraBadges.join('')}</div>`
            : '';

        const tracking = lead.tracking || { seen: false, contacted: false };

        return `
            <tr class="border-b border-midnight/5 hover:bg-paper transition-colors group" data-lead-id="${lead.id}" data-seen="${tracking.seen}" data-contacted="${tracking.contacted}">
                <td class="p-4 font-mono text-xs text-midnight/60">${lead.id}</td>
                <td class="p-4">
                    <div class="flex flex-col gap-1.5">
                        <button type="button" onclick="toggleLeadStatus(${lead.id}, 'seen', this)"
                                class="status-btn status-btn-seen ${tracking.seen ? 'status-active' : ''}"
                                data-status="seen"
                                data-lead-id="${lead.id}">
                            <i data-lucide="eye" class="w-3 h-3"></i>
                            <span>${tracking.seen ? 'Visto' : 'Ver'}</span>
                        </button>
                        <button type="button" onclick="toggleLeadStatus(${lead.id}, 'contacted', this)"
                                class="status-btn status-btn-contacted ${tracking.contacted ? 'status-active' : ''}"
                                data-status="contacted"
                                data-lead-id="${lead.id}">
                            <i data-lucide="message-circle" class="w-3 h-3"></i>
                            <span>${tracking.contacted ? 'Contactado' : 'Contactar'}</span>
                        </button>
                    </div>
                </td>
                <td class="p-4 text-sm font-medium">${escapeHtml(lead.type)}</td>
                <td class="p-4">${propBadge}</td>
                <td class="p-4 text-sm text-midnight/70">${escapeHtml(lead.zone)}</td>
                <td class="p-4">
                    <div class="budget-display">
                        <span class="budget-currency-tag">${sym}</span>
                        <span class="budget-amount" title="${escapeHtml(lead.budget)}">${formatBudget(escapeHtml(lead.budget))}</span>
                    </div>
                    ${specLine}
                    ${extrasLine}
                </td>
                <td class="p-4 text-sm text-midnight/50">${escapeHtml(lead.timestamp)}</td>
                <td class="p-4 text-right">
                    <div class="flex justify-end gap-2 flex-wrap items-center">
                        <button onclick="togglePhone(this,'${lead.id}')"
                            class="inline-flex items-center gap-1.5 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                            <i data-lucide="phone" class="w-3 h-3"></i> Teléfono
                        </button>
                        ${lead.phone_format_valid == 1
                            ? `<span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest bg-emerald-50 text-emerald-700 inline-flex items-center gap-1">
                                <i data-lucide="check" class="w-3 h-3"></i> Formato Válido
                               </span>`
                            : ''
                        }
                        ${lead.phone_is_mobile
                            ? `<a href="/api/lead/${lead.id}/r/whatsapp"
                                 data-wa-link
                                 data-lead-id="${lead.id}"
                                 class="contact-btn contact-btn-whatsapp inline-flex items-center gap-1.5 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest transition-all"
                                 title="Abrir chat de WhatsApp con el usuario"
                                 aria-label="Abrir chat de WhatsApp">
                                 <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21l1.65-3.8a9 9 0 1 1 3.4 2.9L3 21"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 0 0 0-1 0v1Zm0 0a5 5 0 0 0 5 5m0 0a.5.5 0 0 0 0-1h-1a.5.5 0 0 0 0 1v1a.5.5 0 0 0 1 0v-1a.5.5 0 0 0-1 0Z"/><path d="M17 8a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2"/><path d="M12 12h.01"/></svg> WhatsApp
                               </a>`
                            : (lead.phone_format_valid == 1
                                ? `<a href="sms:${lead.phone_e164 || lead.phone}?&body=${encodeURIComponent('Hola, te contacto desde ArchEstate. Vi tu consulta y me interesa conversar.')}"
                                     data-sms-link
                                     data-lead-id="${lead.id}"
                                     class="contact-btn contact-btn-sms inline-flex items-center gap-1.5 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest transition-all"
                                     title="Enviar SMS al cliente (número no es WhatsApp)"
                                     aria-label="Enviar SMS">
                                     <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg> SMS
                                   </a>`
                                : '')
                        }
                        <a href="/profesional/lead/${lead.id}"
                            class="inline-flex items-center gap-1.5 px-3 py-2 bg-gold text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all">
                            <i data-lucide="arrow-right" class="w-3 h-3"></i> Ver más
                        </a>
                        <a href="/api/lead/${lead.id}/download"
                            class="inline-flex items-center gap-1.5 px-3 py-2 bg-paper-dark text-midnight rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold hover:text-white transition-all">
                            <i data-lucide="download" class="w-3 h-3"></i> PDF
                        </a>
                        <button type="button" onclick="openReportModal(${lead.id})"
                            class="inline-flex items-center gap-1.5 px-3 py-2 bg-paper-dark text-rose-600 rounded text-[10px] font-bold uppercase tracking-widest hover:bg-rose-600 hover:text-white transition-all"
                            title="Reportar telefono inexistente">
                            <i data-lucide="flag" class="w-3 h-3"></i>
                        </button>
                    </div>
                </td>
            </tr>`;
    }).join('');
    if (window.lucide) lucide.createIcons();
}

/**
 * Toggle estado de un lead (visto / contactado)
 */
async function toggleLeadStatus(leadId, statusType, btn) {
    if (btn.disabled) return;
    const isActive = btn.classList.contains('status-active');
    const label = btn.querySelector('span');
    const originalText = label ? label.textContent : '';
    const pendingText = isActive ? (statusType === 'seen' ? 'Ver' : 'Contactar') : (statusType === 'seen' ? 'Visto' : 'Contactado');

    btn.disabled = true;
    btn.classList.add('status-toggling');
    if (label) label.textContent = pendingText;

    try {
        const response = await fetch(`/api/lead/${leadId}/toggle-status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: statusType })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Confirmar estado desde servidor (coerce to number for safety)
            const serverValue = Number(data.value);
            if (serverValue === 1) {
                btn.classList.add('status-active');
            } else {
                btn.classList.remove('status-active');
            }
            btn.classList.remove('status-toggling');

            // Actualizar data attributes del row para filtrado
            const row = document.querySelector(`tr[data-lead-id="${leadId}"]`);
            if (row) {
                row.dataset[statusType] = serverValue === 1 ? 'true' : 'false';
            }
        } else {
            // Revertir en caso de error
            btn.classList.remove('status-active');
            btn.classList.remove('status-toggling');
            if (label) label.textContent = originalText;
            showToast(data.error || 'Error al actualizar estado', 'error');
        }
    } catch (error) {
        console.error('Error toggling lead status:', error);
        // Revertir en caso de error de red
        if (isActive) btn.classList.add('status-active');
        else btn.classList.remove('status-active');
        btn.classList.remove('status-toggling');
        if (label) label.textContent = isActive
            ? (statusType === 'seen' ? 'Visto' : 'Contactado')
            : (statusType === 'seen' ? 'Ver' : 'Contactar');
        showToast('Error de conexion', 'error');
    } finally {
        btn.disabled = false;
    }
}

function applyFilters() {
    currentFilters.search = document.getElementById('searchInput').value.trim();
    currentFilters.type   = document.getElementById('typeFilter').value;
    currentFilters.zone   = document.getElementById('zoneFilter').value.trim();
    loadLeads();
}

function clearFilters() {
    ['searchInput', 'zoneFilter'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('typeFilter').value  = '';
    document.getElementById('sortSelect').value  = 'timestamp';
    currentFilters = {
        search: '', type: '', property_type: '', zone: '',
        min_budget: '', max_budget: '', budget_range: '',
        currency: '', sort: 'timestamp', order: 'desc'
    };
    setPropType('');
    setBudgetRange('');
    const sortBtn = document.getElementById('sortOrder');
    if (sortBtn) { sortBtn.innerHTML = '<i data-lucide="arrow-down" class="w-3 h-3"></i>'; if (window.lucide) lucide.createIcons(); }
    loadLeads();
}

function updateSort() {
    currentFilters.sort = document.getElementById('sortSelect').value;
    loadLeads();
}

function toggleSortOrder() {
    currentFilters.order = currentFilters.order === 'desc' ? 'asc' : 'desc';
    const sortBtn = document.getElementById('sortOrder');
    if (sortBtn) {
        sortBtn.innerHTML = '<i data-lucide="' + (currentFilters.order === 'desc' ? 'arrow-down' : 'arrow-up') + '" class="w-3 h-3"></i>';
        if (window.lucide) lucide.createIcons();
    }
    loadLeads();
}

function showLeadError(msg) {
    document.getElementById('leadsTableBody').innerHTML = `
        <tr><td colspan="8" class="p-8 text-center text-rose-600">
            <i data-lucide="alert-circle" class="w-8 h-8 mx-auto mb-2"></i>
            <p>${msg}</p>
        </td></tr>`;
    if (window.lucide) lucide.createIcons();
}

/**
 * Modal de Reporte de Lead
 */
let currentReportLeadId = null;

function openReportModal(leadId) {
    currentReportLeadId = leadId;
    document.getElementById('reportLeadId').textContent = '#' + leadId;
    document.getElementById('reportNotes').value = '';
    document.getElementById('reportModal').classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeReportModal() {
    currentReportLeadId = null;
    document.getElementById('reportModal').classList.add('hidden');
}

async function confirmReport(e) {
    if (!currentReportLeadId) return;

    const notes = document.getElementById('reportNotes').value.trim();
    const btn = e ? e.target : document.getElementById('confirmReportBtn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Enviando...';

    try {
        const response = await fetch(`/api/lead/${currentReportLeadId}/report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast(data.message, 'success');
            closeReportModal();
        } else {
            showToast(data.error || 'Error al reportar', 'error');
        }
    } catch (error) {
        console.error('Error reporting lead:', error);
        showToast('Error de conexion', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/**
 * Refactor Fase D: el link es server-side (/r/whatsapp/<id>) y genera 302 a wa.me.
 * Esta función sólo emite eventos de telemetría (click/popup_blocked) y
 * muestra feedback si la redirección falla.
 */
function trackWhatsAppClick(link, e) {
    const leadId = link.dataset.leadId;
    fetch(`/api/lead/${leadId}/whatsapp-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: 'wa_button_clicked', props: { source: 'professional_table' } })
    }).catch(() => {});
}

function trackSmsClick(link) {
    const leadId = link.dataset.leadId;
    fetch(`/api/lead/${leadId}/whatsapp-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: 'sms_button_clicked', props: { source: 'professional_table' } })
    }).catch(() => {});
}

document.addEventListener('click', (e) => {
    const waLink = e.target.closest('[data-wa-link]');
    if (waLink) trackWhatsAppClick(waLink, e);
    const smsLink = e.target.closest('[data-sms-link]');
    if (smsLink) trackSmsClick(smsLink);
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeReportModal();
})};

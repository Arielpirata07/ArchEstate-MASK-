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
                <p class="text-sm font-semibold text-midnight/70 group-hover:text-midnight transition-colors">${t('upload.drag_here')}</p>
                <p class="text-[10px] text-midnight/60 mt-1 uppercase tracking-widest font-bold">${t('upload.or_click')}</p>
                <p class="text-[9px] text-midnight/30 mt-3 uppercase tracking-widest">${t('upload.max_size', {max: MAX_MB})}</p>
            </div>

            <!-- Preview del archivo seleccionado -->
            <div id="filePreview-${cid}" class="hidden">
                <div class="flex items-center gap-4 p-4 bg-paper-dark rounded-lg border border-midnight/10">
                    <div id="fileIcon-${cid}" class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-gold/10">
                        <i data-lucide="file" class="w-5 h-5 text-gold"></i>
                    </div>
                    <div class="flex-grow min-w-0">
                        <p id="fileName-${cid}" class="text-sm font-semibold text-midnight truncate"></p>
                        <p id="fileSize-${cid}" class="text-[10px] text-midnight/60 mt-0.5 uppercase tracking-widest font-bold"></p>
                    </div>
                    <button onclick="clearFile('${cid}')" class="p-2 text-midnight/30 hover:text-rose-500 transition-colors flex-shrink-0" title="${t('upload.remove_file')}">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>

            <!-- Barra de progreso -->
            <div id="progressWrapper-${cid}" class="hidden space-y-2">
                <div class="flex justify-between items-center">
                    <p class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">${t('upload.uploading')}</p>
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
                        <p class="text-[10px] font-bold uppercase tracking-widest text-emerald-700">${t('upload.doc_loaded')}</p>
                        <p id="docStatusName-${cid}" class="text-xs text-emerald-600 mt-0.5 truncate font-medium"></p>
                    </div>
                    <a href="${(document.getElementById('docApproved') || {}).dataset ? document.getElementById('docApproved').dataset.downloadUrl : '#'}"
                       class="flex-shrink-0 flex items-center gap-1 px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-[9px] font-bold uppercase tracking-widest hover:bg-emerald-200 transition-colors">
                        <i data-lucide="download" class="w-3 h-3"></i> ${t('action.download')}
                    </a>
                </div>
                <button onclick="replaceDoc('${cid}')"
                    class="w-full text-[10px] text-midnight/60 hover:text-gold transition-colors font-bold uppercase tracking-widest py-1 flex items-center justify-center gap-1">
                    <i data-lucide="refresh-cw" class="w-3 h-3"></i> ${t('upload.replace_doc')}
                </button>
            </div>

            <!-- Botón de envío -->
            <div id="submitWrapper-${cid}" class="hidden">
                <button id="uploadBtn-${cid}" onclick="uploadFile('${cid}')"
                    class="w-full py-3 bg-midnight text-white rounded font-bold uppercase tracking-widest text-[10px] hover:bg-gold transition-all flex items-center justify-center gap-2">
                    <i data-lucide="upload" class="w-4 h-4"></i>
                    ${t('upload.submit_docs')}
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
    if (nameEl) nameEl.textContent = name || t('upload.doc_loaded');

    // Actualizar paso 2 en el sidebar (solo estado pendiente)
    const icon  = document.getElementById('step2-icon');
    const label = document.getElementById('step2-label');
    const sub   = document.getElementById('step2-sub');
    if (icon) {
        icon.className = 'w-6 h-6 rounded-full bg-gold flex items-center justify-center flex-shrink-0 mt-0.5';
        icon.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-white"></i>';
        label.className   = 'text-white text-xs font-bold uppercase tracking-widest';
        label.textContent = t('upload.docs_sent');
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
        if (typeof showToast === 'function') showToast(t('error.file_type_not_allowed'), 'error');
        return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
        if (typeof showToast === 'function') showToast(t('error.file_too_large', {max: MAX_MB}), 'error');
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
            if (typeof showToast === 'function') showToast(data.error || t('error.upload_failed'), 'error');
        }
    } catch (err) {
        clearInterval(tick);
        document.getElementById(`progressWrapper-${cid}`).classList.add('hidden');
        document.getElementById(`dropzone-${cid}`).classList.remove('hidden');
        if (typeof showToast === 'function') showToast(t('error.upload_network'), 'error');
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
});

// ================================================================
// LEADS (solo si está aprobado)
// ================================================================

// ---- Labels legibles para los filtros activos ----
const PROP_LABELS = {
    departamento: t('property.department'), casa: t('property.house'), duplex: t('property.duplex'),
    penthouse: t('property.penthouse'), local_comercial: t('property.commercial'),
};
const BUDGET_LABELS = {
    hasta_200k: t('budget.up_to_200k'), '200k_500k': t('budget.200k_500k'),
    '500k_1m': t('budget.500k_1m'), '1m_2m': t('budget.1m_2m'), mas_2m: t('budget.over_2m'),
};

// ---- Íconos por tipo de propiedad ----
const PROP_ICONS = {
    departamento: 'building', casa: 'home', duplex: 'layers',
    penthouse: 'crown', local_comercial: 'store',
};

if (!IS_PENDING) {

document.addEventListener('DOMContentLoaded', () => {
    loadLeads().catch(function(){});
    try { setupLeadEventListeners(); } catch(e) { console.error('setupLeadEventListeners:', e); }
    // Show leads tab by default
    showProTab('leads');
});

var currentFilters = {
    search: '', type: '', property_type: '', zone: '',
    min_budget: '', max_budget: '', budget_range: '',
    currency: '', sort: 'timestamp', order: 'desc', my_leads: true,
    time_range: '', page: 1
};

function setMyLeads(myLeads) {
    currentFilters.my_leads = myLeads;
    currentFilters.page = 1;
    const btnMy = document.getElementById('btnMyLeads');
    const btnAll = document.getElementById('btnAllLeads');
    if (myLeads) {
        btnMy.className = 'px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-md transition-all bg-gold text-white';
        btnAll.className = 'px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-md transition-all text-midnight/50 hover:text-midnight';
    } else {
        btnMy.className = 'px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-md transition-all text-midnight/50 hover:text-midnight';
        btnAll.className = 'px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-md transition-all bg-gold text-white';
    }
    loadLeads();
}

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

    // Event delegation for status buttons (Ver / Contactar)
    document.getElementById('leadsTableBody').addEventListener('click', (e) => {
        const statusBtn = e.target.closest('.status-btn');
        if (statusBtn) {
            const leadId = parseInt(statusBtn.dataset.leadId, 10);
            const statusType = statusBtn.dataset.status;
            if (leadId && statusType) toggleLeadStatus(leadId, statusType, statusBtn);
            return;
        }
        // Event delegation for report button
        const reportBtn = e.target.closest('.report-lead-btn');
        if (reportBtn) {
            const leadId = parseInt(reportBtn.dataset.leadId, 10);
            if (leadId) openReportModal(leadId);
            return;
        }
        // Skip row-click for any click inside the action column
        if (e.target.closest('td:last-child')) return;
        // Event delegation for lead preview drawer (click row → open preview)
        const leadRow = e.target.closest('tr[data-lead-id]');
        if (leadRow) {
            const leadId = parseInt(leadRow.dataset.leadId, 10);
            if (leadId) {
                e.preventDefault();
                openLeadPreview(leadId);
            }
        }
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

// ---- Chips: Período de Tiempo ----
function setTimeRange(days) {
    currentFilters.time_range = days;
    document.querySelectorAll('.period-btn').forEach(function(btn) {
        var active = btn.dataset.days === days;
        btn.className = 'period-btn px-3 py-1 rounded text-[10px] font-bold uppercase tracking-widest transition-all '
            + (active
                ? 'bg-midnight text-white'
                : 'bg-paper-dark text-midnight hover:bg-gold hover:text-white');
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
    if (currentFilters.zone)          tags.push({ key: 'zone',         label: t('filter.zone_label', {zone: currentFilters.zone}) });
    if (currentFilters.budget_range)  tags.push({ key: 'budget_range', label: BUDGET_LABELS[currentFilters.budget_range] || currentFilters.budget_range });
    if (currentFilters.time_range) {
        var trLabels = {'1': t('time.today'), '7': t('time.7_days'), '30': t('time.30_days')};
        tags.push({ key: 'time_range', label: trLabels[currentFilters.time_range] || currentFilters.time_range + ' días' });
    }

    if (tags.length === 0) {
        container.innerHTML = '';
        countEl.classList.add('hidden');
        return;
    }

    countEl.textContent = `${tags.length} activo${tags.length > 1 ? 's' : ''}`;
    countEl.classList.remove('hidden');

    container.innerHTML = tags.map(tag => `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gold/10 text-gold border border-gold/20 rounded-full text-[9px] font-bold uppercase tracking-widest">
            ${escapeHtml(tag.label)}
            <button onclick="removeFilter('${tag.key}')" class="hover:text-rose-500 transition-colors">
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
    if (key === 'time_range') setTimeRange('');
    applyFilters();
}

// ---- Cargar y renderizar leads ----
async function loadLeads() {
    try {
        const params = new URLSearchParams();
        Object.entries(currentFilters).forEach(([k, v]) => {
            if (k === 'page') return;
            if (k === 'my_leads') {
                params.set('my_leads', v ? '1' : '0');
            } else if (k === 'time_range' && v) {
                params.set('time_range', v);
            } else if (v) {
                params.set(k, v);
            }
        });
        if (currentFilters.page > 1) params.set('page', String(currentFilters.page));
        params.set('per_page', '25');

        const tbody = document.getElementById('leadsTableBody');
        tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-midnight/60">
            <div class="flex justify-center items-center gap-2">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gold"></div>
                ${t('leads.searching')}
            </div></td></tr>`;

        const res  = await fetch(`/api/leads?${params}`);
        const data = await res.json();
        if (data.success) {
            window.__leadsData = data.leads;
            renderLeads(data.leads);
            renderLeadKpis(data.leads, { total: data.kpi_total, unseen: data.kpi_unseen, contacted: data.kpi_contacted });
            document.getElementById('leadsCount').textContent = data.total;
            renderPagination(data);
            renderActiveTags();
        } else {
            showLeadError(data.error || t('error.leads_load'));
        }
    } catch (err) {
        showLeadError(t('error.connection'));
    }
}

function goToPage(page) {
    currentFilters.page = page;
    loadLeads();
}

function renderPagination(data) {
    const container = document.getElementById('paginationControls');
    if (!container) return;
    const { page, total_pages, total } = data;
    if (total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    let html = '<div class="flex items-center justify-center gap-2 mt-4">';
    html += `<button onclick="goToPage(${page - 1})" class="px-3 py-1.5 text-[10px] font-bold rounded border border-midnight/20 ${page <= 1 ? 'text-midnight/20 cursor-not-allowed' : 'text-midnight/60 hover:border-gold hover:text-gold'}" ${page <= 1 ? 'disabled' : ''}>${t('pagination.prev') || '‹ Anterior'}</button>`;
    for (let p = 1; p <= total_pages; p++) {
        if (p === page) {
            html += `<span class="px-3 py-1.5 text-[10px] font-bold rounded bg-gold text-white">${p}</span>`;
        } else if (p === 1 || p === total_pages || Math.abs(p - page) <= 2) {
            html += `<button onclick="goToPage(${p})" class="px-3 py-1.5 text-[10px] font-bold rounded text-midnight/60 hover:text-gold">${p}</button>`;
        } else if (p === page - 3 || p === page + 3) {
            html += `<span class="px-1 text-midnight/30">…</span>`;
        }
    }
    html += `<button onclick="goToPage(${page + 1})" class="px-3 py-1.5 text-[10px] font-bold rounded border border-midnight/20 ${page >= total_pages ? 'text-midnight/20 cursor-not-allowed' : 'text-midnight/60 hover:border-gold hover:text-gold'}" ${page >= total_pages ? 'disabled' : ''}>${t('pagination.next') || 'Siguiente ›'}</button>`;
    html += '</div>';
    container.innerHTML = html;
}

function formatBudget(value) {
    if (!value) return '0';
    const cleaned = String(value).replace(/[^\d.,]/g, '');
    if (!cleaned) return value;
    const num = parseFloat(cleaned.replace(/,/g, ''));
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
                <p class="font-semibold text-midnight/60">${t('leads.no_results')}</p>
                <p class="text-xs text-midnight/30 mt-1">${t('leads.no_results_hint')}</p>
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
        if (lead.ambientes)          specs.push(`${lead.ambientes} ${t('spec.rooms')}`);
        if (lead.bedrooms)           specs.push(`${lead.bedrooms} ${t('spec.bedrooms')}`);
        if (lead.bathrooms)          specs.push(`${lead.bathrooms} ${t('spec.bathrooms')}`);
        if (lead.usable_m2 > 0)      specs.push(`${lead.usable_m2} m²`);
        if (lead.land_area > 0)      specs.push(`${lead.land_area} ${t('spec.land_m2')}`);

        const specLine = specs.length
            ? `<div class="text-[9px] text-midnight/60 font-bold uppercase tracking-widest mt-0.5">${specs.join(' · ')}</div>`
            : '';

        // Badges extra
        const parkingLabels = { sin_cochera: t('parking.none'), simple_cubierta: t('parking.single'), doble_cubierta: t('parking.double'), descubierta: t('parking.open'), garage: t('parking.garage') };
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

        var unseenClass = tracking.seen ? '' : ' lead-row-unseen';
        return `
            <tr class="border-b border-midnight/[0.03] hover:bg-paper transition-colors group cursor-pointer${unseenClass}" data-lead-id="${lead.id}" data-seen="${tracking.seen}" data-contacted="${tracking.contacted}">
                <td class="px-4 py-3 font-mono text-[11px] text-midnight/60">${lead.id}</td>
                <td class="px-4 py-3">
                    <div class="flex flex-col gap-1.5">
                        <button type="button" class="status-btn status-btn-seen ${tracking.seen ? 'status-active' : ''}"
                                data-status="seen"
                                data-lead-id="${lead.id}">
                            <i data-lucide="eye" class="w-3 h-3"></i>
                            <span>${tracking.seen ? t('status.seen') : t('action.view')}</span>
                        </button>
                        <button type="button" class="status-btn status-btn-contacted ${tracking.contacted ? 'status-active' : ''}"
                                data-status="contacted"
                                data-lead-id="${lead.id}">
                            <i data-lucide="message-circle" class="w-3 h-3"></i>
                            <span>${tracking.contacted ? t('status.contacted') : t('action.contact')}</span>
                        </button>
                    </div>
                </td>
                <td class="px-4 py-3 text-[13px] text-midnight/50 font-medium">${escapeHtml(lead.type)}</td>
                <td class="px-4 py-3">${propBadge}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${escapeHtml(lead.zone)}</td>
                <td class="px-4 py-3">
                    <div class="budget-display">
                        <span class="budget-currency-tag">${sym}</span>
                        <span class="budget-amount" title="${escapeHtml(lead.budget)}">${formatBudget(escapeHtml(lead.budget))}</span>
                    </div>
                    ${specLine}
                    ${extrasLine}
                </td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${escapeHtml(lead.timestamp)}</td>
                <td class="px-4 py-3 text-right">
                    <div class="flex flex-col items-end gap-1">
                        <div class="flex justify-end gap-1.5 items-center">
                            <button onclick="togglePhone(this,'${lead.id}')"
                                class="inline-flex items-center gap-1.5 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                                <i data-lucide="phone" class="w-3 h-3"></i> ${t('action.phone')}
                            </button>
                            ${lead.phone_is_mobile
                                ? `<a href="/api/lead/${lead.id}/r/whatsapp"
                                     data-wa-link
                                     data-lead-id="${lead.id}"
                                     class="contact-btn contact-btn-whatsapp inline-flex items-center gap-1.5 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest transition-all"
                                     title="${t('action.open_whatsapp')}"
                                     aria-label="${t('action.open_whatsapp')}">
                                     <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21l1.65-3.8a9 9 0 1 1 3.4 2.9L3 21"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 0 0 0-1 0v1Zm0 0a5 5 0 0 0 5 5m0 0a.5.5 0 0 0 0-1h-1a.5.5 0 0 0 0 1v1a.5.5 0 0 0 1 0v-1a.5.5 0 0 0-1 0Z"/><path d="M17 8a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2"/><path d="M12 12h.01"/></svg> WhatsApp
                                   </a>`
                                : (lead.phone_format_valid == 1
                                    ? `<a href="sms:${lead.phone_e164 || lead.phone}?&body=${encodeURIComponent('Hola, te contacto desde ArchEstate.')}"
                                         data-sms-link
                                         data-lead-id="${lead.id}"
                                         class="contact-btn contact-btn-sms inline-flex items-center gap-1.5 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest transition-all"
                                         title="${t('action.send_sms')}"
                                         aria-label="${t('action.send_sms')}">
                                         <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg> SMS
                                       </a>`
                                    : '')
                            }
                        </div>
                        <div class="flex justify-end gap-1.5 items-center flex-wrap">
                            <a href="/profesional/lead/${lead.id}"
                                class="inline-flex items-center gap-1.5 px-3 py-2 bg-gold text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all">
                                <i data-lucide="arrow-right" class="w-3 h-3"></i> ${t('action.view_more')}
                            </a>
                            <a href="/api/lead/${lead.id}/download"
                                class="inline-flex items-center gap-1 px-2.5 py-1.5 bg-paper-dark text-midnight rounded text-[9px] font-bold uppercase tracking-widest hover:bg-midnight hover:text-white transition-all">
                                <i data-lucide="download" class="w-3 h-3"></i> PDF
                            </a>
                            <button type="button" class="report-lead-btn inline-flex items-center gap-1 px-2.5 py-1.5 bg-rose-50 text-rose-600 rounded text-[9px] font-bold uppercase tracking-widest hover:bg-rose-600 hover:text-white transition-all"
                                data-lead-id="${lead.id}"
                                title="${t('action.report_phone')}">
                                <i data-lucide="flag" class="w-3 h-3"></i> ${t('action.report')}
                            </button>
                            ${lead.phone_format_valid == 1
                                ? '<span class="inline-flex items-center gap-1 px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest bg-emerald-50 text-emerald-700"><i data-lucide="check" class="w-3 h-3"></i> OK</span>'
                                : ''
                            }
                        </div>
                    </div>
                </td>
            </tr>`;
    }).join('');
    initTableStagger(tbody);
    if (window.lucide) lucide.createIcons();
}

function applyFilters() {
    currentFilters.search = document.getElementById('searchInput').value.trim();
    currentFilters.type   = document.getElementById('typeFilter').value;
    currentFilters.zone   = document.getElementById('zoneFilter').value.trim();
    currentFilters.page = 1;
    loadLeads();
}

function clearFilters() {
    ['searchInput', 'zoneFilter'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('typeFilter').value  = '';
    document.getElementById('sortSelect').value  = 'timestamp';
    currentFilters = {
        search: '', type: '', property_type: '', zone: '',
        min_budget: '', max_budget: '', budget_range: '',
        currency: '', sort: 'timestamp', order: 'desc',
        my_leads: currentFilters.my_leads, time_range: '', page: 1
    };
    setPropType('');
    setBudgetRange('');
    setTimeRange('');
    const sortBtn = document.getElementById('sortOrder');
    if (sortBtn) { sortBtn.innerHTML = '<i data-lucide="arrow-down" class="w-3 h-3"></i>'; if (window.lucide) lucide.createIcons(); }
    loadLeads();
}

function updateSort() {
    currentFilters.sort = document.getElementById('sortSelect').value;
    currentFilters.page = 1;
    loadLeads();
}

function toggleSortOrder() {
    currentFilters.order = currentFilters.order === 'desc' ? 'asc' : 'desc';
    currentFilters.page = 1;
    const sortBtn = document.getElementById('sortOrder');
    if (sortBtn) {
        sortBtn.innerHTML = '<i data-lucide="' + (currentFilters.order === 'desc' ? 'arrow-down' : 'arrow-up') + '" class="w-3 h-3"></i>';
        if (window.lucide) lucide.createIcons();
    }
    loadLeads();
}

function showLeadError(msg) {
    var safeMsg = msg;
    if (typeof escapeHtml === 'function') safeMsg = escapeHtml(msg);
    document.getElementById('leadsTableBody').innerHTML = `
        <tr><td colspan="8" class="p-8 text-center text-rose-600">
            <i data-lucide="alert-circle" class="w-8 h-8 mx-auto mb-2"></i>
            <p>${safeMsg}</p>
        </td></tr>`;
    if (window.lucide) lucide.createIcons();
}

} // end if (!IS_PENDING)

/**
 * Toggle estado de un lead (visto / contactado)
 */
async function toggleLeadStatus(leadId, statusType, btn) {
    if (btn.disabled) return;
    const isActive = btn.classList.contains('status-active');
    const label = btn.querySelector('span');
    const originalText = label ? label.textContent : '';
    const pendingText = isActive ? (statusType === 'seen' ? t('action.view') : t('action.contact')) : (statusType === 'seen' ? t('status.seen') : t('status.contacted'));

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

            // Actualizar tracking local y refrescar KPIs
            const leads = window.__leadsData || [];
            for (var i = 0; i < leads.length; i++) {
                if (leads[i].id === leadId) {
                    if (!leads[i].tracking) leads[i].tracking = {};
                    leads[i].tracking[statusType] = serverValue === 1;
                    break;
                }
            }
            renderLeadKpis(leads);
        } else {
            // Revertir en caso de error
            btn.classList.remove('status-active');
            btn.classList.remove('status-toggling');
            if (label) label.textContent = originalText;
            if (typeof showToast === 'function') showToast(data.error || t('error.generic'), 'error');
        }
    } catch (error) {
        console.error('Error toggling lead status:', error);
        // Revertir en caso de error de red
        if (isActive) btn.classList.add('status-active');
        else btn.classList.remove('status-active');
        btn.classList.remove('status-toggling');
        if (label) label.textContent = isActive
            ? (statusType === 'seen' ? t('status.seen') : t('status.contacted'))
            : (statusType === 'seen' ? t('action.view') : t('action.contact'));
        if (typeof showToast === 'function') showToast(t('error.connection'), 'error');
    } finally {
        btn.disabled = false;
    }
}

// ================================================================
// LEAD KPI BAR (leads tab header)
// ================================================================
function renderLeadKpis(leads, aggregates) {
    var total, unseen, contacted;
    if (aggregates) {
        total = aggregates.total;
        unseen = aggregates.unseen;
        contacted = aggregates.contacted;
    } else {
        total = leads.length;
        unseen = 0; contacted = 0;
        for (var i = 0; i < leads.length; i++) {
            var trk = leads[i].tracking;
            if (trk) {
                if (!trk.seen) unseen++;
                if (trk.contacted) contacted++;
            } else {
                unseen++;
            }
        }
    }
    var seen = total - unseen;
    var contactRate = seen > 0 ? Math.round((contacted / seen) * 100) : 0;

    var el = document.getElementById('kpiLeadsTotal');
    if (el) {
        if (total === 0) { el.textContent = '\u2014'; }
        else { el.textContent = '0'; setTimeout(function() { if (typeof animateCounter === 'function') animateCounter(el, total); else el.textContent = total; }, 50); }
    }
    el = document.getElementById('kpiLeadsUnseen');
    if (el) {
        if (total === 0) { el.textContent = '\u2014'; }
        else { el.textContent = '0'; setTimeout(function() { if (typeof animateCounter === 'function') animateCounter(el, unseen); else el.textContent = unseen; }, 50); }
    }
    el = document.getElementById('kpiLeadsContacted');
    if (el) {
        if (total === 0) { el.textContent = '\u2014'; }
        else { el.textContent = '0'; setTimeout(function() { if (typeof animateCounter === 'function') animateCounter(el, contacted); else el.textContent = contacted; }, 50); }
    }
    el = document.getElementById('kpiLeadsContactRate');
    if (el) { el.textContent = total === 0 ? '\u2014' : contactRate + '%'; }
}

// ================================================================
// LEAD PREVIEW DRAWER
// ================================================================
function openLeadPreview(leadId) {
    var leads = window.__leadsData || [];
    var lead = null;
    for (var i = 0; i < leads.length; i++) {
        if (leads[i].id === leadId) { lead = leads[i]; break; }
    }
    if (!lead) return;

    var overlay = document.getElementById('leadPreviewOverlay');
    var drawer = document.getElementById('leadPreviewDrawer');
    if (!overlay || !drawer) return;

    document.getElementById('previewLeadId').textContent = '#' + lead.id;
    document.getElementById('previewLeadTitle').textContent = (lead.type || t('leads.no_type')) + ' en ' + (lead.zone || '—');

    var sym = lead.currency === 'USD' ? 'US$' : lead.currency === 'EUR' ? '\u20ac' : '$';
    var propType = (lead.property_type || '').toLowerCase();
    var propLabel = PROP_LABELS[propType] || lead.property_type || '—';

    var specs = [];
    if (lead.ambientes) specs.push(lead.ambientes + ' ' + t('spec.rooms'));
    if (lead.bedrooms) specs.push(lead.bedrooms + ' ' + t('spec.bedrooms'));
    if (lead.bathrooms) specs.push(lead.bathrooms + ' ' + t('spec.bathrooms'));
    if (lead.usable_m2 > 0) specs.push(lead.usable_m2 + ' m\u00b2');

    var tracking = lead.tracking || { seen: false, contacted: false };

    var html = '';

    // Info grid
    html += '<div class="grid grid-cols-2 gap-3">';
    html += '<div class="bg-paper-dark rounded-lg p-3"><p class="text-[8px] uppercase tracking-widest font-bold text-midnight/60 mb-1">' + t('preview.operation') + '</p><p class="text-[13px] font-medium text-midnight">' + escapeHtml(lead.type) + '</p></div>';
    html += '<div class="bg-paper-dark rounded-lg p-3"><p class="text-[8px] uppercase tracking-widest font-bold text-midnight/60 mb-1">' + t('preview.housing') + '</p><p class="text-[13px] font-medium text-midnight">' + propLabel + '</p></div>';
    html += '<div class="bg-paper-dark rounded-lg p-3"><p class="text-[8px] uppercase tracking-widest font-bold text-midnight/60 mb-1">' + t('preview.zone') + '</p><p class="text-[13px] font-medium text-midnight">' + escapeHtml(lead.zone) + '</p></div>';
    html += '<div class="bg-paper-dark rounded-lg p-3"><p class="text-[8px] uppercase tracking-widest font-bold text-midnight/60 mb-1">' + t('preview.budget') + '</p><p class="text-[13px] font-medium text-midnight">' + sym + ' ' + escapeHtml(lead.budget) + '</p></div>';
    html += '</div>';

    // Specs
    if (specs.length) {
        html += '<div class="bg-paper-dark rounded-lg p-3"><p class="text-[8px] uppercase tracking-widest font-bold text-midnight/60 mb-1">' + t('preview.specifications') + '</p><p class="text-xs text-midnight/70">' + specs.join(' \u00b7 ') + '</p></div>';
    }

    // Status buttons
    html += '<div class="flex gap-2">';
    html += '<button type="button" class="status-btn status-btn-seen ' + (tracking.seen ? 'status-active' : '') + '" data-status="seen" data-lead-id="' + lead.id + '" onclick="event.stopPropagation(); toggleLeadStatus(' + lead.id + ', \'seen\', this)"><i data-lucide="eye" class="w-3 h-3"></i><span>' + (tracking.seen ? t('status.seen') : t('action.view')) + '</span></button>';
    html += '<button type="button" class="status-btn status-btn-contacted ' + (tracking.contacted ? 'status-active' : '') + '" data-status="contacted" data-lead-id="' + lead.id + '" onclick="event.stopPropagation(); toggleLeadStatus(' + lead.id + ', \'contacted\', this)"><i data-lucide="message-circle" class="w-3 h-3"></i><span>' + (tracking.contacted ? t('status.contacted') : t('action.contact')) + '</span></button>';
    html += '</div>';

    // Phone + contact
    html += '<div class="flex flex-wrap gap-2">';
    html += '<button onclick="event.stopPropagation(); togglePhone(this,\'' + lead.id + '\')" class="inline-flex items-center gap-1.5 px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all"><i data-lucide="phone" class="w-3 h-3"></i> ' + t('action.phone') + '</button>';
    if (lead.phone_is_mobile) {
        html += '<a href="/api/lead/' + lead.id + '/r/whatsapp" data-wa-link data-lead-id="' + lead.id + '" class="contact-btn contact-btn-whatsapp inline-flex items-center gap-1.5 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21l1.65-3.8a9 9 0 1 1 3.4 2.9L3 21"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 0 0 0-1 0v1Zm0 0a5 5 0 0 0 5 5m0 0a.5.5 0 0 0 0-1h-1a.5.5 0 0 0 0 1v1a.5.5 0 0 0 1 0v-1a.5.5 0 0 0-1 0Z"/><path d="M17 8a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2"/><path d="M12 12h.01"/></svg> WhatsApp</a>';
    } else if (lead.phone_format_valid == 1) {
        html += '<a href="sms:' + (lead.phone_e164 || lead.phone) + '?&body=' + encodeURIComponent('Hola, te contacto desde ArchEstate. Vi tu consulta y me interesa conversar.') + '" data-sms-link data-lead-id="' + lead.id + '" class="contact-btn contact-btn-sms inline-flex items-center gap-1.5 px-3 py-2 rounded text-[10px] font-bold uppercase tracking-widest"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg> SMS</a>';
    }
    html += '</div>';

    // Ver más
    html += '<a href="/profesional/lead/' + lead.id + '" class="block w-full text-center px-4 py-3 bg-gold text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all"><i data-lucide="arrow-right" class="w-3 h-3 inline mr-1"></i> ' + t('action.view_full_details') + '</a>';

    document.getElementById('previewLeadContent').innerHTML = html;

    overlay.classList.remove('hidden', 'pointer-events-none');
    drawer.classList.remove('hidden');
    requestAnimationFrame(function() {
        overlay.classList.remove('opacity-0');
        drawer.classList.remove('translate-x-full');
    });

    if (window.lucide) lucide.createIcons();
}

function closeLeadPreview() {
    var overlay = document.getElementById('leadPreviewOverlay');
    var drawer = document.getElementById('leadPreviewDrawer');
    if (!overlay || !drawer) return;

    overlay.classList.add('opacity-0');
    drawer.classList.add('translate-x-full');
    setTimeout(function() {
        overlay.classList.add('hidden', 'pointer-events-none');
        drawer.classList.add('hidden');
    }, 300);
}

// ================================================================
// MODAL REPORTE — funciones globales (fuera de if(!IS_PENDING))
// ================================================================
let currentReportLeadId = null;

function openReportModal(leadId) {
    currentReportLeadId = leadId;
    document.getElementById('reportLeadId').textContent = '#' + leadId;
    document.getElementById('reportNotes').value = '';
    openModalAnim(document.getElementById('reportModal'));
    if (window.lucide) lucide.createIcons();
}

function closeReportModal() {
    currentReportLeadId = null;
    closeModalAnim(document.getElementById('reportModal'));
}

document.addEventListener('click', function(e) {
    const btn = e.target.closest('#confirmReportBtn');
    if (btn) {
        e.preventDefault();
        confirmReport(btn);
        return;
    }
    const cancelBtn = e.target.closest('#reportModal [data-close-report]');
    if (cancelBtn) {
        closeReportModal();
        return;
    }
    const backdrop = e.target.closest('#reportModal > .absolute');
    if (backdrop) {
        closeReportModal();
        return;
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLeadPreview();
        closeReportModal();
    }
});

async function confirmReport(btn) {
    if (!currentReportLeadId) return;

    const notes = document.getElementById('reportNotes').value.trim();
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = t('action.sending');

    try {
        const response = await fetch('/api/lead/' + currentReportLeadId + '/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            if (typeof showToast === 'function') showToast(data.message, 'success');
            closeReportModal();
        } else {
            if (typeof showToast === 'function') showToast(data.error || t('error.report'), 'error');
        }
    } catch (error) {
        console.error('Error reporting lead:', error);
        if (typeof showToast === 'function') showToast(t('error.connection'), 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function trackWhatsAppClick(link, e) {
    const leadId = link.dataset.leadId;
    fetch('/api/lead/' + leadId + '/whatsapp-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: 'wa_button_clicked', props: { source: 'professional_table' } })
    }).catch(function() {});
}

function trackSmsClick(link) {
    const leadId = link.dataset.leadId;
    fetch('/api/lead/' + leadId + '/whatsapp-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: 'sms_button_clicked', props: { source: 'professional_table' } })
    }).catch(function() {});
}

document.addEventListener('click', function(e) {
    const waLink = e.target.closest('[data-wa-link]');
    if (waLink) trackWhatsAppClick(waLink, e);
    const smsLink = e.target.closest('[data-sms-link]');
    if (smsLink) trackSmsClick(smsLink);
    const telLink = e.target.closest('[data-tel-link]');
    if (telLink) {
        const leadId = telLink.dataset.leadId;
        fetch('/api/lead/' + leadId + '/whatsapp-event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event: 'tel_clicked' })
        }).catch(function() {});
    }
});

// ================================================================
// MARKET STATISTICS
// ================================================================
function isDarkMode() {
    return document.documentElement.classList.contains('dark');
}

function getPalette() {
    if (isDarkMode()) {
        return {
            gold:  ['#A68A64', '#C4A882', '#D4BC9A', '#E8D5B7', '#F0E6D0'],
            dark:  ['#243E62', '#2E4E7A', '#3A5F96', '#4A70A8', '#5A82BA'],
            mixed: ['#A68A64', '#243E62', '#C4A882', '#2E4E7A', '#D4BC9A', '#3A5F96'],
        };
    }
    return {
        gold:  ['#735A3A', '#A68A64', '#C4A882', '#D4BC9A', '#E8D5B7'],
        dark:  ['#000410', '#101E33', '#1A2E4A', '#243E62', '#2E4E7A'],
        mixed: ['#735A3A', '#000410', '#A68A64', '#101E33', '#C4A882', '#1A2E4A'],
    };
}

function chartGridColor() {
    return isDarkMode() ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)';
}

const baseFont = { family: 'Manrope', size: 10, weight: 'bold' };
const statsCharts = {};

function destroyStatsChart(key) {
    if (statsCharts[key]) { statsCharts[key].destroy(); delete statsCharts[key]; }
}

function formatMonthLabel(ym) {
    if (!ym) return '';
    const [y, m] = ym.split('-');
    const months = [t('month.january'), t('month.february'), t('month.march'), t('month.april'), t('month.may'), t('month.june'),
                    t('month.july'), t('month.august'), t('month.september'), t('month.october'), t('month.november'), t('month.december')];
    const idx = parseInt(m, 10) - 1;
    return months[idx] + ' ' + y;
}

function populateMonthSelect() {
    const sel = document.getElementById('statsMonthSelect');
    if (!sel) return;
    const now = new Date();
    const current = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
    sel.innerHTML = '';
    for (let i = 5; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const val = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = formatMonthLabel(val);
        if (val === current) opt.selected = true;
        sel.appendChild(opt);
    }
}

function showProTab(tab) {
    const panelLeads = document.getElementById('panel-leads');
    const panelStats = document.getElementById('panel-stats');
    const tabLeads = document.getElementById('tab-leads');
    const tabStats = document.getElementById('tab-stats');
    const exportCsv = document.getElementById('exportCsvBtn');
    const exportXlsx = document.getElementById('exportXlsxBtn');
    if (!panelLeads || !panelStats || !tabLeads || !tabStats) return;

    const activeClass = 'tab-btn px-4 py-2 text-[10px] font-bold uppercase tracking-widest rounded transition-all bg-midnight text-white';
    const inactiveClass = 'tab-btn px-4 py-2 text-[10px] font-bold uppercase tracking-widest rounded transition-all bg-paper-dark text-midnight hover:bg-gold hover:text-white';

    if (tab === 'stats') {
        panelLeads.classList.add('hidden');
        panelStats.classList.remove('hidden');
        panelStats.classList.remove('panel-enter');
        void panelStats.offsetWidth;
        panelStats.classList.add('panel-enter');
        tabLeads.className = inactiveClass;
        tabStats.className = activeClass;
        if (exportCsv) exportCsv.href = exportCsv.dataset.statsHref;
        if (exportXlsx) exportXlsx.href = exportXlsx.dataset.statsHref;
        populateMonthSelect();
        loadMarketStats();
    } else {
        panelStats.classList.add('hidden');
        panelLeads.classList.remove('hidden');
        panelLeads.classList.remove('panel-enter');
        void panelLeads.offsetWidth;
        panelLeads.classList.add('panel-enter');
        tabStats.className = inactiveClass;
        tabLeads.className = activeClass;
        if (exportCsv) exportCsv.href = exportCsv.dataset.leadsHref;
        if (exportXlsx) exportXlsx.href = exportXlsx.dataset.leadsHref;
    }
}

async function loadMarketStats(tryAutoSelect) {
    const sel = document.getElementById('statsMonthSelect');
    if (!sel) return;
    let month = sel.value;
    if (!month) return;

    const monthLabel = document.getElementById('statsMonthLabel');
    if (monthLabel) monthLabel.textContent = formatMonthLabel(month);

    const params = new URLSearchParams();
    params.set('month', month);
    params.set('my_leads', currentFilters.my_leads ? '1' : '0');

    try {
        const res = await fetch('/api/leads/stats?' + params.toString());
        const data = await res.json();
        if (data.success) {
            if (data.stats.total === 0 && tryAutoSelect !== false) {
                const options = Array.from(sel.options);
                for (let i = 0; i < options.length; i++) {
                    const opt = options[i];
                    if (opt.value === month) continue;
                    const p = new URLSearchParams();
                    p.set('month', opt.value);
                    p.set('my_leads', currentFilters.my_leads ? '1' : '0');
                    const r = await fetch('/api/leads/stats?' + p.toString());
                    const d = await r.json();
                    if (d.success && d.stats.total > 0) {
                        sel.value = opt.value;
                        if (monthLabel) monthLabel.textContent = formatMonthLabel(opt.value);
                        renderStatsSection(d.stats);
                        return;
                    }
                }
            }
            renderStatsSection(data.stats);
        } else {
            showToast(data.message || t('error.stats_load'), 'error');
        }
    } catch (err) {
        console.error('Error loading market stats:', err);
        showToast(t('error.stats_network'), 'error');
    }
}

function renderStatsSection(stats) {
    const emptyState = document.getElementById('statsEmptyState');
    const content = document.getElementById('statsContent');
    const isEmpty = !stats.total;

    if (emptyState) emptyState.classList.toggle('hidden', !isEmpty);
    if (content) content.classList.toggle('hidden', isEmpty);

    if (isEmpty) {
        if (window.lucide) lucide.createIcons();
        return;
    }

    renderStatsKpis(stats);
    renderStatsCharts(stats);
    renderTopSearched(stats);
    triggerStatsEntrance();
}

function triggerStatsEntrance() {
    var els = document.querySelectorAll('.stats-entrance');
    els.forEach(function(el, i) {
        el.classList.remove('stats-entrance-in');
        void el.offsetWidth;
        el.style.setProperty('--stagger-order', i);
        el.classList.add('stats-entrance-in');
    });
}

function formatCurrency(value) {
    if (!value || value === 0) return '$0';
    const num = Number(value);
    if (num >= 1000000) return '$' + (num / 1000000).toFixed(1).replace('.0', '') + 'M';
    if (num >= 1000) return '$' + (num / 1000).toFixed(0) + 'k';
    return '$' + num.toLocaleString('es-AR');
}

function renderStatsKpis(stats) {
    const totalEl = document.getElementById('kpiTotal');
    const prevEl = document.getElementById('kpiPrevTotal');
    const prevLabelEl = document.getElementById('kpiPrevLabel');
    const growthEl = document.getElementById('kpiTotalGrowth');
    const budgetEl = document.getElementById('kpiAvgBudget');
    const zonesEl = document.getElementById('kpiZones');

    if (totalEl) {
        totalEl.textContent = stats.total;
        animateCounter(totalEl, stats.total);
    }

    const prevTotal = stats.previous_month ? stats.previous_month.total : 0;
    if (prevEl) {
        prevEl.textContent = prevTotal;
        animateCounter(prevEl, prevTotal);
    }
    if (prevLabelEl) {
        const sel = document.getElementById('statsMonthSelect');
        const opts = sel ? sel.options : [];
        const idx = sel ? sel.selectedIndex : 0;
        const prevIdx = idx > 0 ? idx - 1 : 0;
        prevLabelEl.textContent = opts[prevIdx] ? 'vs ' + opts[prevIdx].textContent : '';
    }

    if (growthEl) {
        const diff = stats.total - prevTotal;
        if (prevTotal > 0) {
            const pct = ((diff / prevTotal) * 100).toFixed(1);
            growthEl.className = 'text-[10px] font-bold mt-1 ' + (diff >= 0 ? 'text-emerald-600' : 'text-rose-600');
            growthEl.textContent = (diff >= 0 ? '+' : '') + diff + ' (' + (diff >= 0 ? '+' : '') + pct + '%)';
            growthEl.classList.remove('hidden');
        } else if (stats.total > 0) {
            growthEl.className = 'text-[10px] font-bold mt-1 text-emerald-600';
            growthEl.textContent = t('stats.new_this_month');
            growthEl.classList.remove('hidden');
        } else {
            growthEl.classList.add('hidden');
        }
    }

    if (budgetEl) {
        const val = stats.avg_budget || 0;
        budgetEl.textContent = formatCurrency(val);
    }

    if (zonesEl) {
        zonesEl.textContent = stats.active_zones || 0;
        animateCounter(zonesEl, stats.active_zones || 0);
    }
}

function renderStatsCharts(stats) {
    if (typeof Chart === 'undefined') return;

    const palette = getPalette();
    const isDark = isDarkMode();

    const tooltipOpts = {
        backgroundColor: isDark ? '#1a2332' : '#fff',
        titleFont: { family: 'Manrope', size: 11, weight: 'bold' },
        titleColor: isDark ? '#FAF9F7' : '#000410',
        bodyFont: { family: 'Manrope', size: 10 },
        bodyColor: isDark ? '#C4A882' : '#735A3A',
        borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,4,16,0.08)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
    };

    // 1. Property Type (doughnut)
    destroyStatsChart('propType');
    const ptData = stats.by_property_type || [];
    if (ptData.length && document.getElementById('chart-prop-type')) {
        const ptLabels = ptData.map(function(d) { return d.label || t('chart.no_type'); });
        const ptValues = ptData.map(function(d) { return d.value; });
        statsCharts['propType'] = new Chart(document.getElementById('chart-prop-type'), {
            type: 'doughnut',
            data: {
                labels: ptLabels,
                datasets: [{
                    data: ptValues,
                    backgroundColor: palette.gold,
                    borderWidth: 0,
                    hoverOffset: 10,
                    hoverBorderWidth: 2,
                    hoverBorderColor: palette.dark[0],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: { display: true, position: 'bottom', labels: { font: baseFont, boxWidth: 14, padding: 14, usePointStyle: true, pointStyle: 'circle' } },
                    tooltip: Object.assign({}, tooltipOpts, {
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce(function(a, b) { return a + b; }, 0);
                                const pct = total ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return '  ' + ctx.label + ': ' + ctx.parsed.toLocaleString('es-AR') + ' (' + pct + '%)';
                            }
                        }
                    })
                },
                animation: chartAnim()
            }
        });
    }

    // 2. Zones (horizontal bar)
    destroyStatsChart('zones');
    const zData = stats.by_zone || [];
    if (zData.length && document.getElementById('chart-zones')) {
        const zLabels = zData.map(function(d) { return d.label || t('chart.no_zone'); }).reverse();
        const zValues = zData.map(function(d) { return d.value; }).reverse();
        statsCharts['zones'] = new Chart(document.getElementById('chart-zones'), {
            type: 'bar',
            data: {
                labels: zLabels,
                datasets: [{
                    data: zValues,
                    backgroundColor: palette.dark,
                    borderWidth: 0,
                    borderRadius: 4,
                    borderSkipped: false,
                    hoverBackgroundColor: palette.gold,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: Object.assign({}, tooltipOpts, {
                        padding: 8,
                        cornerRadius: 6,
                        callbacks: {
                            label: function(ctx) { return '  ' + ctx.parsed.x.toLocaleString('es-AR') + ' leads'; }
                        }
                    })
                },
                scales: {
                    x: {
                        ticks: { font: baseFont, stepSize: 1, callback: function(v) { return v.toLocaleString('es-AR'); } },
                        grid: { color: chartGridColor() },
                        beginAtZero: true
                    },
                    y: { ticks: { font: { family: 'Manrope', size: 9 } }, grid: { display: false } }
                },
                animation: chartAnim()
            }
        });
    }

    // 3. Trend (line)
    destroyStatsChart('trend');
    const tData = stats.trend || [];
    if (tData.length && document.getElementById('chart-trend')) {
        const tLabels = tData.map(function(d) {
            var parts = d.label.split('-');
            return new Date(parts[0], parseInt(parts[1], 10) - 1).toLocaleString('es', { month: 'short', year: '2-digit' });
        });
        const tValues = tData.map(function(d) { return d.value; });
        statsCharts['trend'] = new Chart(document.getElementById('chart-trend'), {
            type: 'line',
            data: {
                labels: tLabels,
                datasets: [{
                    label: 'Leads',
                    data: tValues,
                    borderColor: palette.gold[0],
                    backgroundColor: function(ctx) {
                        if (!ctx || !ctx.chart || !ctx.chart.chartArea) return palette.gold[0] + '30';
                        var chart = ctx.chart;
                        var gradient = chart.ctx.createLinearGradient(0, chart.chartArea.top, 0, chart.chartArea.bottom);
                        gradient.addColorStop(0, palette.gold[0] + '30');
                        gradient.addColorStop(1, palette.gold[0] + '04');
                        return gradient;
                    },
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: palette.gold[0],
                    pointBorderColor: isDark ? '#1a2332' : '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8,
                    pointHoverBorderWidth: 3,
                    pointHoverBorderColor: palette.dark[0],
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: Object.assign({}, tooltipOpts, {
                        padding: 8,
                        cornerRadius: 6,
                        callbacks: {
                            label: function(ctx) { return '  ' + ctx.parsed.y.toLocaleString('es-AR') + ' leads'; }
                        }
                    })
                },
                scales: {
                    x: { ticks: { font: { family: 'Manrope', size: 9 } }, grid: { display: false } },
                    y: {
                        ticks: { font: baseFont, stepSize: 1, callback: function(v) { return v.toLocaleString('es-AR'); } },
                        grid: { color: chartGridColor() },
                        beginAtZero: true
                    }
                },
                animation: chartAnim()
            }
        });
    }

    // 4. Operation Type (doughnut)
    destroyStatsChart('opType');
    const otData = stats.by_operation_type || [];
    if (otData.length && document.getElementById('chart-op-type')) {
        const otLabels = otData.map(function(d) { return d.label || t('chart.no_type'); });
        const otValues = otData.map(function(d) { return d.value; });
        statsCharts['opType'] = new Chart(document.getElementById('chart-op-type'), {
            type: 'doughnut',
            data: {
                labels: otLabels,
                datasets: [{
                    data: otValues,
                    backgroundColor: palette.mixed,
                    borderWidth: 0,
                    hoverOffset: 10,
                    hoverBorderWidth: 2,
                    hoverBorderColor: palette.dark[0],
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: { display: true, position: 'bottom', labels: { font: baseFont, boxWidth: 14, padding: 14, usePointStyle: true, pointStyle: 'circle' } },
                    tooltip: Object.assign({}, tooltipOpts, {
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce(function(a, b) { return a + b; }, 0);
                                const pct = total ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return '  ' + ctx.label + ': ' + ctx.parsed.toLocaleString('es-AR') + ' (' + pct + '%)';
                            }
                        }
                    })
                },
                animation: chartAnim()
            }
        });
    }

    // Update chart count badges
    var ptCount = document.getElementById('chartPropTypeCount');
    if (ptCount) ptCount.textContent = (stats.by_property_type || []).length + ' ' + t('chart.types');

    var zCount = document.getElementById('chartZonesCount');
    if (zCount) zCount.textContent = (stats.by_zone || []).length + ' ' + t('chart.zones');

    var tCount = document.getElementById('chartTrendCount');
    if (tCount) tCount.textContent = (stats.trend || []).length + ' ' + t('chart.months');

    var otCount = document.getElementById('chartOpTypeCount');
    if (otCount) otCount.textContent = (stats.by_operation_type || []).length + ' ' + t('chart.types');
}

function renderTopSearched(stats) {
    var total = stats.total || 0;

    function renderCard(data, nameElId, pctElId, barElId, subElId) {
        var items = data || [];
        var nameEl = document.getElementById(nameElId);
        var pctEl = document.getElementById(pctElId);
        var barEl = document.getElementById(barElId);
        var subEl = document.getElementById(subElId);

        if (items.length && nameEl && total > 0) {
            nameEl.textContent = items[0].label || t('chart.no_data');
            var pct = ((items[0].value / total) * 100).toFixed(1);
            if (pctEl) pctEl.textContent = pct + '%';
            if (subEl) subEl.textContent = items[0].value + ' ' + t('stats.requests_total');

            // Animate progress bar
            if (barEl) {
                barEl.style.width = '0%';
                requestAnimationFrame(function() {
                    requestAnimationFrame(function() {
                        barEl.style.width = pct + '%';
                    });
                });
            }
        } else {
            if (nameEl) nameEl.textContent = '—';
            if (pctEl) pctEl.textContent = '';
            if (subEl) subEl.textContent = '';
            if (barEl) barEl.style.width = '0%';
        }
    }

    renderCard(stats.by_property_type, 'topPropertyType', 'topPropertyTypePct', 'topPropertyTypeBar', 'topPropertyTypeSub');
    renderCard(stats.by_zone, 'topZone', 'topZonePct', 'topZoneBar', 'topZoneSub');
    renderCard(stats.by_operation_type, 'topOperationType', 'topOperationTypePct', 'topOperationTypeBar', 'topOperationTypeSub');
}



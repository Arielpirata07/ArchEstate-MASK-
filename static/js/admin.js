// ---- Tab switching ----
function showTab(tab) {
    document.getElementById('panel-dashboard').classList.add('hidden');
    document.getElementById('panel-management').classList.add('hidden');
    document.getElementById('panel-reports').classList.add('hidden');
    document.getElementById('panel-form-options').classList.add('hidden');
    document.getElementById('panel-' + tab).classList.remove('hidden');

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-midnight', 'text-white');
        btn.classList.add('bg-paper-dark', 'text-midnight');
    });
    const active = document.getElementById('tab-' + tab);
    active.classList.add('bg-midnight', 'text-white');
    active.classList.remove('bg-paper-dark', 'text-midnight');

    if (tab === 'reports') {
        loadReports();
    }
    if (tab === 'form-options') {
        loadFormOptions();
    }
}

// ================================================================
// DASHBOARD INTERACTIVO
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

// Instancias de Chart.js (para poder destruir y recrear)
const charts = {};

// Estado del dashboard
let dashState = {
    period:        7,
    typeChartMode: 'doughnut',   // 'doughnut' | 'bar'
    monthChartType: 'line',      // 'line' | 'bar'
    rawData:       null,
    allZones:      [],
};

// ---- Animación de contador ----
function animateCounter(el, target) {
    const duration = 700;
    const start    = performance.now();
    const from     = 0;
    const step = (now) => {
        const t   = Math.min((now - start) / duration, 1);
        const val = Math.round(from + (target - from) * (1 - Math.pow(1 - t, 3)));
        el.textContent = val;
        if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

// ---- Helpers ----
function destroyChart(key) {
    if (charts[key]) { charts[key].destroy(); delete charts[key]; }
}

function exportChart(canvasId, filename) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

// ---- Período ----
function setPeriod(days) {
    dashState.period = days;
    document.querySelectorAll('.period-btn').forEach(btn => {
        const active = parseInt(btn.dataset.period) === days;
        btn.className = 'period-btn px-3 py-1 rounded text-[10px] font-bold uppercase tracking-widest transition-all '
            + (active ? 'bg-midnight text-white' : 'bg-paper-dark text-midnight hover:bg-gold hover:text-white');
    });
    renderMonthChart();
}

// ---- Refresh ----
async function refreshDashboard() {
    const icon = document.getElementById('refresh-icon');
    icon.style.animation = 'spin 0.8s linear infinite';
    icon.style.display   = 'inline-block';
    dashState.rawData = null;
    await initDashboard();
    setTimeout(() => { icon.style.animation = ''; }, 600);
}

// ---- Filtro de zonas ----
function filterZoneChart() {
    const q = document.getElementById('zone-filter-input').value.toLowerCase().trim();
    const filtered = q
        ? dashState.allZones.filter(d => d.label.toLowerCase().includes(q))
        : dashState.allZones;

    if (!charts['zone']) return;
    charts['zone'].data.labels   = filtered.map(d => d.label);
    charts['zone'].data.datasets[0].data            = filtered.map(d => d.value);
    charts['zone'].data.datasets[0].backgroundColor = getPalette().dark.slice(0, filtered.length);
    charts['zone'].update();
}

// ---- Toggle tipo/operación: Doughnut ↔ Bar ----
function toggleChartType() {
    dashState.typeChartMode = dashState.typeChartMode === 'doughnut' ? 'bar' : 'doughnut';
    renderTypeChart();
}

function renderTypeChart() {
    if (typeof Chart === 'undefined') return;
    const data = dashState.rawData;
    if (!data) return;
    destroyChart('type');
    const isDoughnut = dashState.typeChartMode === 'doughnut';
    charts['type'] = new Chart(document.getElementById('chart-type'), {
        type: isDoughnut ? 'doughnut' : 'bar',
        data: {
            labels: data.leads_by_type.map(d => d.label),
            datasets: [{
                data: data.leads_by_type.map(d => d.value),
                backgroundColor: getPalette().gold,
                borderWidth: 0,
                hoverOffset: 6,
                borderRadius: isDoughnut ? 0 : 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            cutout: isDoughnut ? '65%' : undefined,
            plugins: {
                legend: { display: isDoughnut, labels: { font: baseFont, boxWidth: 12 } },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct   = total ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return `  ${ctx.label}: ${ctx.parsed} (${pct}%)`;
                        }
                    }
                }
            },
            scales: isDoughnut ? {} : {
                x: { ticks: { font: { family: 'Manrope', size: 9 } }, grid: { display: false } },
                y: { ticks: { font: baseFont, stepSize: 1 }, grid: { color: chartGridColor() }, beginAtZero: true }
            }
        }
    });
}

// ---- Toggle chart mensual: Línea ↔ Barras ----
function setMonthChartType(type) {
    dashState.monthChartType = type;
    document.querySelectorAll('.month-type-btn').forEach(btn => {
        const active = btn.dataset.mtype === type;
        btn.className = 'month-type-btn px-2 py-1 text-[9px] font-bold uppercase tracking-widest rounded transition-all '
            + (active ? 'bg-midnight text-white' : 'bg-midnight/5 text-midnight/50 hover:bg-gold hover:text-white');
    });
    renderMonthChart();
}

function renderMonthChart() {
    if (typeof Chart === 'undefined') return;
    const data = dashState.rawData;
    if (!data) return;

    // Filtrar por período seleccionado
    const all     = data.leads_by_month;
    const months  = dashState.period <= 30  ? 1
                  : dashState.period <= 90  ? 3
                  : dashState.period <= 180 ? 6
                  : all.length;

    const slice   = all.slice(-Math.max(months, 1));
    const labels  = slice.map(d => {
        const [y, m] = d.label.split('-');
        return new Date(y, m - 1).toLocaleString('es', { month: 'short', year: '2-digit' });
    });
    const values  = slice.map(d => d.value);
    const isLine  = dashState.monthChartType === 'line';

    destroyChart('month');
    charts['month'] = new Chart(document.getElementById('chart-month'), {
        type: isLine ? 'line' : 'bar',
        data: {
            labels: labels.length ? labels : ['Este mes'],
            datasets: [{
                label: 'Leads',
                data:  values.length ? values : [data.total_leads],
                borderColor: '#735A3A',
                backgroundColor: isLine ? 'rgba(115,90,58,0.08)' : '#735A3A',
                fill: isLine, tension: 0.4,
                pointBackgroundColor: '#735A3A', pointRadius: isLine ? 5 : 0,
                borderRadius: isLine ? 0 : 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: { label: ctx => `  ${ctx.parsed.y} leads` }
                }
            },
            scales: {
                x: { ticks: { font: baseFont }, grid: { color: chartGridColor() } },
                y: { ticks: { font: baseFont, stepSize: 1 }, grid: { color: chartGridColor() }, beginAtZero: true }
            },
            animation: { duration: 400 }
        }
    });
}

// ---- Init principal ----
async function initDashboard() {
    try {
        const res  = await fetch('/api/admin/stats');
        const data = await res.json();
        dashState.rawData  = data;
        dashState.allZones = data.leads_by_zone;

        // KPI Cards con contadores animados
        animateCounter(document.getElementById('kpi-leads'), data.total_leads);

        const approved = data.pros_stats.find(s => s.label === 'approved');
        const pending  = data.pros_stats.find(s => s.label === 'pending');
        const rejected = data.pros_stats.find(s => s.label === 'rejected');
        const totalPros = (approved?.value || 0) + (pending?.value || 0) + (rejected?.value || 0);

        animateCounter(document.getElementById('kpi-pros-approved'), approved?.value || 0);
        animateCounter(document.getElementById('kpi-pros-pending'),  pending?.value  || 0);

        const pct = totalPros ? Math.round((approved?.value || 0) / totalPros * 100) : 0;
        document.getElementById('kpi-pros-approved-pct').textContent = totalPros ? `${pct}% del total` : '';
        document.getElementById('kpi-pending-label').textContent     = (pending?.value || 0) > 0 ? '⚠ Requieren revisión' : '';

        const totalAudit = data.audit_actions.reduce((sum, a) => sum + a.value, 0);
        animateCounter(document.getElementById('kpi-audit'), totalAudit);
        const topAction = data.audit_actions[0];
        document.getElementById('kpi-audit-sub').textContent = topAction ? `${topAction.label}: ${topAction.value}` : '';

        // Gráficos (solo si Chart.js cargó correctamente)
        if (typeof Chart !== 'undefined') {
            renderTypeChart();

            // Zona
            destroyChart('zone');
            charts['zone'] = new Chart(document.getElementById('chart-zone'), {
                type: 'bar',
                data: {
                    labels: data.leads_by_zone.map(d => d.label),
                    datasets: [{ label: 'Leads', data: data.leads_by_zone.map(d => d.value), backgroundColor: getPalette().dark, borderRadius: 4, borderSkipped: false }]
                },
                options: {
                    responsive: true,
                    indexAxis: 'y',
                    plugins: { legend: { display: false },
                        tooltip: { callbacks: { label: ctx => `  ${ctx.parsed.x} leads` } }
                    },
                    scales: {
                        x: { ticks: { font: baseFont, stepSize: 1 }, grid: { color: chartGridColor() } },
                        y: { ticks: { font: baseFont }, grid: { display: false } }
                    }
                }
            });

            renderMonthChart();

            // Presupuesto
            destroyChart('budget');
            charts['budget'] = new Chart(document.getElementById('chart-budget'), {
                type: 'bar',
                data: {
                    labels: data.leads_by_budget.map(d => d.label),
                    datasets: [{ label: 'Leads', data: data.leads_by_budget.map(d => d.value), backgroundColor: getPalette().mixed, borderRadius: 4, borderSkipped: false }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false },
                        tooltip: { callbacks: { label: ctx => `  ${ctx.parsed.y} leads` } }
                    },
                    scales: {
                        x: { ticks: { font: { family: 'Manrope', size: 8, weight: 'bold' }, maxRotation: 30 }, grid: { display: false } },
                        y: { ticks: { font: baseFont, stepSize: 1 }, grid: { color: chartGridColor() }, beginAtZero: true }
                    }
                }
            });
        } else {
            console.warn('Chart.js no está disponible. Los gráficos no se renderizarán.');
        }

        if (window.lucide) lucide.createIcons();

    } catch (err) {
        console.error('Error cargando estadísticas:', err);
    }
}

// Agregar estilo de spin
const spinStyle = document.createElement('style');
spinStyle.textContent = '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }';
document.head.appendChild(spinStyle);

document.addEventListener('DOMContentLoaded', initDashboard);

// ---- Profesionales dinámicos ----
let currentProFilters = {
    search: '',
    status: '',
    specialty: '',
    sort: 'id',
    order: 'desc'
};

// Cargar profesionales al cambiar a la pestaña de gestión
document.getElementById('tab-management').addEventListener('click', function() {
    loadProfessionals();
});

// Configurar event listeners para filtros de profesionales
document.addEventListener('DOMContentLoaded', function() {
    const applyBtn = document.getElementById('applyProFilters');
    const clearBtn = document.getElementById('clearProFilters');
    const sortSelect = document.getElementById('proSortSelect');
    const sortOrderBtn = document.getElementById('proSortOrder');
    
    if (applyBtn) applyBtn.addEventListener('click', applyProFilters);
    if (clearBtn) clearBtn.addEventListener('click', clearProFilters);
    if (sortSelect) sortSelect.addEventListener('change', updateProSort);
    if (sortOrderBtn) sortOrderBtn.addEventListener('click', toggleProSortOrder);
    
    // Búsqueda en tiempo real
    let searchTimeout;
    const searchInput = document.getElementById('proSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(applyProFilters, 500);
        });
    }

    // Delegación de eventos para botones toggle-active en la tabla de profesionales
    document.getElementById('professionalsTableBody').addEventListener('click', function(e) {
        const btn = e.target.closest('.toggle-active-btn');
        if (!btn) return;
        const userId = parseInt(btn.dataset.userId, 10);
        const userName = btn.dataset.userName || '';
        const activate = btn.dataset.activate === 'true';
        if (userId) openDeactivateModal(userId, userName, activate);
    });
});

// Cargar profesionales desde la API
async function loadProfessionals() {
    try {
        const params = new URLSearchParams(currentProFilters);
        const response = await fetch(`/api/professionals?${params}`);
        const data = await response.json();
        
        if (data.success) {
            renderProfessionals(data.professionals);
            updateProsCount(data.total);
        } else {
            showProError(data.error || 'Error al cargar profesionales');
        }
    } catch (error) {
        console.error('Error loading professionals:', error);
        showProError('Error de conexión');
    }
}

// Renderizar profesionales en la tabla
function renderProfessionals(pros) {
    const tbody = document.getElementById('professionalsTableBody');
    
    if (pros.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="p-8 text-center text-midnight/60">
                    <i data-lucide="search" class="w-8 h-8 mx-auto mb-2 text-midnight/30"></i>
                    <p>No se encontraron profesionales con los filtros aplicados.</p>
                </td>
            </tr>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }
    
    tbody.innerHTML = pros.map(pro => {
        // Badge de estado de habilitación profesional
        let statusBadge = '';
        if (pro.status === 'approved') {
            statusBadge = '<span class="px-2 py-1 bg-emerald-50 text-emerald-700 text-[9px] font-bold uppercase tracking-widest rounded">Aprobado</span>';
        } else if (pro.status === 'rejected') {
            statusBadge = '<span class="px-2 py-1 bg-rose-50 text-rose-700 text-[9px] font-bold uppercase tracking-widest rounded">Rechazado</span>';
        } else {
            statusBadge = '<span class="px-2 py-1 bg-amber-50 text-amber-700 text-[9px] font-bold uppercase tracking-widest rounded">Pendiente</span>';
        }

        // Badge de estado de cuenta (activa / baja)
        // is_active: 1=activo, 0=baja, null=campo no devuelto por la API → asumir activo
        const hasUser  = pro.user_id !== null && pro.user_id !== undefined;
        const rawActive = pro.is_active;
        const isActive  = !hasUser ? null
                        : (rawActive === null || rawActive === undefined) ? true
                        : rawActive !== 0;

        const accountBadge = isActive === false
            ? '<span class="ml-1 px-2 py-1 bg-midnight/10 text-midnight/50 text-[9px] font-bold uppercase tracking-widest rounded">Cuenta baja</span>'
            : '';

        // Botones de aprobación/rechazo (deshabilitados si cuenta dada de baja o sin usuario)
        let approvalActions = '';
        if (!hasUser || isActive === false) {
            approvalActions = '<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest">—</span>';
        } else if (pro.status === 'pending') {
            approvalActions = `
                <button onclick="updateProStatus('${pro.id}', 'approved', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-emerald-100 transition-colors">
                    <i data-lucide="check" class="w-3 h-3"></i> Aprobar
                </button>
                <button onclick="updateProStatus('${pro.id}', 'rejected', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-rose-50 text-rose-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-rose-100 transition-colors">
                    <i data-lucide="x" class="w-3 h-3"></i> Rechazar
                </button>`;
        } else if (pro.status === 'approved') {
            approvalActions = `
                <button onclick="updateProStatus('${pro.id}', 'rejected', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-rose-50 text-rose-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-rose-100 transition-colors">
                    <i data-lucide="x" class="w-3 h-3"></i> Desaprobar
                </button>`;
        } else if (pro.status === 'rejected') {
            approvalActions = `
                <button onclick="updateProStatus('${pro.id}', 'approved', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-emerald-100 transition-colors">
                    <i data-lucide="check" class="w-3 h-3"></i> Aprobar
                </button>`;
        }

        // Botón de baja/reactivación — solo si hay usuario vinculado
        let accountBtn = '';
        if (!hasUser) {
            accountBtn = '<span class="text-[10px] text-midnight/20 italic">Sin cuenta</span>';
        } else if (isActive !== false) {
            accountBtn = `<button data-user-id="${pro.user_id}" data-user-name="${escapeHtml(pro.name)}" data-activate="false"
                   class="toggle-active-btn inline-flex items-center gap-1 px-2 py-1 bg-midnight/5 text-midnight/50 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-rose-50 hover:text-rose-600 transition-colors">
                   <i data-lucide="user-x" class="w-3 h-3"></i> Dar de baja
               </button>`;
        } else {
            accountBtn = `<button data-user-id="${pro.user_id}" data-user-name="${escapeHtml(pro.name)}" data-activate="true"
                   class="toggle-active-btn inline-flex items-center gap-1 px-2 py-1 bg-midnight/5 text-midnight/50 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-emerald-50 hover:text-emerald-600 transition-colors">
                   <i data-lucide="user-check" class="w-3 h-3"></i> Reactivar
               </button>`;
        }

        const docCell = pro.doc_path
            ? `<a href="/admin/download_doc/${pro.user_id}" class="inline-flex items-center gap-2 px-2 py-1 bg-gold text-white rounded font-bold uppercase tracking-widest text-[9px] hover:bg-midnight transition-colors">
                   <i data-lucide="download" class="w-3 h-3"></i> Descargar
               </a>`
            : '<span class="text-midnight/30 text-[10px] uppercase italic">Sin documento</span>';

        const rowOpacity = isActive === false ? 'opacity-60' : '';

        return `
            <tr class="border-b border-midnight/[0.03] hover:bg-paper transition-colors ${rowOpacity}">
                <td class="px-4 py-3 text-[13px]">
                    <div class="font-medium text-midnight">${escapeHtml(pro.name)} ${accountBadge}</div>
                    <div class="text-[11px] text-midnight/40 italic">${escapeHtml(pro.specialty || '')}</div>
                </td>
                <td class="px-4 py-3 font-mono text-[11px] text-midnight/40">${escapeHtml(pro.license)}</td>
                <td class="px-4 py-3">${statusBadge}</td>
                <td class="px-4 py-3">${docCell}</td>
                <td class="px-4 py-3 text-right">
                    <div class="flex justify-end items-center gap-2 flex-wrap">
                        ${approvalActions}
                        <span class="text-midnight/10 select-none">|</span>
                        ${accountBtn}
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    initTableStagger(tbody);
    if (window.lucide) lucide.createIcons();
}

// Aplicar filtros de profesionales
function applyProFilters() {
    const searchInput = document.getElementById('proSearchInput');
    const statusFilter = document.getElementById('statusFilter');
    const specialtyFilter = document.getElementById('specialtyFilter');
    
    currentProFilters.search = searchInput ? searchInput.value.trim() : '';
    currentProFilters.status = statusFilter ? statusFilter.value : '';
    currentProFilters.specialty = specialtyFilter ? specialtyFilter.value.trim() : '';
    
    loadProfessionals();
}

// Limpiar filtros de profesionales
function clearProFilters() {
    const searchInput = document.getElementById('proSearchInput');
    const statusFilter = document.getElementById('statusFilter');
    const specialtyFilter = document.getElementById('specialtyFilter');
    const sortSelect = document.getElementById('proSortSelect');
    
    if (searchInput) searchInput.value = '';
    if (statusFilter) statusFilter.value = '';
    if (specialtyFilter) specialtyFilter.value = '';
    if (sortSelect) sortSelect.value = 'id';
    
    // Resetear ícono de orden
    const proSortBtn = document.getElementById('proSortOrder');
    if (proSortBtn) { proSortBtn.innerHTML = '<i data-lucide="arrow-down" class="w-3 h-3"></i>'; if (window.lucide) lucide.createIcons(); }

    currentProFilters = {
        search: '',
        status: '',
        specialty: '',
        sort: 'id',
        order: 'desc'
    };
    
    loadProfessionals();
}

// Actualizar ordenamiento de profesionales
function updateProSort() {
    const sortSelect = document.getElementById('proSortSelect');
    currentProFilters.sort = sortSelect ? sortSelect.value : 'id';
    loadProfessionals();
}

// Cambiar dirección del ordenamiento de profesionales
function toggleProSortOrder() {
    currentProFilters.order = currentProFilters.order === 'desc' ? 'asc' : 'desc';
    const proSortBtn = document.getElementById('proSortOrder');
    if (proSortBtn) {
        proSortBtn.innerHTML = '<i data-lucide="' + (currentProFilters.order === 'desc' ? 'arrow-down' : 'arrow-up') + '" class="w-3 h-3"></i>';
        if (window.lucide) lucide.createIcons();
    }
    
    loadProfessionals();
}

// Actualizar contador de profesionales
function updateProsCount(count) {
    const countEl = document.getElementById('prosCount');
    if (countEl) countEl.textContent = count;
}

// Mostrar errores de profesionales
function showProError(message) {
    const tbody = document.getElementById('professionalsTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="p-8 text-center text-rose-600">
                    <i data-lucide="alert-circle" class="w-8 h-8 mx-auto mb-2"></i>
                <p>${escapeHtml(message)}</p>
            </td>
        </tr>
        `;
        
        if (window.lucide) {
            lucide.createIcons();
        }
    }
}
// ================================================================
// MODAL: DAR DE BAJA / REACTIVAR USUARIO
// ================================================================
let deactivateTargetId   = null;
let deactivateTargetName = null;
let deactivateNewState   = null;   // false = dar de baja, true = reactivar

function openDeactivateModal(userId, username, activate) {
    deactivateTargetId   = userId;
    deactivateTargetName = username;
    deactivateNewState   = activate;

    document.getElementById('deactivateModalUsername').textContent = username;
    document.getElementById('deactivateModalError').classList.add('hidden');
    document.getElementById('deactivateReason').value = '';

    const header  = document.getElementById('deactivateModalHeader');
    const tag     = document.getElementById('deactivateModalTag');
    const title   = document.getElementById('deactivateModalTitle');
    const warning = document.getElementById('deactivateModalWarning');
    const btn     = document.getElementById('confirmDeactivateBtn');
    const reasonW = document.getElementById('deactivateReasonWrapper');

    if (activate) {
        header.className = 'border-t-4 border-emerald-500 px-8 pt-8 pb-4';
        tag.className    = 'text-[10px] uppercase tracking-widest font-bold text-emerald-600 mb-1';
        tag.textContent  = 'Acción administrativa';
        title.innerHTML  = 'Reactivar <span class="serif-italic">Cuenta</span>';
        warning.className = 'mx-8 mb-6 p-3 bg-emerald-50 border border-emerald-100 rounded flex items-start gap-3';
        warning.innerHTML = `
            <i data-lucide="info" class="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5"></i>
            <p id="deactivateModalWarningText" class="text-[10px] text-emerald-700 font-bold uppercase tracking-wider leading-relaxed">
                El usuario recuperará el acceso a la plataforma inmediatamente. La acción quedará registrada en el log de auditoría.
            </p>`;
        btn.className    = 'flex-1 py-3 bg-emerald-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all flex items-center justify-center gap-2';
        btn.innerHTML    = '<i data-lucide="user-check" class="w-3 h-3"></i><span id="confirmDeactivateBtnLabel">Reactivar Cuenta</span>';
        reasonW.classList.add('hidden');
    } else {
        header.className = 'border-t-4 border-rose-500 px-8 pt-8 pb-4';
        tag.className    = 'text-[10px] uppercase tracking-widest font-bold text-rose-500 mb-1';
        tag.textContent  = 'Acción administrativa';
        title.innerHTML  = 'Dar de <span class="serif-italic">Baja</span>';
        warning.className = 'mx-8 mb-6 p-3 bg-rose-50 border border-rose-100 rounded flex items-start gap-3';
        warning.innerHTML = `
            <i data-lucide="alert-triangle" class="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5"></i>
            <p id="deactivateModalWarningText" class="text-[10px] text-rose-700 font-bold uppercase tracking-wider leading-relaxed">
                El usuario perderá acceso inmediatamente. Esta acción quedará registrada en el log de auditoría y puede revertirse.
            </p>`;
        btn.className    = 'flex-1 py-3 bg-rose-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all flex items-center justify-center gap-2';
        btn.innerHTML    = '<i data-lucide="user-x" class="w-3 h-3"></i><span id="confirmDeactivateBtnLabel">Dar de Baja</span>';
        reasonW.classList.remove('hidden');
    }

    document.getElementById('deactivateModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    if (window.lucide) lucide.createIcons();
}

function closeDeactivateModal() {
    document.getElementById('deactivateModal').classList.add('hidden');
    document.body.style.overflow = '';
    deactivateTargetId   = null;
    deactivateTargetName = null;
    deactivateNewState   = null;
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        closeDeactivateModal();
        closeLeadDetailModal();
    }
});

async function confirmDeactivate() {
    if (deactivateTargetId === null) return;

    const btn    = document.getElementById('confirmDeactivateBtn');
    const errEl  = document.getElementById('deactivateModalError');
    const orig   = btn.innerHTML;
    errEl.classList.add('hidden');

    btn.innerHTML = '<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div> Procesando...';
    btn.disabled  = true;

    try {
        const res  = await fetch(`/api/admin/user/${deactivateTargetId}/set-active`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                is_active: deactivateNewState,
                reason:    document.getElementById('deactivateReason').value.trim()
            })
        });
        const data = await res.json();

        if (res.ok) {
            closeDeactivateModal();
            if (typeof showToast === 'function') showToast(data.message);
            loadProfessionals();   // refrescar tabla
        } else {
            errEl.textContent = data.error || 'Error al procesar la solicitud.';
            errEl.classList.remove('hidden');
            btn.innerHTML = orig;
            btn.disabled  = false;
        }
    } catch (err) {
        errEl.textContent = 'Error de conexión. Intentá de nuevo.';
        errEl.classList.remove('hidden');
        btn.innerHTML = orig;
        btn.disabled  = false;
    }
}

/**
 * Gestion de Reportes de Leads
 */
let allReports = [];
let currentReportFilter = 'pending';

function loadReports() {
    fetch('/api/admin/reports')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                allReports = data.reports;
                renderReportsKPIs(data);
                renderReports(data.reports);
                updateReportBadge(data.status_counts);
            }
        })
        .catch(e => console.error('Error loading reports:', e));
}

function renderReportsKPIs(data) {
    document.getElementById('kpiTotalReports').textContent = data.total || 0;
    document.getElementById('kpiPendingReports').textContent = (data.status_counts && data.status_counts.pending) || 0;
    document.getElementById('kpiDismissedReports').textContent = (data.status_counts && data.status_counts.dismissed) || 0;
    document.getElementById('kpiDeletedReports').textContent = (data.status_counts && data.status_counts.deleted) || 0;
}

function updateReportBadge(statusCounts) {
    const badge = document.getElementById('reportBadge');
    const pending = (statusCounts && statusCounts.pending) || 0;
    if (pending > 0) {
        badge.textContent = pending;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function filterReports(filter) {
    currentReportFilter = filter;
    document.querySelectorAll('.report-filter-chip').forEach(chip => {
        chip.classList.toggle('report-filter-active', chip.dataset.filter === filter);
    });

    let filtered = allReports;
    if (filter === 'pending') filtered = allReports.filter(r => r.status === 'pending');
    else if (filter === 'dismissed') filtered = allReports.filter(r => r.status === 'dismissed');
    else if (filter === 'deleted') filtered = allReports.filter(r => r.status === 'deleted');

    renderReports(filtered);
}

function renderReports(reports) {
    const tbody = document.getElementById('reportsTableBody');

    if (!reports.length) {
        tbody.innerHTML = `
            <tr><td colspan="10" class="p-12 text-center text-midnight/60">
                <i data-lucide="check-circle" class="w-10 h-10 mx-auto mb-3 text-emerald-200"></i>
                <p class="font-semibold text-midnight/40">No hay reportes para mostrar</p>
            </td></tr>`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = reports.map(r => {
        const statusBadge = r.status === 'pending'
            ? '<span class="px-2 py-1 bg-amber-50 text-amber-700 text-[9px] font-bold uppercase tracking-widest rounded">Pendiente</span>'
            : r.status === 'dismissed'
            ? '<span class="px-2 py-1 bg-paper-dark text-midnight/40 text-[9px] font-bold uppercase tracking-widest rounded">Descartado</span>'
            : '<span class="px-2 py-1 bg-rose-50 text-rose-600 text-[9px] font-bold uppercase tracking-widest rounded">Eliminado</span>';

        let actions;
        if (r.status === 'pending') {
            actions = `<div class="flex justify-end gap-2 flex-wrap">
                    <button onclick="viewLeadDetail(${r.lead_id})" class="px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                        Ver Lead
                    </button>
                    <button onclick="deleteLead(${r.id}, ${r.lead_id})" class="px-3 py-2 bg-rose-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all">
                        Eliminar
                    </button>
                    <button onclick="dismissReport(${r.id})" class="px-3 py-2 bg-paper-dark text-midnight rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold hover:text-white transition-all">
                        Descartar
                    </button>
               </div>`;
        } else {
            actions = `<div class="flex justify-end gap-2 flex-wrap">
                    ${r.lead_id ? `<button onclick="viewLeadDetail(${r.lead_id})" class="px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">Ver Lead</button>` : ''}
                    <button onclick="restoreReport(${r.id})" class="px-3 py-2 bg-emerald-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all">
                        Restaurar
                    </button>
               </div>`;
        }

        return `
            <tr class="border-b border-midnight/[0.03] hover:bg-paper transition-colors ${r.status === 'deleted' ? 'opacity-60' : ''}">
                <td class="px-4 py-3 font-mono text-[11px] text-midnight/40">#${r.lead_id}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${r.lead_type ? escapeHtml(r.lead_type) : '<span class="text-midnight/30">Lead eliminado</span>'}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${r.lead_property_type ? escapeHtml(r.lead_property_type) : '—'}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${r.lead_zone ? escapeHtml(r.lead_zone) : '—'}</td>
                <td class="px-4 py-3 text-[13px]">${r.lead_budget ? '<span class="text-[9px] font-bold uppercase tracking-widest text-midnight/50">' + (r.lead_currency === 'USD' ? 'US$' : r.lead_currency === 'EUR' ? '€' : '$') + '</span> ' + escapeHtml(r.lead_budget) : '—'}</td>
                <td class="px-4 py-3 font-mono text-[11px] text-rose-600">${r.lead_phone ? escapeHtml(r.lead_phone) : '—'}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${escapeHtml(r.reported_by_name)}</td>
                <td class="px-4 py-3">${statusBadge}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${r.created_at}</td>
                <td class="px-4 py-3">${actions}</td>
            </tr>`;
    }).join('');

    initTableStagger(tbody);
    if (window.lucide) lucide.createIcons();
}

function viewLeadDetail(leadId) {
    document.getElementById('leadDetailId').textContent = '#' + leadId;
    document.getElementById('leadDetailContent').innerHTML = `
        <div class="flex justify-center py-8">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gold"></div>
        </div>`;
    document.getElementById('leadDetailModal').classList.remove('hidden');
    if (window.lucide) lucide.createIcons();

    fetch(`/api/admin/lead/${leadId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                renderLeadDetail(data.lead);
            } else {
                document.getElementById('leadDetailContent').innerHTML = `
                    <p class="text-center text-rose-600 py-8">${escapeHtml(data.error || 'Error al cargar')}</p>`;
            }
        })
        .catch(() => {
            document.getElementById('leadDetailContent').innerHTML = `
                <p class="text-center text-rose-600 py-8">Error de conexion</p>`;
        });
}

function renderLeadDetail(lead) {
    const sym = lead.currency === 'USD' ? 'US$' : lead.currency === 'EUR' ? '€' : '$';
    const budget = `${sym}${lead.budget}`;
    const style = lead.architectural_style || 'No especificado';
    const amenities = lead.amenities
        ? lead.amenities.split(',').map(a => `
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 bg-gold rounded-full"></span>
                <p class="text-sm text-midnight">${escapeHtml(a.trim())}</p>
            </div>`).join('')
        : '<p class="text-sm text-midnight/50">No especificadas</p>';

    let typeDetails = '';
    if (lead.property_type === 'departamento') {
        typeDetails = `
            <div class="border-t border-midnight/10 pt-5 mt-5">
                <p class="text-[10px] uppercase tracking-widest text-midnight/60 font-bold mb-3">Detalles del Departamento</p>
                <div class="grid grid-cols-2 gap-4">
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Piso/Bloque</p><p class="text-sm text-midnight">${escapeHtml(lead.floor_block || 'No especificado')}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Metros Utiles</p><p class="text-sm text-midnight">${lead.usable_m2 ? lead.usable_m2 + ' m²' : 'No especificado'}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Ascensor</p><p class="text-sm text-midnight">${escapeHtml(lead.elevator || 'No especificado')}</p></div>
                </div>
            </div>`;
    } else if (lead.property_type === 'casa') {
        typeDetails = `
            <div class="border-t border-midnight/10 pt-5 mt-5">
                <p class="text-[10px] uppercase tracking-widest text-midnight/60 font-bold mb-3">Detalles de la Casa</p>
                <div class="grid grid-cols-2 gap-4">
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Terreno</p><p class="text-sm text-midnight">${lead.land_area ? lead.land_area + ' m²' : 'No especificado'}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Construida</p><p class="text-sm text-midnight">${lead.built_area ? lead.built_area + ' m²' : 'No especificado'}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Piscina</p><p class="text-sm text-midnight">${escapeHtml(lead.pool || 'No especificado')}</p></div>
                </div>
            </div>`;
    }

    document.getElementById('leadDetailContent').innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Tipo de Operacion</p><p class="text-base font-semibold text-midnight">${escapeHtml(lead.type)}</p></div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Tipo de Vivienda</p><p class="text-base text-midnight">${escapeHtml(lead.property_type || 'No especificado')}</p></div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Zona</p><p class="text-base text-midnight">${escapeHtml(lead.zone)}</p></div>
                ${lead.province ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Provincia</p><p class="text-base text-midnight">${escapeHtml(lead.province)}</p></div>` : ''}
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Presupuesto</p><p class="text-base font-serif italic text-gold">${budget}</p></div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Estilo Arquitectonico</p><p class="text-base text-midnight">${escapeHtml(style)}</p></div>
                ${lead.ambientes ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Ambientes</p><p class="text-base text-midnight">${escapeHtml(String(lead.ambientes))}</p></div>` : ''}
                ${lead.parking ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Cochera</p><p class="text-base text-midnight">${escapeHtml(lead.parking)}</p></div>` : ''}
                ${lead.orientation ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Orientacion</p><p class="text-base text-midnight">${escapeHtml(lead.orientation)}</p></div>` : ''}
                ${lead.property_condition ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Estado</p><p class="text-base text-midnight">${escapeHtml(lead.property_condition)}</p></div>` : ''}
                ${lead.property_age ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Antiguedad</p><p class="text-base text-midnight">${escapeHtml(lead.property_age)}</p></div>` : ''}
                <div class="border-t border-midnight/10 pt-4">
                    <p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-2">Contacto</p>
                    <div class="flex items-center gap-2 text-sm text-midnight"><i data-lucide="mail" class="w-4 h-4 text-gold flex-shrink-0"></i><span>${escapeHtml(lead.email)}</span></div>
                    <div class="flex items-center gap-2 text-sm text-midnight mt-1"><i data-lucide="phone" class="w-4 h-4 text-gold flex-shrink-0"></i><span>${escapeHtml(lead.phone)}</span></div>
                </div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">Registrado</p><p class="text-sm text-midnight">${lead.timestamp}</p></div>
            </div>
            <div class="space-y-4">
                <p class="text-lg font-serif text-midnight">Especificaciones Tecnicas</p>
                <div class="grid grid-cols-3 gap-4">
                    <div class="text-center"><p class="text-[9px] uppercase tracking-widest text-gold font-bold mb-1">Habitaciones</p><p class="text-2xl font-serif text-midnight">${lead.bedrooms || '-'}</p></div>
                    <div class="text-center"><p class="text-[9px] uppercase tracking-widest text-gold font-bold mb-1">Banos</p><p class="text-2xl font-serif text-midnight">${lead.bathrooms || '-'}</p></div>
                    <div class="text-center"><p class="text-[9px] uppercase tracking-widest text-gold font-bold mb-1">Metros</p><p class="text-2xl font-serif text-midnight">${lead.total_area || lead.land_area || lead.usable_m2 || '-'}</p>${(lead.total_area || lead.land_area || lead.usable_m2) ? '<p class="text-[9px] text-midnight/60">m²</p>' : ''}</div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    ${lead.usable_m2 ? `<div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Metros Utiles</p><p class="text-sm text-midnight">${lead.usable_m2} m²</p></div>` : ''}
                    ${lead.built_area ? `<div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Construida</p><p class="text-sm text-midnight">${lead.built_area} m²</p></div>` : ''}
                    ${lead.land_area ? `<div><p class="text-[9px] uppercase tracking-widest text-midnight/40 font-bold">Terreno</p><p class="text-sm text-midnight">${lead.land_area} m²</p></div>` : ''}
                </div>
                <div class="border-t border-midnight/10 pt-4">
                    <p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-3">Extras y Comodidades</p>
                    <div class="space-y-1.5">${amenities}</div>
                </div>
                ${typeDetails}
            </div>
        </div>`;

    if (window.lucide) lucide.createIcons();
}

function closeLeadDetailModal() {
    document.getElementById('leadDetailModal').classList.add('hidden');
}

function deleteLead(reportId, leadId) {
    var promise = typeof showConfirm === 'function' ? showConfirm('Eliminar permanentemente el lead #' + leadId + '? Esta accion no se puede deshacer.') : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
    fetch('/api/admin/report/' + reportId + '/delete', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') showToast('Lead eliminado correctamente', 'success');
                loadReports();
                if (typeof refreshDashboard === 'function') refreshDashboard();
            } else {
                if (typeof showToast === 'function') showToast(data.error || 'Error al eliminar', 'error');
            }
        })
        .catch(() => {
            if (typeof showToast === 'function') showToast('Error de conexion', 'error');
        });
    });
}

function dismissReport(reportId) {
    fetch(`/api/admin/report/${reportId}/dismiss`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') showToast('Reporte descartado', 'success');
                loadReports();
            } else {
                if (typeof showToast === 'function') showToast(data.error || 'Error', 'error');
            }
        })
        .catch(() => {
            if (typeof showToast === 'function') showToast('Error de conexion', 'error');
        });
}

function restoreReport(reportId) {
    var promise = typeof showConfirm === 'function' ? showConfirm('Restaurar este reporte a estado pendiente?') : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
        fetch('/api/admin/report/' + reportId + '/restore', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                if (typeof showToast === 'function') showToast('Reporte restaurado correctamente', 'success');
                loadReports();
                if (typeof refreshDashboard === 'function') refreshDashboard();
            } else {
                if (typeof showToast === 'function') showToast(data.error || 'Error al restaurar', 'error');
            }
        })
        .catch(function () {
            if (typeof showToast === 'function') showToast('Error de conexion', 'error');
        });
    });
}

// ================================================================
// FORM OPTIONS CRUD
// ================================================================
var allFormOptions = [];
var currentCategoryFilter = '';
var currentSearchFilter = '';
var isFormOptionSaving = false;
var _formOptionModalPrevFocus = null;

var FORM_OPTION_CATEGORIES = [
    'property_type', 'operation_type', 'currency', 'parking',
    'orientation', 'condition', 'age', 'budget_range',
    'province', 'architectural_style', 'amenities'
];

var FORM_OPTION_ICONS = [
    { name: 'building', label: 'Edificio' },
    { name: 'home', label: 'Casa' },
    { name: 'layers', label: 'Duplex' },
    { name: 'crown', label: 'Penthouse' },
    { name: 'store', label: 'Local' },
    { name: 'shopping-cart', label: 'Comprar' },
    { name: 'wrench', label: 'Reparar' },
    { name: 'hammer', label: 'Construir' },
    { name: 'paintbrush', label: 'Pintar' },
    { name: 'ruler', label: 'Medir' },
    { name: 'dollar-sign', label: 'Dolar' },
    { name: 'euro', label: 'Euro' },
    { name: 'banknote', label: 'Billete' },
    { name: 'car', label: 'Auto' },
    { name: 'parking-circle', label: 'Estacionamiento' },
    { name: 'lock', label: 'Cerrado' },
    { name: 'unlock', label: 'Abierto' },
    { name: 'arrow-up', label: 'Norte' },
    { name: 'arrow-down', label: 'Sur' },
    { name: 'arrow-right', label: 'Este' },
    { name: 'arrow-left', label: 'Oeste' },
    { name: 'compass', label: 'Orientacion' },
    { name: 'sparkles', label: 'Nuevo' },
    { name: 'hard-hat', label: 'Obra' },
    { name: 'clock', label: 'Antiguedad' },
    { name: 'timer', label: 'Tiempo' },
    { name: 'calendar', label: 'Fecha' },
    { name: 'map-pin', label: 'Ubicacion' },
    { name: 'map', label: 'Mapa' },
    { name: 'globe', label: 'Global' },
    { name: 'bed', label: 'Dormitorio' },
    { name: 'bath', label: 'Bano' },
    { name: 'sofa', label: 'Ambiente' },
    { name: 'maximize', label: 'Metros' },
    { name: 'move', label: 'Superficie' },
    { name: 'triangle', label: 'Terreno' },
    { name: 'box', label: 'Construido' },
    { name: 'zap', label: 'Energia' },
    { name: 'wifi', label: 'Conexion' },
    { name: 'shield', label: 'Seguridad' },
    { name: 'trees', label: 'Verde' },
    { name: 'mountain', label: 'Montana' },
    { name: 'sun', label: 'Sol' },
    { name: 'droplets', label: 'Agua' },
    { name: 'wind', label: 'Viento' },
    { name: 'thermometer', label: 'Clima' },
    { name: 'heart', label: 'Favorito' },
    { name: 'star', label: 'Destacado' },
    { name: 'eye', label: 'Visible' },
    { name: 'camera', label: 'Foto' },
    { name: 'image', label: 'Imagen' },
    { name: 'file-text', label: 'Documento' },
    { name: 'phone', label: 'Telefono' },
    { name: 'mail', label: 'Email' },
    { name: 'flag', label: 'Bandera' },
    { name: 'tag', label: 'Etiqueta' },
    { name: 'info', label: 'Info' },
    { name: 'check-circle', label: 'OK' },
    { name: 'x-circle', label: 'No' },
    { name: 'alert-triangle', label: 'Alerta' },
    { name: 'plus-circle', label: 'Agregar' },
    { name: 'minus-circle', label: 'Quitar' }
];

function _setupFormOptionModalFocusTrap() {
    var modal = document.getElementById('formOptionModal');
    if (!modal) return;
    modal.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeFormOptionModal();
            return;
        }
        if (e.key !== 'Tab') return;
        var focusable = modal.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey) {
            if (document.activeElement === first) { e.preventDefault(); last.focus(); }
        } else {
            if (document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
    });
}

function renderIconPicker(selectedIcon) {
    var html = '<div class="icon-picker-wrap mt-1 border border-midnight/10 rounded overflow-hidden">' +
        '<label for="fo-icon-search" class="sr-only">Buscar icono</label>' +
        '<input id="fo-icon-search" type="text" placeholder="Buscar icono..." oninput="filterIcons(this.value)" class="icon-search w-full px-2 py-1.5 text-xs border-0 border-b border-midnight/10 outline-none bg-paper-dark/50">' +
        '<div id="icon-picker-grid" class="grid grid-cols-6 gap-0.5 p-1.5 max-h-32 overflow-y-auto">';
    html += '<button type="button" data-icon="" data-search="ninguno" onclick="selectIconOption(this)" aria-label="Sin icono" class="icon-pick p-1 rounded border text-[10px] flex flex-col items-center gap-px transition-all ' +
        (!selectedIcon ? 'border-gold bg-gold/10 text-gold' : 'border-transparent text-midnight/40 hover:border-midnight/20') + '" title="Sin icono">' +
        '<i data-lucide="x" class="w-3 h-3"></i><span class="leading-none">Ninguno</span></button>';
    FORM_OPTION_ICONS.forEach(function(icon) {
        var active = selectedIcon === icon.name;
        html += '<button type="button" data-icon="' + icon.name + '" data-search="' + (icon.name + ' ' + icon.label).toLowerCase() + '" onclick="selectIconOption(this)" aria-label="' + escapeHtml(icon.label) + '" class="icon-pick p-1 rounded border text-[10px] flex flex-col items-center gap-px transition-all ' +
            (active ? 'border-gold bg-gold/10 text-gold' : 'border-transparent text-midnight/50 hover:border-midnight/20 hover:text-midnight') + '" title="' + escapeHtml(icon.label) + '">' +
            '<i data-lucide="' + icon.name + '" class="w-3 h-3"></i><span class="leading-none truncate w-full text-center">' + escapeHtml(icon.label) + '</span></button>';
    });
    html += '</div></div>';
    return html;
}

function filterIcons(query) {
    var grid = document.getElementById('icon-picker-grid');
    if (!grid) return;
    var q = query.toLowerCase().trim();
    grid.querySelectorAll('.icon-pick').forEach(function(btn) {
        var match = !q || (btn.dataset.search && btn.dataset.search.indexOf(q) !== -1);
        btn.style.display = match ? '' : 'none';
    });
}

function selectIconOption(btn) {
    var picker = btn.closest('.grid');
    picker.querySelectorAll('.icon-pick').forEach(function(b) {
        b.classList.remove('border-gold', 'bg-gold/10', 'text-gold');
        b.classList.add('border-transparent', 'text-midnight/50');
    });
    btn.classList.remove('border-transparent', 'text-midnight/50');
    btn.classList.add('border-gold', 'bg-gold/10', 'text-gold');
    document.getElementById('fo-icon').value = btn.dataset.icon || '';
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function loadFormOptions() {
    currentSearchFilter = '';
    var searchInput = document.getElementById('fo-search');
    if (searchInput) searchInput.value = '';
    fetch('/api/form-options/all')
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(data) {
            allFormOptions = data.options || [];
            buildCategoryFilters();
            renderFormOptions();
        })
        .catch(function() {
            if (typeof showToast === 'function') showToast('Error al cargar opciones', 'error');
        });
}

function buildCategoryFilters() {
    var cats = [];
    allFormOptions.forEach(function(o) {
        if (cats.indexOf(o.category) === -1) cats.push(o.category);
    });
    var container = document.getElementById('category-filters');
    var html = '<button role="tab" aria-pressed="' + (!currentCategoryFilter) + '" onclick="filterCategory(\'\')" class="cat-filter px-3 py-1 text-[10px] font-bold uppercase tracking-widest rounded ' +
        (!currentCategoryFilter ? 'bg-midnight text-white' : 'bg-paper-dark text-midnight hover:bg-gold hover:text-white') + '">Todas</button>';
    cats.forEach(function(c) {
        html += '<button role="tab" aria-pressed="' + (currentCategoryFilter === c) + '" onclick="filterCategory(\'' + c + '\')" class="cat-filter px-3 py-1 text-[10px] font-bold uppercase tracking-widest rounded ' +
            (currentCategoryFilter === c ? 'bg-midnight text-white' : 'bg-paper-dark text-midnight hover:bg-gold hover:text-white') + '">' + c.replace(/_/g, ' ') + '</button>';
    });
    container.innerHTML = html;
}

function filterCategory(cat) {
    currentCategoryFilter = cat;
    buildCategoryFilters();
    renderFormOptions();
}

function filterBySearch(query) {
    currentSearchFilter = query.toLowerCase().trim();
    renderFormOptions();
}

function renderFormOptions() {
    var filtered = allFormOptions;
    if (currentCategoryFilter) {
        filtered = filtered.filter(function(o) { return o.category === currentCategoryFilter; });
    }
    if (currentSearchFilter) {
        filtered = filtered.filter(function(o) {
            return o.value.toLowerCase().indexOf(currentSearchFilter) !== -1 ||
                   o.label.toLowerCase().indexOf(currentSearchFilter) !== -1 ||
                   o.category.toLowerCase().indexOf(currentSearchFilter) !== -1;
        });
    }

    var tbody = document.getElementById('form-options-tbody');
    var liveRegion = document.getElementById('fo-results-count');
    if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-midnight/40">Sin opciones</td></tr>';
        if (liveRegion) liveRegion.textContent = '0 opciones encontradas';
        return;
    }
    tbody.innerHTML = filtered.map(function(o) {
        return '<tr class="hover:bg-paper-dark/30 ' + (o.is_active ? '' : 'opacity-40') + '">' +
            '<td class="px-4 py-3 text-[13px]"><span class="text-[10px] font-bold uppercase tracking-widest text-gold bg-gold/10 px-2 py-1 rounded">' + escapeHtml(o.category) + '</span></td>' +
            '<td class="px-4 py-3 font-mono text-[11px] text-midnight/40">' + escapeHtml(o.value) + '</td>' +
            '<td class="px-4 py-3 text-[13px] text-midnight/50">' + escapeHtml(o.label) + '</td>' +
            '<td class="px-4 py-3 text-[13px] text-midnight/50">' + (o.icon ? '<i data-lucide="' + escapeHtml(o.icon) + '" class="w-4 h-4 inline-block"></i> <span class="text-[11px]">' + escapeHtml(o.icon) + '</span>' : '<span class="text-[11px]">-</span>') + '</td>' +
            '<td class="px-4 py-3 text-[13px] text-midnight/50">' + o.sort_order + '</td>' +
            '<td class="px-4 py-3"><span class="px-2 py-1 text-[10px] font-bold rounded ' +
            (o.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700') + '">' +
            (o.is_active ? 'Activo' : 'Inactivo') + '</span></td>' +
            '<td class="px-4 py-3 text-right"><div class="flex gap-1 justify-end">' +
            '<button onclick="editFormOption(' + o.id + ')" aria-label="Editar ' + escapeHtml(o.label) + '" class="p-1.5 rounded hover:bg-paper-dark" title="Editar"><i data-lucide="pencil" class="w-3 h-3"></i></button>' +
            '<button onclick="toggleFormOption(' + o.id + ', ' + (o.is_active ? 0 : 1) + ')" aria-label="' + (o.is_active ? 'Desactivar' : 'Activar') + ' ' + escapeHtml(o.label) + '" class="p-1.5 rounded hover:bg-paper-dark" title="' + (o.is_active ? 'Desactivar' : 'Activar') + '"><i data-lucide="' + (o.is_active ? 'eye-off' : 'eye') + '" class="w-3 h-3"></i></button>' +
            '<button onclick="deleteFormOption(' + o.id + ')" aria-label="Eliminar ' + escapeHtml(o.label) + '" class="p-1.5 rounded hover:bg-rose-50 text-rose-600" title="Eliminar"><i data-lucide="trash-2" class="w-3 h-3"></i></button>' +
            '</div></td></tr>';
    }).join('');
    if (liveRegion) liveRegion.textContent = filtered.length + ' opcion' + (filtered.length !== 1 ? 'es' : '') + ' encontrada' + (filtered.length !== 1 ? 's' : '');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function openCreateOptionModal() {
    _formOptionModalPrevFocus = document.activeElement;
    var catOptions = FORM_OPTION_CATEGORIES.map(function(c) {
        return '<option value="' + c + '">' + c.replace(/_/g, ' ') + '</option>';
    }).join('');
    var html = '<div id="formOptionModal" class="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="fo-modal-title">' +
        '<div class="absolute inset-0 bg-midnight/60 backdrop-blur-sm" onclick="closeFormOptionModal()"></div>' +
        '<div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md max-h-[90vh] mx-4 sm:mx-0 flex flex-col">' +
        '<div class="bg-white rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-full">' +
        '<div class="border-t-4 border-gold px-4 sm:px-6 pt-6 pb-3 flex-shrink-0">' +
        '<h3 id="fo-modal-title" class="text-2xl font-serif">Nueva <span class="serif-italic">Opcion</span></h3>' +
        '</div>' +
        '<div class="px-4 sm:px-6 pb-6 space-y-3 overflow-y-auto min-h-0">' +
        '<div><label for="fo-category" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Categoria</label>' +
        '<select id="fo-category" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm">' + catOptions + '</select></div>' +
        '<div><label for="fo-value" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Valor</label>' +
        '<input id="fo-value" type="text" maxlength="100" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" placeholder="ej: departamento"></div>' +
        '<div><label for="fo-label" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Etiqueta</label>' +
        '<input id="fo-label" type="text" maxlength="200" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" placeholder="ej: Departamento"></div>' +
        '<div><label for="fo-icon-search" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Icono (opcional)</label>' +
        '<input id="fo-icon" type="hidden" value="">' +
        renderIconPicker('') + '</div>' +
        '<div><label for="fo-order" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Orden</label>' +
        '<input id="fo-order" type="number" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="0"></div>' +
        '<div class="flex gap-3 pt-2">' +
        '<button onclick="closeFormOptionModal()" class="flex-1 py-3 border border-midnight/20 rounded text-[10px] font-bold uppercase tracking-widest text-midnight hover:border-midnight transition-all">Cancelar</button>' +
        '<button id="fo-save-btn" onclick="saveFormOption()" class="flex-1 py-3 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">Guardar</button>' +
        '</div></div></div></div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
    _setupFormOptionModalFocusTrap();
    function _updateNextSortOrder() {
        var cat = document.getElementById('fo-category').value;
        var maxOrder = 0;
        allFormOptions.forEach(function(o) { if (o.category === cat && o.sort_order >= maxOrder) maxOrder = o.sort_order + 1; });
        document.getElementById('fo-order').value = maxOrder;
    }
    _updateNextSortOrder();
    document.getElementById('fo-category').addEventListener('change', _updateNextSortOrder);
    var firstInput = document.getElementById('fo-category');
    if (firstInput) firstInput.focus();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeFormOptionModal() {
    isFormOptionSaving = false;
    var m = document.getElementById('formOptionModal');
    if (m) m.remove();
    if (_formOptionModalPrevFocus && _formOptionModalPrevFocus.focus) {
        _formOptionModalPrevFocus.focus();
    }
}

function saveFormOption(editId) {
    if (isFormOptionSaving) return;
    var data = {
        category: document.getElementById('fo-category').value,
        value: document.getElementById('fo-value').value.trim(),
        label: document.getElementById('fo-label').value.trim(),
        icon: document.getElementById('fo-icon').value.trim(),
        sort_order: parseInt(document.getElementById('fo-order').value) || 0
    };
    if (!data.value || !data.label) {
        if (typeof showToast === 'function') showToast('Valor y etiqueta son requeridos', 'error');
        return;
    }
    isFormOptionSaving = true;
    var saveBtn = document.getElementById('fo-save-btn');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Guardando...'; }
    var url = editId ? '/api/form-options/' + editId : '/api/form-options';
    var method = editId ? 'PUT' : 'POST';
    fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
        .then(function(r) {
            if (!r.ok) return r.json().then(function(body) { throw new Error(body.error || 'HTTP ' + r.status); });
            return r.json();
        })
        .then(function(res) {
            if (res.error) {
                if (typeof showToast === 'function') showToast(res.error, 'error');
            } else {
                if (typeof showToast === 'function') showToast(editId ? 'Opcion actualizada' : 'Opcion creada', 'success');
                closeFormOptionModal();
                loadFormOptions();
            }
        })
        .catch(function(err) {
            if (typeof showToast === 'function') showToast(err.message || 'Error de conexion', 'error');
        })
        .finally(function() {
            isFormOptionSaving = false;
            var btn = document.getElementById('fo-save-btn');
            if (btn) { btn.disabled = false; btn.textContent = editId ? 'Actualizar' : 'Guardar'; }
        });
}

function editFormOption(id) {
    var opt = allFormOptions.find(function(o) { return o.id === id; });
    if (!opt) return;
    _formOptionModalPrevFocus = document.activeElement;
    var catOptions = FORM_OPTION_CATEGORIES.map(function(c) {
        return '<option value="' + c + '"' + (c === opt.category ? ' selected' : '') + '>' + c.replace(/_/g, ' ') + '</option>';
    }).join('');
    var html = '<div id="formOptionModal" class="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="fo-modal-title">' +
        '<div class="absolute inset-0 bg-midnight/60 backdrop-blur-sm" onclick="closeFormOptionModal()"></div>' +
        '<div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md max-h-[90vh] mx-4 sm:mx-0 flex flex-col">' +
        '<div class="bg-white rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-full">' +
        '<div class="border-t-4 border-gold px-4 sm:px-6 pt-6 pb-3 flex-shrink-0">' +
        '<h3 id="fo-modal-title" class="text-2xl font-serif">Editar <span class="serif-italic">Opcion</span></h3>' +
        '</div>' +
        '<div class="px-4 sm:px-6 pb-6 space-y-3 overflow-y-auto min-h-0">' +
        '<div><label for="fo-category" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Categoria</label>' +
        '<select id="fo-category" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" disabled>' + catOptions + '</select></div>' +
        '<div><label for="fo-value" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Valor</label>' +
        '<input id="fo-value" type="text" maxlength="100" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="' + escapeHtml(opt.value) + '"></div>' +
        '<div><label for="fo-label" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Etiqueta</label>' +
        '<input id="fo-label" type="text" maxlength="200" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="' + escapeHtml(opt.label) + '"></div>' +
        '<div><label for="fo-icon-search" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Icono</label>' +
        '<input id="fo-icon" type="hidden" value="' + escapeHtml(opt.icon || '') + '">' +
        renderIconPicker(opt.icon || '') + '</div>' +
        '<div><label for="fo-order" class="text-[10px] uppercase tracking-widest font-bold text-midnight/40">Orden</label>' +
        '<input id="fo-order" type="number" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="' + opt.sort_order + '"></div>' +
        '<div class="flex gap-3 pt-2">' +
        '<button onclick="closeFormOptionModal()" class="flex-1 py-3 border border-midnight/20 rounded text-[10px] font-bold uppercase tracking-widest text-midnight hover:border-midnight transition-all">Cancelar</button>' +
        '<button id="fo-save-btn" onclick="saveFormOption(' + id + ')" class="flex-1 py-3 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">Actualizar</button>' +
        '</div></div></div></div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
    _setupFormOptionModalFocusTrap();
    var firstInput = document.getElementById('fo-value');
    if (firstInput) firstInput.focus();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function toggleFormOption(id, newActive) {
    fetch('/api/form-options/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_active: newActive }) })
        .then(function(r) {
            if (!r.ok) return r.json().then(function(body) { throw new Error(body.error || 'HTTP ' + r.status); });
            return r.json();
        })
        .then(function(res) {
            if (res.error) {
                if (typeof showToast === 'function') showToast(res.error, 'error');
            } else {
                if (typeof showToast === 'function') showToast(newActive ? 'Opcion activada' : 'Opcion desactivada', 'success');
                loadFormOptions();
            }
        })
        .catch(function(err) {
            if (typeof showToast === 'function') showToast(err.message || 'Error de conexion', 'error');
        });
}

function deleteFormOption(id) {
    var promise = typeof showConfirm === 'function' ? showConfirm('Eliminar esta opcion?') : Promise.resolve(true);
    promise.then(function(ok) {
        if (!ok) return;
        fetch('/api/form-options/' + id, { method: 'DELETE' })
            .then(function(r) {
                if (!r.ok) return r.json().then(function(body) { throw new Error(body.error || 'HTTP ' + r.status); });
                return r.json();
            })
            .then(function(res) {
                if (res.error) {
                    if (typeof showToast === 'function') showToast(res.error, 'error');
                } else {
                    if (typeof showToast === 'function') showToast('Opcion eliminada', 'success');
                    loadFormOptions();
                }
            })
            .catch(function(err) {
                if (typeof showToast === 'function') showToast(err.message || 'Error de conexion', 'error');
            });
    });
}

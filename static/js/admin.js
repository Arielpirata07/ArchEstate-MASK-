// ---- Tab switching ----
function showTab(tab) {
    document.getElementById('panel-dashboard').classList.add('hidden');
    document.getElementById('panel-management').classList.add('hidden');
    document.getElementById('panel-reports').classList.add('hidden');
    document.getElementById('panel-form-options').classList.add('hidden');
    document.getElementById('panel-phone-area-codes').classList.add('hidden');
    document.getElementById('panel-notifications').classList.add('hidden');
    document.getElementById('panel-' + tab).classList.remove('hidden');
    const activePanel = document.getElementById('panel-' + tab);
    activePanel.classList.remove('panel-enter');
    void activePanel.offsetWidth;
    activePanel.classList.add('panel-enter');

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
    if (tab === 'phone-area-codes') {
        loadPhoneAreaCodes();
    }
    if (tab === 'notifications') {
        loadAdminNotifPrefs();
        loadNotificationLog(1);
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

// ---- Collapsible sections ----
function toggleSection(id) {
    var body = document.getElementById(id + '-body');
    var chevron = document.getElementById(id + '-chevron');
    if (!body) return;
    body.classList.toggle('hidden');
    if (chevron) chevron.classList.toggle('-rotate-90');
}

// ---- Período ----
function setPeriod(days) {
    dashState.period = days;
    document.querySelectorAll('.period-btn').forEach(btn => {
        const active = parseInt(btn.dataset.period) === days;
        btn.className = 'period-btn px-3 py-1 rounded text-[10px] font-bold uppercase tracking-widest transition-all '
            + (active ? 'bg-midnight text-white' : 'bg-paper-dark text-midnight hover:bg-gold hover:text-white');
    });
    initDashboard();
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
                hoverOffset: 10,
                hoverBorderWidth: 2,
                hoverBorderColor: getPalette().dark[0],
                borderRadius: isDoughnut ? 0 : 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: isDoughnut ? '68%' : undefined,
            plugins: {
                legend: {
                    display: isDoughnut,
                    position: 'bottom',
                    labels: { font: baseFont, boxWidth: 14, padding: 14, usePointStyle: true, pointStyle: 'circle' }
                },
                tooltip: {
                    backgroundColor: isDarkMode() ? '#1a2332' : '#fff',
                    titleFont: { family: 'Manrope', size: 11, weight: 'bold' },
                    titleColor: isDarkMode() ? '#FAF9F7' : '#000410',
                    bodyFont: { family: 'Manrope', size: 10 },
                    bodyColor: isDarkMode() ? '#C4A882' : '#735A3A',
                    borderColor: isDarkMode() ? 'rgba(255,255,255,0.08)' : 'rgba(0,4,16,0.08)',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct   = total ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            const val   = ctx.parsed.toLocaleString('es-AR');
                            return `  ${ctx.label}: ${val} (${pct}%)`;
                        }
                    }
                }
            },
            scales: isDoughnut ? {} : {
                x: { ticks: { font: { family: 'Manrope', size: 9 } }, grid: { display: false } },
                y: {
                    ticks: { font: baseFont, stepSize: 1, callback: v => v.toLocaleString('es-AR') },
                    grid: { color: chartGridColor() },
                    beginAtZero: true
                }
            },
            animation: chartAnim()
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

    const all = data.leads_by_month;
    if (!all || !all.length) return;

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
            labels: labels.length ? labels : [t('dashboard.this_month')],
            datasets: [{
                label: t('dashboard.leads'),
                data:  values.length ? values : [data.total_leads],
                borderColor: getPalette().gold[0],
                backgroundColor: isLine
                    ? (function(ctx) {
                        if (!ctx || !ctx.chart || !ctx.chart.chartArea) return getPalette().gold[0] + '30';
                        var chart = ctx.chart;
                        if (!chart.chartArea) return getPalette().gold[0] + '30';
                        var gradient = chart.ctx.createLinearGradient(0, chart.chartArea.top, 0, chart.chartArea.bottom);
                        gradient.addColorStop(0, getPalette().gold[0] + '30');
                        gradient.addColorStop(1, getPalette().gold[0] + '04');
                        return gradient;
                      })
                    : getPalette().gold[0],
                fill: isLine,
                tension: 0.35,
                pointBackgroundColor: getPalette().gold[0],
                pointBorderColor: isDarkMode() ? '#1a2332' : '#fff',
                pointBorderWidth: 2,
                pointRadius: isLine ? 5 : 0,
                pointHoverRadius: isLine ? 8 : 0,
                pointHoverBorderWidth: 3,
                pointHoverBorderColor: getPalette().dark[0],
                borderWidth: 2,
                borderRadius: isLine ? 0 : 4,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: isDarkMode() ? '#1a2332' : '#fff',
                    titleFont: { family: 'Manrope', size: 11, weight: 'bold' },
                    titleColor: isDarkMode() ? '#FAF9F7' : '#000410',
                    bodyFont: { family: 'Manrope', size: 10 },
                    bodyColor: isDarkMode() ? '#C4A882' : '#735A3A',
                    borderColor: isDarkMode() ? 'rgba(255,255,255,0.08)' : 'rgba(0,4,16,0.08)',
                    borderWidth: 1,
                    padding: 8,
                    cornerRadius: 6,
                    callbacks: { label: ctx => `  ${ctx.parsed.y.toLocaleString('es-AR')} leads` }
                }
            },
            scales: {
                x: { ticks: { font: baseFont }, grid: { color: chartGridColor() } },
                y: {
                    ticks: { font: baseFont, stepSize: 1, callback: v => v.toLocaleString('es-AR') },
                    grid: { color: chartGridColor() },
                    beginAtZero: true
                }
            },
            animation: chartAnim()
        }
    });
}

// ---- Init principal ----
async function initDashboard() {
    try {
        const res  = await fetch('/api/admin/stats?period=' + dashState.period);
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
        document.getElementById('kpi-pros-approved-pct').textContent = totalPros ? t('dashboard.pct_of_total', {pct: pct}) : '';
        document.getElementById('kpi-pending-label').textContent     = (pending?.value || 0) > 0 ? t('dashboard.requires_review') : '';

        const totalAudit = data.audit_actions.reduce((sum, a) => sum + a.value, 0);
        animateCounter(document.getElementById('kpi-audit'), totalAudit);
        const topAction = data.audit_actions[0];
        document.getElementById('kpi-audit-sub').textContent = topAction ? `${topAction.label}: ${topAction.value}` : '';

        animateCounter(document.getElementById('kpi-phones'), data.phone_reveals || 0);
        const phoneClicks = data.phone_clicks || 0;
        const phoneReveals = data.phone_reveals || 0;
        const phoneRate = phoneClicks ? Math.round(phoneReveals / phoneClicks * 100) : 0;
        document.getElementById('kpi-phones-rate').textContent = phoneClicks ? t('dashboard.phone_success_rate', {rate: phoneRate}) : '';

        // Gráficos (solo si Chart.js cargó correctamente)
        if (typeof Chart !== 'undefined') {
            renderTypeChart();

            // Zona
            destroyChart('zone');
            charts['zone'] = new Chart(document.getElementById('chart-zone'), {
                type: 'bar',
                data: {
                    labels: data.leads_by_zone.map(d => d.label),
                    datasets: [{
                        label: t('dashboard.leads'),
                        data: data.leads_by_zone.map(d => d.value),
                        backgroundColor: getPalette().dark,
                        borderRadius: 4,
                        borderSkipped: false,
                        hoverBackgroundColor: getPalette().gold,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: isDarkMode() ? '#1a2332' : '#fff',
                            titleFont: { family: 'Manrope', size: 11, weight: 'bold' },
                            titleColor: isDarkMode() ? '#FAF9F7' : '#000410',
                            bodyFont: { family: 'Manrope', size: 10 },
                            bodyColor: isDarkMode() ? '#C4A882' : '#735A3A',
                            borderColor: isDarkMode() ? 'rgba(255,255,255,0.08)' : 'rgba(0,4,16,0.08)',
                            borderWidth: 1,
                            padding: 8,
                            cornerRadius: 6,
                            callbacks: {
                                label: ctx => `  ${ctx.parsed.x.toLocaleString('es-AR')} leads`
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { font: baseFont, stepSize: 1, callback: v => v.toLocaleString('es-AR') },
                            grid: { color: chartGridColor() }
                        },
                        y: { ticks: { font: { family: 'Manrope', size: 9 } }, grid: { display: false } }
                    },
                    animation: chartAnim()
                }
            });

            renderMonthChart();

            // Presupuesto
            destroyChart('budget');
            charts['budget'] = new Chart(document.getElementById('chart-budget'), {
                type: 'bar',
                data: {
                    labels: data.leads_by_budget.map(d => d.label),
                    datasets: [{
                        label: t('dashboard.leads'),
                        data: data.leads_by_budget.map(d => d.value),
                        backgroundColor: getPalette().mixed,
                        borderRadius: 4,
                        borderSkipped: false,
                        hoverBackgroundColor: getPalette().gold,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: isDarkMode() ? '#1a2332' : '#fff',
                            titleFont: { family: 'Manrope', size: 11, weight: 'bold' },
                            titleColor: isDarkMode() ? '#FAF9F7' : '#000410',
                            bodyFont: { family: 'Manrope', size: 10 },
                            bodyColor: isDarkMode() ? '#C4A882' : '#735A3A',
                            borderColor: isDarkMode() ? 'rgba(255,255,255,0.08)' : 'rgba(0,4,16,0.08)',
                            borderWidth: 1,
                            padding: 8,
                            cornerRadius: 6,
                            callbacks: { label: ctx => `  ${ctx.parsed.y.toLocaleString('es-AR')} leads` }
                        }
                    },
                    scales: {
                        x: { ticks: { font: { family: 'Manrope', size: 8, weight: 'bold' }, maxRotation: 30 }, grid: { display: false } },
                        y: {
                            ticks: { font: baseFont, stepSize: 1, callback: v => v.toLocaleString('es-AR') },
                            grid: { color: chartGridColor() },
                            beginAtZero: true
                        }
                    },
                    animation: chartAnim()
                }
            });
        } else {
            console.warn('Chart.js no está disponible. Los gráficos no se renderizarán.');
        }

        if (window.lucide) lucide.createIcons();
        loadTelemetry();

    } catch (err) {
        console.error('Error cargando estadísticas:', err);
    }
}

async function loadTelemetry() {
    var periodMap = {0: '0', 7: '7d', 30: '30d', 90: '90d', 365: '1y'};
    var p = periodMap[dashState.period] || '30d';
    var loadingEl = document.getElementById('tm-loading');
    var loadedEl = document.getElementById('tm-loaded');
    var emptyEl = document.getElementById('tm-empty');
    if (!loadedEl) return;
    loadedEl.classList.add('hidden');
    emptyEl.classList.add('hidden');
    loadingEl.classList.remove('hidden');
    try {
        var res = await fetch('/api/admin/telemetry?period=' + p);
        var data = await res.json();
        loadingEl.classList.add('hidden');
        if (!data.success) { emptyEl.classList.remove('hidden'); return; }
        var m = data.metrics || {};
        var c = m.phone_clicks || 0;
        var r = m.phone_revealed || 0;
        var tc = m.tel_clicks || 0;
        if (c === 0 && r === 0 && tc === 0) {
            emptyEl.classList.remove('hidden');
            return;
        }
        emptyEl.classList.add('hidden');
        loadedEl.classList.remove('hidden');
        animateCounter(document.getElementById('tm-phone-clicks'), c);
        animateCounter(document.getElementById('tm-phone-revealed'), r);
        var rateEl = document.getElementById('tm-phone-rate');
        var rate = m.phone_success_rate_pct != null ? m.phone_success_rate_pct : 0;
        rateEl.textContent = rate > 0 ? t('dashboard.success_rate', {rate: rate}) : '—';
        var telEl = document.getElementById('tm-tel-clicks');
        telEl.innerHTML = '<i data-lucide="phone" class="w-2.5 h-2.5"></i> <span>' + t('dashboard.call_clicks', {count: tc}) + '</span>';
        animateCounter(document.getElementById('tm-wa-clicks'), m.wa_button_clicks || 0);
        var ctrEl = document.getElementById('tm-wa-ctr');
        var ctr = m.wa_click_through_rate_pct != null ? m.wa_click_through_rate_pct : 0;
        ctrEl.textContent = ctr > 0 ? ctr + '%' : '—';
        animateCounter(document.getElementById('tm-otp-sent'), m.otp_sent || 0);
        animateCounter(document.getElementById('tm-otp-verified'), m.otp_verified || 0);
        if (typeof Chart !== 'undefined' && data.phone_daily && data.phone_daily.length > 0) {
            var sparkCanvas = document.getElementById('sparkline-phone');
            if (sparkCanvas) {
                var sparkCtx = sparkCanvas.getContext('2d');
                if (sparkCtx) {
                    var dm = isDarkMode();
                    var lineColor = dm ? '#A68A64' : '#735A3A';
                    var fillTop = dm ? 'rgba(166,138,100,0.20)' : 'rgba(115,90,58,0.20)';
                    var fillBot = dm ? 'rgba(166,138,100,0.01)' : 'rgba(115,90,58,0.01)';
                    new Chart(sparkCtx, {
                        type: 'line',
                        data: {
                            labels: data.phone_daily.map(function(d) { return d.day; }),
                            datasets: [{
                                data: data.phone_daily.map(function(d) { return d.count; }),
                                borderColor: lineColor,
                                borderWidth: 1.5,
                                backgroundColor: function(ctx) {
                                    if (!ctx.chart.chartArea) return fillTop;
                                    var g = ctx.chart.chartArea;
                                    var grad = ctx.chart.ctx.createLinearGradient(0, g.top, 0, g.bottom);
                                    grad.addColorStop(0, fillTop);
                                    grad.addColorStop(1, fillBot);
                                    return grad;
                                },
                                fill: true,
                                pointRadius: 0,
                                pointHoverRadius: 2,
                                tension: 0.3,
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: false }, tooltip: { enabled: false } },
                            scales: {
                                x: { display: false },
                                y: { display: false, beginAtZero: true }
                            },
                            animation: chartAnim(400)
                        }
                    });
                }
            }
        }
        if (window.lucide) lucide.createIcons();
    } catch (err) {
        loadingEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        console.error('Error cargando telemetría:', err);
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
            showProError(data.error || t('error.pros_load'));
        }
    } catch (error) {
        console.error('Error loading professionals:', error);
        showProError(t('error.connection'));
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
                    <p>${t('pros.not_found')}</p>
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
            statusBadge = '<span class="px-2 py-1 bg-emerald-50 text-emerald-700 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.approved') + '</span>';
        } else if (pro.status === 'rejected') {
            statusBadge = '<span class="px-2 py-1 bg-rose-50 text-rose-700 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.rejected') + '</span>';
        } else {
            statusBadge = '<span class="px-2 py-1 bg-amber-50 text-amber-700 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.pending') + '</span>';
        }

        // Badge de estado de cuenta (activa / baja)
        // is_active: 1=activo, 0=baja, null=campo no devuelto por la API → asumir activo
        const hasUser  = pro.user_id !== null && pro.user_id !== undefined;
        const rawActive = pro.is_active;
        const isActive  = !hasUser ? null
                        : (rawActive === null || rawActive === undefined) ? true
                        : rawActive !== 0;

        const accountBadge = isActive === false
            ? '<span class="ml-1 px-2 py-1 bg-midnight/10 text-midnight/50 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.account_disabled') + '</span>'
            : '';

        // Botones de aprobación/rechazo (deshabilitados si cuenta dada de baja o sin usuario)
        let approvalActions = '';
        if (!hasUser || isActive === false) {
            approvalActions = '<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest">—</span>';
        } else if (pro.status === 'pending') {
            approvalActions = `
                <button onclick="updateProStatus('${pro.id}', 'approved', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-emerald-100 transition-colors">
                    <i data-lucide="check" class="w-3 h-3"></i> ${t('action.approve')}
                </button>
                <button onclick="updateProStatus('${pro.id}', 'rejected', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-rose-50 text-rose-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-rose-100 transition-colors">
                    <i data-lucide="x" class="w-3 h-3"></i> ${t('action.reject')}
                </button>`;
        } else if (pro.status === 'approved') {
            approvalActions = `
                <button onclick="updateProStatus('${pro.id}', 'rejected', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-rose-50 text-rose-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-rose-100 transition-colors">
                    <i data-lucide="x" class="w-3 h-3"></i> ${t('action.disapprove')}
                </button>`;
        } else if (pro.status === 'rejected') {
            approvalActions = `
                <button onclick="updateProStatus('${pro.id}', 'approved', this)"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-emerald-100 transition-colors">
                    <i data-lucide="check" class="w-3 h-3"></i> ${t('action.approve')}
                </button>`;
        }

        // Botón de baja/reactivación — solo si hay usuario vinculado
        let accountBtn = '';
        if (!hasUser) {
            accountBtn = '<span class="text-[10px] text-midnight/20 italic">' + t('pros.no_account') + '</span>';
        } else if (isActive !== false) {
            accountBtn = `<button data-user-id="${pro.user_id}" data-user-name="${escapeHtml(pro.name)}" data-activate="false"
                   class="toggle-active-btn inline-flex items-center gap-1 px-2 py-1 bg-midnight/5 text-midnight/50 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-rose-50 hover:text-rose-600 transition-colors">
                   <i data-lucide="user-x" class="w-3 h-3"></i> ${t('action.disable')}
               </button>`;
        } else {
            accountBtn = `<button data-user-id="${pro.user_id}" data-user-name="${escapeHtml(pro.name)}" data-activate="true"
                   class="toggle-active-btn inline-flex items-center gap-1 px-2 py-1 bg-midnight/5 text-midnight/50 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-emerald-50 hover:text-emerald-600 transition-colors">
                   <i data-lucide="user-check" class="w-3 h-3"></i> ${t('action.reactivate')}
               </button>`;
        }

        const docCell = pro.doc_path
            ? `<a href="/admin/download_doc/${pro.user_id}" class="inline-flex items-center gap-2 px-2 py-1 bg-gold text-white rounded font-bold uppercase tracking-widest text-[9px] hover:bg-midnight transition-colors">
                   <i data-lucide="download" class="w-3 h-3"></i> ${t('action.download')}
               </a>`
            : '<span class="text-midnight/30 text-[10px] uppercase italic">' + t('pros.no_document') + '</span>';

        const rowOpacity = isActive === false ? 'opacity-60' : '';

        return `
            <tr class="border-b border-midnight/[0.03] hover:bg-paper transition-colors ${rowOpacity}">
                <td class="px-4 py-3 text-[13px]">
                    <div class="font-medium text-midnight">${escapeHtml(pro.name)} ${accountBadge}</div>
                    <div class="text-[11px] text-midnight/60 italic">${escapeHtml(pro.specialty || '')}</div>
                </td>
                <td class="px-4 py-3 font-mono text-[11px] text-midnight/60">${escapeHtml(pro.license)}</td>
                <td class="px-4 py-3">${statusBadge}</td>
                <td class="px-4 py-3">${docCell}</td>
                <td class="px-4 py-3 text-right">
                    <div class="flex justify-end items-center gap-2 flex-wrap">
                        ${approvalActions}
                        <button onclick="openNotifyModal('${pro.id}', '${escapeHtml(pro.name)}')"
                            class="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded font-bold uppercase tracking-widest text-[9px] hover:bg-blue-100 transition-colors">
                            <i data-lucide="bell" class="w-3 h-3"></i> ${t('admin.send_notification_to')}
                        </button>
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
        tag.textContent  = t('admin.admin_action');
        title.innerHTML  = t('admin.reactivate_account');
        warning.className = 'mx-8 mb-6 p-3 bg-emerald-50 border border-emerald-100 rounded flex items-start gap-3';
        warning.innerHTML = `
            <i data-lucide="info" class="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5"></i>
            <p id="deactivateModalWarningText" class="text-[10px] text-emerald-700 font-bold uppercase tracking-wider leading-relaxed">
                ${t('admin.reactivate_warning')}
            </p>`;
        btn.className    = 'flex-1 py-3 bg-emerald-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all flex items-center justify-center gap-2';
        btn.innerHTML    = '<i data-lucide="user-check" class="w-3 h-3"></i><span id="confirmDeactivateBtnLabel">' + t('admin.reactivate_account_btn') + '</span>';
        reasonW.classList.add('hidden');
    } else {
        header.className = 'border-t-4 border-rose-500 px-8 pt-8 pb-4';
        tag.className    = 'text-[10px] uppercase tracking-widest font-bold text-rose-500 mb-1';
        tag.textContent  = t('admin.admin_action');
        title.innerHTML  = t('admin.disable_account');
        warning.className = 'mx-8 mb-6 p-3 bg-rose-50 border border-rose-100 rounded flex items-start gap-3';
        warning.innerHTML = `
            <i data-lucide="alert-triangle" class="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5"></i>
            <p id="deactivateModalWarningText" class="text-[10px] text-rose-700 font-bold uppercase tracking-wider leading-relaxed">
                ${t('admin.disable_warning')}
            </p>`;
        btn.className    = 'flex-1 py-3 bg-rose-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all flex items-center justify-center gap-2';
        btn.innerHTML    = '<i data-lucide="user-x" class="w-3 h-3"></i><span id="confirmDeactivateBtnLabel">' + t('admin.disable_account_btn') + '</span>';
        reasonW.classList.remove('hidden');
    }

    openModalAnim(document.getElementById('deactivateModal'));
    document.body.style.overflow = 'hidden';
    if (window.lucide) lucide.createIcons();
}

function closeDeactivateModal() {
    closeModalAnim(document.getElementById('deactivateModal'));
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

// ---- Notificaciones a profesionales ----
let notifyTargetId = null;

function openNotifyModal(proId, proName) {
    notifyTargetId = proId;
    document.getElementById('notifyModalProName').textContent = proName;
    document.getElementById('notifySubject').value = '';
    document.getElementById('notifyMessage').value = '';
    document.getElementById('notifyModalError').classList.add('hidden');
    openModalAnim(document.getElementById('notifyModal'));
    document.body.style.overflow = 'hidden';
    setTimeout(() => document.getElementById('notifySubject').focus(), 100);
}

function closeNotifyModal() {
    closeModalAnim(document.getElementById('notifyModal'));
    document.body.style.overflow = '';
    notifyTargetId = null;
}

async function confirmNotify() {
    if (!notifyTargetId) return;
    const btn = document.getElementById('confirmNotifyBtn');
    const errEl = document.getElementById('notifyModalError');
    const orig = btn.innerHTML;
    errEl.classList.add('hidden');

    const title = document.getElementById('notifySubject').value.trim();
    const body = document.getElementById('notifyMessage').value.trim();

    if (!title) {
        errEl.textContent = t('admin.notification_title_required');
        errEl.classList.remove('hidden');
        return;
    }

    btn.innerHTML = '<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div> ' + t('action.processing');
    btn.disabled = true;

    try {
        const res = await fetch('/api/admin/send-notification', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: notifyTargetId, title: title, body: body })
        });
        const data = await res.json();

        if (res.ok) {
            closeNotifyModal();
            if (typeof showToast === 'function') showToast(data.message);
        } else {
            errEl.textContent = data.error || t('error.process_request');
            errEl.classList.remove('hidden');
        }
    } catch (err) {
        errEl.textContent = t('error.connection_retry');
        errEl.classList.remove('hidden');
    } finally {
        btn.innerHTML = orig;
        btn.disabled = false;
    }
}

async function confirmDeactivate() {
    if (deactivateTargetId === null) return;

    const btn    = document.getElementById('confirmDeactivateBtn');
    const errEl  = document.getElementById('deactivateModalError');
    const orig   = btn.innerHTML;
    errEl.classList.add('hidden');

    btn.innerHTML = '<div class="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div> ' + t('action.processing');
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
            errEl.textContent = data.error || t('error.process_request');
            errEl.classList.remove('hidden');
            btn.innerHTML = orig;
            btn.disabled  = false;
        }
    } catch (err) {
        errEl.textContent = t('error.connection_retry');
        errEl.classList.remove('hidden');
        btn.innerHTML = orig;
        btn.disabled  = false;
    }
}

/**
 * Gestion de Reportes de Leads
 */
let currentReportsPage = 1;
let currentReportsFilter = 'pending';

function loadReports(filter, page) {
    if (filter !== undefined) currentReportsFilter = filter;
    if (page !== undefined) currentReportsPage = page;

    var params = new URLSearchParams();
    params.set('page', currentReportsPage);
    params.set('per_page', '25');
    if (currentReportsFilter !== 'all') params.set('status', currentReportsFilter);

    fetch('/api/admin/reports?' + params.toString())
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                renderReportsKPIs(data);
                renderReports(data.reports);
                updateReportBadge(data.status_counts);
                renderReportsPagination(data.total, data.page, data.per_page);
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
    currentReportsFilter = filter;
    currentReportsPage = 1;
    document.querySelectorAll('.report-filter-chip').forEach(chip => {
        chip.classList.toggle('report-filter-active', chip.dataset.filter === filter);
    });
    loadReports();
}

function loadReportsPage(page) {
    if (page < 1) return;
    currentReportsPage = page;
    loadReports();
}

function renderReportsPagination(total, page, perPage) {
    var paginationEl = document.getElementById('reports-pagination');
    if (!paginationEl) return;
    var totalPages = Math.ceil(total / perPage);
    if (totalPages <= 1) { paginationEl.classList.add('hidden'); return; }
    paginationEl.classList.remove('hidden');

    var infoEl = document.getElementById('reports-page-info');
    var prevBtn = document.getElementById('reports-prev');
    var nextBtn = document.getElementById('reports-next');
    var indicator = document.getElementById('reports-page-indicator');

    if (infoEl) infoEl.textContent = t('pagination.reports_page', {page: page, totalPages: totalPages, total: total});
    if (prevBtn) {
        prevBtn.disabled = page <= 1;
        prevBtn.classList.toggle('disabled\\:opacity-30', page <= 1);
    }
    if (nextBtn) {
        nextBtn.disabled = page >= totalPages;
        nextBtn.classList.toggle('disabled\\:opacity-30', page >= totalPages);
    }
    if (indicator) indicator.textContent = page + ' / ' + totalPages;
}

function renderReports(reports) {
    const tbody = document.getElementById('reportsTableBody');

    if (!reports.length) {
        tbody.innerHTML = `
            <tr><td colspan="10" class="p-12 text-center text-midnight/60">
                <i data-lucide="check-circle" class="w-10 h-10 mx-auto mb-3 text-emerald-200"></i>
                <p class="font-semibold text-midnight/60">${t('reports.empty')}</p>
            </td></tr>`;
        if (window.lucide) lucide.createIcons();
        return;
    }

    tbody.innerHTML = reports.map(r => {
        const statusBadge = r.status === 'pending'
            ? '<span class="px-2 py-1 bg-amber-50 text-amber-700 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.pending') + '</span>'
            : r.status === 'dismissed'
            ? '<span class="px-2 py-1 bg-paper-dark text-midnight/60 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.dismissed') + '</span>'
            : '<span class="px-2 py-1 bg-rose-50 text-rose-600 text-[9px] font-bold uppercase tracking-widest rounded">' + t('status.deleted') + '</span>';

        let actions;
        if (r.status === 'pending') {
            actions = `<div class="flex justify-end gap-2 flex-wrap">
                    <button onclick="viewLeadDetail(${r.lead_id})" class="px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                        ${t('action.view_lead')}
                    </button>
                    <button onclick="deleteLead(${r.id}, ${r.lead_id})" class="px-3 py-2 bg-rose-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all">
                        ${t('action.delete')}
                    </button>
                    <button onclick="dismissReport(${r.id})" class="px-3 py-2 bg-paper-dark text-midnight rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold hover:text-white transition-all">
                        ${t('action.dismiss')}
                    </button>
               </div>`;
        } else {
            actions = `<div class="flex justify-end gap-2 flex-wrap">
                    ${r.lead_id ? `<button onclick="viewLeadDetail(${r.lead_id})" class="px-3 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">${t('action.view_lead')}</button>` : ''}
                    <button onclick="restoreReport(${r.id})" class="px-3 py-2 bg-emerald-600 text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-midnight transition-all">
                        ${t('action.restore')}
                    </button>
               </div>`;
        }

        return `
            <tr class="border-b border-midnight/[0.03] hover:bg-paper transition-colors ${r.status === 'deleted' ? 'opacity-60' : ''}">
                <td class="px-4 py-3 font-mono text-[11px] text-midnight/60">#${r.lead_id}</td>
                <td class="px-4 py-3 text-[13px] text-midnight/50">${r.lead_type ? escapeHtml(r.lead_type) : '<span class="text-midnight/30">' + t('reports.lead_deleted') + '</span>'}</td>
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
    openModalAnim(document.getElementById('leadDetailModal'));
    if (window.lucide) lucide.createIcons();

    fetch(`/api/admin/lead/${leadId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                renderLeadDetail(data.lead);
            } else {
                document.getElementById('leadDetailContent').innerHTML = `
                    <p class="text-center text-rose-600 py-8">${escapeHtml(data.error || t('error.load'))}</p>`;
            }
        })
        .catch(() => {
            document.getElementById('leadDetailContent').innerHTML = `
                <p class="text-center text-rose-600 py-8">${t('error.connection')}</p>`;
        });
}

function renderLeadDetail(lead) {
    const sym = lead.currency === 'USD' ? 'US$' : lead.currency === 'EUR' ? '€' : '$';
    const budget = `${sym}${lead.budget}`;
    const style = lead.architectural_style || t('detail.not_specified');
    const amenities = lead.amenities
        ? lead.amenities.split(',').map(a => `
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 bg-gold rounded-full"></span>
                <p class="text-sm text-midnight">${escapeHtml(a.trim())}</p>
            </div>`).join('')
        : '<p class="text-sm text-midnight/50">' + t('detail.not_specified_pl') + '</p>';

    let typeDetails = '';
    if (lead.property_type === 'departamento') {
        typeDetails = `
            <div class="border-t border-midnight/10 pt-5 mt-5">
                <p class="text-[10px] uppercase tracking-widest text-midnight/60 font-bold mb-3">${t('detail.department')}</p>
                <div class="grid grid-cols-2 gap-4">
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.floor_block')}</p><p class="text-sm text-midnight">${escapeHtml(lead.floor_block || t('detail.not_specified'))}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.useful_meters')}</p><p class="text-sm text-midnight">${lead.usable_m2 ? lead.usable_m2 + ' m²' : t('detail.not_specified')}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.elevator')}</p><p class="text-sm text-midnight">${escapeHtml(lead.elevator || t('detail.not_specified'))}</p></div>
                </div>
            </div>`;
    } else if (lead.property_type === 'casa') {
        typeDetails = `
            <div class="border-t border-midnight/10 pt-5 mt-5">
                <p class="text-[10px] uppercase tracking-widest text-midnight/60 font-bold mb-3">${t('detail.house')}</p>
                <div class="grid grid-cols-2 gap-4">
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.land')}</p><p class="text-sm text-midnight">${lead.land_area ? lead.land_area + ' m²' : t('detail.not_specified')}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.built')}</p><p class="text-sm text-midnight">${lead.built_area ? lead.built_area + ' m²' : t('detail.not_specified')}</p></div>
                    <div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.pool')}</p><p class="text-sm text-midnight">${escapeHtml(lead.pool || t('detail.not_specified'))}</p></div>
                </div>
            </div>`;
    }

    document.getElementById('leadDetailContent').innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-4">
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.operation_type')}</p><p class="text-base font-semibold text-midnight">${escapeHtml(lead.type)}</p></div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.property_type')}</p><p class="text-base text-midnight">${escapeHtml(lead.property_type || t('detail.not_specified'))}</p></div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.zone')}</p><p class="text-base text-midnight">${escapeHtml(lead.zone)}</p></div>
                ${lead.province ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.province')}</p><p class="text-base text-midnight">${escapeHtml(lead.province)}</p></div>` : ''}
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.budget')}</p><p class="text-base font-serif italic text-gold">${budget}</p></div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.arch_style')}</p><p class="text-base text-midnight">${escapeHtml(style)}</p></div>
                ${lead.ambientes ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.rooms')}</p><p class="text-base text-midnight">${escapeHtml(String(lead.ambientes))}</p></div>` : ''}
                ${lead.parking ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.parking')}</p><p class="text-base text-midnight">${escapeHtml(lead.parking)}</p></div>` : ''}
                ${lead.orientation ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.orientation')}</p><p class="text-base text-midnight">${escapeHtml(lead.orientation)}</p></div>` : ''}
                ${lead.property_condition ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.condition')}</p><p class="text-base text-midnight">${escapeHtml(lead.property_condition)}</p></div>` : ''}
                ${lead.property_age ? `<div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.age')}</p><p class="text-base text-midnight">${escapeHtml(lead.property_age)}</p></div>` : ''}
                <div class="border-t border-midnight/10 pt-4">
                    <p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-2">${t('detail.contact')}</p>
                    <div class="flex items-center gap-2 text-sm text-midnight"><i data-lucide="mail" class="w-4 h-4 text-gold flex-shrink-0"></i><span>${escapeHtml(lead.email)}</span></div>
                    <div class="flex items-center gap-2 text-sm text-midnight mt-1"><i data-lucide="phone" class="w-4 h-4 text-gold flex-shrink-0"></i><span>${escapeHtml(lead.phone)}</span></div>
                </div>
                <div><p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.registered')}</p><p class="text-sm text-midnight">${lead.timestamp}</p></div>
            </div>
            <div class="space-y-4">
                <p class="text-lg font-serif text-midnight">${t('detail.technical_specs')}</p>
                <div class="grid grid-cols-3 gap-4">
                    <div class="text-center"><p class="text-[9px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.bedrooms')}</p><p class="text-2xl font-serif text-midnight">${lead.bedrooms || '-'}</p></div>
                    <div class="text-center"><p class="text-[9px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.bathrooms')}</p><p class="text-2xl font-serif text-midnight">${lead.bathrooms || '-'}</p></div>
                    <div class="text-center"><p class="text-[9px] uppercase tracking-widest text-gold font-bold mb-1">${t('detail.meters')}</p><p class="text-2xl font-serif text-midnight">${lead.total_area || lead.land_area || lead.usable_m2 || '-'}</p>${(lead.total_area || lead.land_area || lead.usable_m2) ? '<p class="text-[9px] text-midnight/60">m²</p>' : ''}</div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    ${lead.usable_m2 ? `<div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.useful_meters')}</p><p class="text-sm text-midnight">${lead.usable_m2} m²</p></div>` : ''}
                    ${lead.built_area ? `<div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.built')}</p><p class="text-sm text-midnight">${lead.built_area} m²</p></div>` : ''}
                    ${lead.land_area ? `<div><p class="text-[9px] uppercase tracking-widest text-midnight/60 font-bold">${t('detail.land')}</p><p class="text-sm text-midnight">${lead.land_area} m²</p></div>` : ''}
                </div>
                <div class="border-t border-midnight/10 pt-4">
                    <p class="text-[10px] uppercase tracking-widest text-gold font-bold mb-3">${t('detail.extras')}</p>
                    <div class="space-y-1.5">${amenities}</div>
                </div>
                ${typeDetails}
            </div>
        </div>`;

    if (window.lucide) lucide.createIcons();
}

function closeLeadDetailModal() {
    closeModalAnim(document.getElementById('leadDetailModal'));
}

function deleteLead(reportId, leadId) {
    var promise = typeof showConfirm === 'function' ? showConfirm(t('confirm.delete_lead', {id: leadId})) : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
    fetch('/api/admin/report/' + reportId + '/delete', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') showToast(t('success.lead_deleted'), 'success');
                loadReports(undefined, 1);
                if (typeof refreshDashboard === 'function') refreshDashboard();
            } else {
                if (typeof showToast === 'function') showToast(data.error || t('error.delete'), 'error');
            }
        })
        .catch(() => {
            if (typeof showToast === 'function') showToast(t('error.connection'), 'error');
        });
    });
}

function dismissReport(reportId) {
    fetch(`/api/admin/report/${reportId}/dismiss`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                if (typeof showToast === 'function') showToast(t('success.report_dismissed'), 'success');
                loadReports(undefined, 1);
            } else {
                if (typeof showToast === 'function') showToast(data.error || t('error.generic'), 'error');
            }
        })
        .catch(() => {
            if (typeof showToast === 'function') showToast(t('error.connection'), 'error');
        });
}

function restoreReport(reportId) {
    var promise = typeof showConfirm === 'function' ? showConfirm(t('confirm.restore_report')) : Promise.resolve(true);
    promise.then(function (ok) {
        if (!ok) return;
        fetch('/api/admin/report/' + reportId + '/restore', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                if (typeof showToast === 'function') showToast(t('success.report_restored'), 'success');
                loadReports(undefined, 1);
                if (typeof refreshDashboard === 'function') refreshDashboard();
            } else {
                if (typeof showToast === 'function') showToast(data.error || t('error.restore'), 'error');
            }
        })
        .catch(function () {
            if (typeof showToast === 'function') showToast(t('error.connection'), 'error');
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
    { name: 'compass', label: 'Orientación' },
    { name: 'sparkles', label: 'Nuevo' },
    { name: 'hard-hat', label: 'Obra' },
    { name: 'clock', label: 'Antiguedad' },
    { name: 'timer', label: 'Tiempo' },
    { name: 'calendar', label: 'Fecha' },
    { name: 'map-pin', label: 'Ubicación' },
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
        '<label for="fo-icon-search" class="sr-only">' + t('icon.search') + '</label>' +
        '<input id="fo-icon-search" type="text" placeholder="' + t('icon.search_placeholder') + '" oninput="filterIcons(this.value)" class="icon-search w-full px-2 py-1.5 text-xs border-0 border-b border-midnight/10 outline-none bg-paper-dark/50">' +
        '<div id="icon-picker-grid" class="grid grid-cols-6 gap-0.5 p-1.5 max-h-32 overflow-y-auto">';
    html += '<button type="button" data-icon="" data-search="ninguno" onclick="selectIconOption(this)" aria-label="' + t('icon.none') + '" class="icon-pick p-1 rounded border text-[10px] flex flex-col items-center gap-px transition-all ' +
        (!selectedIcon ? 'border-gold bg-gold/10 text-gold' : 'border-transparent text-midnight/60 hover:border-midnight/20') + '" title="' + t('icon.none') + '">' +
        '<i data-lucide="x" class="w-3 h-3"></i><span class="leading-none">' + t('icon.none_label') + '</span></button>';
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
            if (typeof showToast === 'function') showToast(t('error.options_load'), 'error');
        });
}

function buildCategoryFilters() {
    var cats = [];
    allFormOptions.forEach(function(o) {
        if (cats.indexOf(o.category) === -1) cats.push(o.category);
    });
    var container = document.getElementById('category-filters');
    var html = '<button role="tab" aria-pressed="' + (!currentCategoryFilter) + '" onclick="filterCategory(\'\')" class="cat-filter px-3 py-1 text-[10px] font-bold uppercase tracking-widest rounded ' +
        (!currentCategoryFilter ? 'bg-midnight text-white' : 'bg-paper-dark text-midnight hover:bg-gold hover:text-white') + '">' + t('form_options.all_categories') + '</button>';
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
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-midnight/60">' + t('form_options.empty') + '</td></tr>';
        if (liveRegion) liveRegion.textContent = t('form_options.zero_found');
        return;
    }
    tbody.innerHTML = filtered.map(function(o) {
        return '<tr class="hover:bg-paper-dark/30 ' + (o.is_active ? '' : 'opacity-40') + '">' +
            '<td class="px-4 py-3 text-[13px]"><span class="text-[10px] font-bold uppercase tracking-widest text-gold bg-gold/10 px-2 py-1 rounded">' + escapeHtml(o.category) + '</span></td>' +
            '<td class="px-4 py-3 font-mono text-[11px] text-midnight/60">' + escapeHtml(o.value) + '</td>' +
            '<td class="px-4 py-3 text-[13px] text-midnight/50">' + escapeHtml(o.label) + '</td>' +
            '<td class="px-4 py-3 text-[13px] text-midnight/50">' + (o.icon ? '<i data-lucide="' + escapeHtml(o.icon) + '" class="w-4 h-4 inline-block"></i> <span class="text-[11px]">' + escapeHtml(o.icon) + '</span>' : '<span class="text-[11px]">-</span>') + '</td>' +
            '<td class="px-4 py-3 text-[13px] text-midnight/50">' + o.sort_order + '</td>' +
            '<td class="px-4 py-3"><span class="px-2 py-1 text-[10px] font-bold rounded ' +
            (o.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700') + '">' +
            (o.is_active ? t('status.active') : t('status.inactive')) + '</span></td>' +
            '<td class="px-4 py-3 text-right"><div class="flex gap-1 justify-end">' +
            '<button onclick="editFormOption(' + o.id + ')" aria-label="' + t('action.edit') + ' ' + escapeHtml(o.label) + '" class="p-1.5 rounded hover:bg-paper-dark" title="' + t('action.edit') + '"><i data-lucide="pencil" class="w-3 h-3"></i></button>' +
            '<button onclick="toggleFormOption(' + o.id + ', ' + (o.is_active ? 0 : 1) + ')" aria-label="' + (o.is_active ? t('action.deactivate') : t('action.activate')) + ' ' + escapeHtml(o.label) + '" class="p-1.5 rounded hover:bg-paper-dark" title="' + (o.is_active ? t('action.deactivate') : t('action.activate')) + '"><i data-lucide="' + (o.is_active ? 'eye-off' : 'eye') + '" class="w-3 h-3"></i></button>' +
            '<button onclick="deleteFormOption(' + o.id + ')" aria-label="' + t('action.delete') + ' ' + escapeHtml(o.label) + '" class="p-1.5 rounded hover:bg-rose-50 text-rose-600" title="' + t('action.delete') + '"><i data-lucide="trash-2" class="w-3 h-3"></i></button>' +
            '</div></td></tr>';
    }).join('');
    if (liveRegion) liveRegion.textContent = t('form_options.results_count', {count: filtered.length});
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
        '<h3 id="fo-modal-title" class="text-2xl font-serif">' + t('form_options.new_option') + '</h3>' +
        '</div>' +
        '<div class="px-4 sm:px-6 pb-6 space-y-3 overflow-y-auto min-h-0">' +
        '<div><label for="fo-category" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.category') + '</label>' +
        '<select id="fo-category" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm">' + catOptions + '</select></div>' +
        '<div><label for="fo-value" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.value') + '</label>' +
        '<input id="fo-value" type="text" maxlength="100" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" placeholder="' + t('form_options.value_placeholder') + '"></div>' +
        '<div><label for="fo-label" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.label') + '</label>' +
        '<input id="fo-label" type="text" maxlength="200" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" placeholder="' + t('form_options.label_placeholder') + '"></div>' +
        '<div><label for="fo-icon-search" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.icon_optional') + '</label>' +
        '<input id="fo-icon" type="hidden" value="">' +
        renderIconPicker('') + '</div>' +
        '<div><label for="fo-order" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.sort_order') + '</label>' +
        '<input id="fo-order" type="number" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="0"></div>' +
        '<div class="flex gap-3 pt-2">' +
        '<button onclick="closeFormOptionModal()" class="flex-1 py-3 border border-midnight/20 rounded text-[10px] font-bold uppercase tracking-widest text-midnight hover:border-midnight transition-all">' + t('action.cancel') + '</button>' +
        '<button id="fo-save-btn" onclick="saveFormOption()" class="flex-1 py-3 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">' + t('action.save') + '</button>' +
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
        if (typeof showToast === 'function') showToast(t('form_options.required_fields'), 'error');
        return;
    }
    isFormOptionSaving = true;
    var saveBtn = document.getElementById('fo-save-btn');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = t('action.saving'); }
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
                if (typeof showToast === 'function') showToast(editId ? t('success.option_updated') : t('success.option_created'), 'success');
                closeFormOptionModal();
                loadFormOptions();
            }
        })
        .catch(function(err) {
            if (typeof showToast === 'function') showToast(err.message || t('error.connection'), 'error');
        })
        .finally(function() {
            isFormOptionSaving = false;
            var btn = document.getElementById('fo-save-btn');
            if (btn) { btn.disabled = false; btn.textContent = editId ? t('action.update') : t('action.save'); }
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
        '<h3 id="fo-modal-title" class="text-2xl font-serif">' + t('form_options.edit_option') + '</h3>' +
        '</div>' +
        '<div class="px-4 sm:px-6 pb-6 space-y-3 overflow-y-auto min-h-0">' +
        '<div><label for="fo-category" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.category') + '</label>' +
        '<select id="fo-category" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" disabled>' + catOptions + '</select></div>' +
        '<div><label for="fo-value" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.value') + '</label>' +
        '<input id="fo-value" type="text" maxlength="100" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="' + escapeHtml(opt.value) + '"></div>' +
        '<div><label for="fo-label" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.label') + '</label>' +
        '<input id="fo-label" type="text" maxlength="200" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="' + escapeHtml(opt.label) + '"></div>' +
        '<div><label for="fo-icon-search" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.icon') + '</label>' +
        '<input id="fo-icon" type="hidden" value="' + escapeHtml(opt.icon || '') + '">' +
        renderIconPicker(opt.icon || '') + '</div>' +
        '<div><label for="fo-order" class="text-[10px] uppercase tracking-widest font-bold text-midnight/60">' + t('form_options.sort_order') + '</label>' +
        '<input id="fo-order" type="number" class="w-full mt-1 px-4 py-2 border border-midnight/10 rounded text-sm" value="' + opt.sort_order + '"></div>' +
        '<div class="flex gap-3 pt-2">' +
        '<button onclick="closeFormOptionModal()" class="flex-1 py-3 border border-midnight/20 rounded text-[10px] font-bold uppercase tracking-widest text-midnight hover:border-midnight transition-all">' + t('action.cancel') + '</button>' +
        '<button id="fo-save-btn" onclick="saveFormOption(' + id + ')" class="flex-1 py-3 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">' + t('action.update') + '</button>' +
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
                if (typeof showToast === 'function') showToast(newActive ? t('success.option_activated') : t('success.option_deactivated'), 'success');
                loadFormOptions();
            }
        })
        .catch(function(err) {
            if (typeof showToast === 'function') showToast(err.message || t('error.connection'), 'error');
        });
}

function deleteFormOption(id) {
    var promise = typeof showConfirm === 'function' ? showConfirm(t('confirm.delete_option')) : Promise.resolve(true);
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
                    if (typeof showToast === 'function') showToast(t('success.option_deleted'), 'success');
                    loadFormOptions();
                }
            })
            .catch(function(err) {
            if (typeof showToast === 'function') showToast(err.message || t('error.connection'), 'error');
            });
    });
}

// ================================================================
// PHONE AUDIT — Historial de Acceso a Teléfonos
// ================================================================
var currentPaPage = 1;
var currentPaFilters = {};
var paProfesionalList = [];

function initPhoneAudit() {
    fetch('/api/professionals?sort=name&order=asc')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success && data.professionals) {
                paProfesionalList = data.professionals.map(function(p) { return p.name; });
                var select = document.getElementById('pa-profesional');
                if (select) {
                    paProfesionalList.forEach(function(name) {
                        var opt = document.createElement('option');
                        opt.value = name;
                        opt.textContent = name;
                        select.appendChild(opt);
                    });
                }
            }
        })
        .catch(function() {});
    loadPhoneAudit();
}

function loadPhoneAudit() {
    currentPaPage = 1;
    var profesional = document.getElementById('pa-profesional');
    var evento = document.getElementById('pa-evento');
    var desde = document.getElementById('pa-desde');
    var hasta = document.getElementById('pa-hasta');
    currentPaFilters = {
        profesional: profesional ? profesional.value : '',
        evento: evento ? evento.value : '',
        desde: desde ? desde.value : '',
        hasta: hasta ? hasta.value : '',
    };
    _fetchPhoneAudit();
}

function loadPhoneAuditPage(page) {
    if (page < 1) return;
    currentPaPage = page;
    _fetchPhoneAudit();
}

function clearPhoneAuditFilters() {
    var profesional = document.getElementById('pa-profesional');
    var evento = document.getElementById('pa-evento');
    var desde = document.getElementById('pa-desde');
    var hasta = document.getElementById('pa-hasta');
    if (profesional) profesional.value = '';
    if (evento) evento.value = '';
    if (desde) desde.value = '';
    if (hasta) hasta.value = '';
    currentPaFilters = {};
    currentPaPage = 1;
    _fetchPhoneAudit();
}

function _fetchPhoneAudit() {
    var loadingEl = document.getElementById('pa-loading');
    var emptyEl = document.getElementById('pa-empty');
    var tbody = document.getElementById('pa-tbody');
    var paginationEl = document.getElementById('pa-pagination');
    var countEl = document.getElementById('pa-count');
    if (!tbody) return;
    loadingEl.classList.remove('hidden');
    emptyEl.classList.add('hidden');
    if (paginationEl) paginationEl.classList.add('hidden');
    var params = new URLSearchParams();
    params.set('page', currentPaPage);
    params.set('per_page', '25');
    if (currentPaFilters.profesional) params.set('profesional', currentPaFilters.profesional);
    if (currentPaFilters.evento) params.set('evento', currentPaFilters.evento);
    if (currentPaFilters.desde) params.set('desde', currentPaFilters.desde);
    if (currentPaFilters.hasta) params.set('hasta', currentPaFilters.hasta);
    fetch('/api/admin/phone-audit?' + params.toString())
        .then(function(r) { return r.json(); })
        .then(function(data) {
            loadingEl.classList.add('hidden');
            if (data.success) {
                renderPhoneAudit(data);
                if (countEl) countEl.textContent = data.total || 0;
            } else {
                emptyEl.classList.remove('hidden');
            }
        })
        .catch(function() {
            loadingEl.classList.add('hidden');
            emptyEl.classList.remove('hidden');
        });
}

function renderPhoneAudit(data) {
    var tbody = document.getElementById('pa-tbody');
    var emptyEl = document.getElementById('pa-empty');
    var paginationEl = document.getElementById('pa-pagination');
    if (!tbody) return;
    var rows = data.data || [];
    if (!rows.length) {
        emptyEl.classList.remove('hidden');
        if (paginationEl) paginationEl.classList.add('hidden');
        tbody.querySelectorAll('tr:not(#pa-loading):not(#pa-empty)').forEach(function(r) { r.remove(); });
        return;
    }
    emptyEl.classList.add('hidden');
    tbody.querySelectorAll('tr:not(#pa-loading):not(#pa-empty)').forEach(function(r) { r.remove(); });
    rows.forEach(function(entry, idx) {
        var tr = document.createElement('tr');
        tr.className = 'border-b border-midnight/[0.03] hover:bg-paper transition-colors';
        tr.style.animationDelay = (idx * 0.05) + 's';
        tr.innerHTML = renderPhoneAuditRow(entry);
        tbody.appendChild(tr);
    });
    initTableStagger(tbody);
    updatePaPagination(data.total, data.page, data.per_page);
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderPhoneAuditRow(entry) {
    var eventoLabel, eventoClass, eventoIcon;
    if (entry.event === 'phone_revealed') {
        eventoLabel = t('audit.revealed');
        eventoClass = 'bg-emerald-50 text-emerald-700';
        eventoIcon = '<i data-lucide="eye" class="w-2.5 h-2.5"></i>';
    } else if (entry.event === 'wa_link_generated') {
        eventoLabel = t('audit.whatsapp');
        eventoClass = 'bg-gold/10 text-gold';
        eventoIcon = '<i data-lucide="message-circle" class="w-2.5 h-2.5"></i>';
    } else {
        eventoLabel = entry.event;
        eventoClass = 'bg-paper-dark text-midnight/50';
        eventoIcon = '<i data-lucide="activity" class="w-2.5 h-2.5"></i>';
    }
    var leadCell = entry.lead_id
        ? '<div class="font-medium text-midnight">#' + entry.lead_id + ' ' + escapeHtml(entry.lead_tipo || '') + '</div>' +
          '<div class="text-[11px] text-midnight/60">' + escapeHtml(entry.lead_zona || '') + '</div>'
        : '<span class="text-midnight/30 italic">' + t('audit.lead_deleted') + '</span>';
    var phoneCell = entry.lead_telefono
        ? '<span class="font-mono text-[11px] text-midnight/70">' + escapeHtml(entry.lead_telefono) + '</span>'
        : '<span class="text-midnight/30 italic">—</span>';
    var fecha = entry.ts || '';
    return '<td class="px-4 py-3 text-[13px] font-medium text-midnight">' + escapeHtml(entry.profesional || '') + '</td>' +
           '<td class="px-4 py-3 text-[13px]">' + leadCell + '</td>' +
           '<td class="px-4 py-3">' + phoneCell + '</td>' +
           '<td class="px-4 py-3"><span class="inline-flex items-center gap-1 px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest ' + eventoClass + '">' + eventoIcon + ' ' + eventoLabel + '</span></td>' +
           '<td class="px-4 py-3 text-[11px] text-midnight/50 font-mono">' + fecha + '</td>';
}

function updatePaPagination(total, page, perPage) {
    var paginationEl = document.getElementById('pa-pagination');
    var infoEl = document.getElementById('pa-info');
    var prevBtn = document.getElementById('pa-prev');
    var nextBtn = document.getElementById('pa-next');
    var indicator = document.getElementById('pa-page-indicator');
    if (!paginationEl || !total) { paginationEl.classList.add('hidden'); return; }
    var totalPages = Math.ceil(total / perPage);
    paginationEl.classList.remove('hidden');
    if (infoEl) infoEl.textContent = t('pagination.audit_page', {page: page, totalPages: totalPages, total: total});
    if (prevBtn) {
        prevBtn.disabled = page <= 1;
        prevBtn.classList.toggle('disabled\\:opacity-30', page <= 1);
    }
    if (nextBtn) {
        nextBtn.disabled = page >= totalPages;
        nextBtn.classList.toggle('disabled\\:opacity-30', page >= totalPages);
    }
    if (indicator) indicator.textContent = page + ' / ' + totalPages;
}

document.addEventListener('DOMContentLoaded', function() {
    // Phone audit init after dashboard renders
    var paCard = document.getElementById('phone-audit-card');
    if (paCard) {
        // init after telemetry loads
        setTimeout(initPhoneAudit, 100);
    }
});

// ================================================================
// NOTIFICATIONS TAB
// ================================================================
var currentNotifLogPage = 1;

function loadAdminNotifPrefs() {
    fetch('/api/profile/settings')
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!data.success) return;
        setToggle('admin-notif-email', data.email_notifications);
        setToggle('admin-notif-sms', data.sms_notifications);
        setToggle('admin-notif-leads', data.lead_alerts);
    })
    .catch(function() {});
}

function saveAdminNotifPrefs() {
    var data = {
        email_notifications: document.getElementById('admin-notif-email')?.checked ? 1 : 0,
        sms_notifications: document.getElementById('admin-notif-sms')?.checked ? 1 : 0,
        lead_alerts: document.getElementById('admin-notif-leads')?.checked ? 1 : 0,
    };
    fetch('/api/profile/settings', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })
    .then(function(r) { return r.json(); })
    .then(function(result) {
        if (result.success) {
            var msg = document.getElementById('admin-notif-save-msg');
            if (msg) { msg.classList.remove('hidden'); setTimeout(function() { msg.classList.add('hidden'); }, 3000); }
        }
    })
    .catch(function() {});
}

function loadNotificationLog(page) {
    currentNotifLogPage = page;
    var search = document.getElementById('notif-log-search')?.value || '';
    var tbody = document.getElementById('notif-log-body');
    var pagination = document.getElementById('notif-log-pagination');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-xs text-midnight/40 dark:text-white/40">' + window.t('nav.loading') + '</td></tr>';
    fetch('/api/admin/notification-log?page=' + page + '&q=' + encodeURIComponent(search))
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!data.success || !data.items || data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-xs text-midnight/40 dark:text-white/40">' + window.t('admin.notif_no_results') + '</td></tr>';
            if (pagination) pagination.classList.add('hidden');
            return;
        }
        var html = '';
        data.items.forEach(function(n) {
            html += '<tr class="border-b border-midnight/10 dark:border-white/10">' +
                '<td class="text-[13px] text-midnight/50 dark:text-white/50 px-4 py-3">' + n.id + '</td>' +
                '<td class="text-[13px] text-midnight dark:text-white px-4 py-3">' + escapeHtml(n.recipient_username || 'User #' + n.user_id) + '</td>' +
                '<td class="text-[13px] text-midnight dark:text-white px-4 py-3">' + escapeHtml(n.title || '-') + '</td>' +
                '<td class="text-[13px] text-midnight/50 dark:text-white/50 px-4 py-3">' + n.created_at + '</td>' +
                '</tr>';
        });
        tbody.innerHTML = html;
        if (pagination) {
            if (data.pages > 1) {
                pagination.classList.remove('hidden');
                document.getElementById('notif-log-prev').disabled = page <= 1;
                document.getElementById('notif-log-prev').className = 'text-[10px] uppercase tracking-wider font-bold transition-colors ' + (page <= 1 ? 'text-midnight/20 cursor-not-allowed' : 'text-midnight/40 hover:text-gold');
                document.getElementById('notif-log-page-info').textContent = window.t('notif.page_of', {page: page, pages: data.pages});
                document.getElementById('notif-log-next').disabled = page >= data.pages;
                document.getElementById('notif-log-next').className = 'text-[10px] uppercase tracking-wider font-bold transition-colors ' + (page >= data.pages ? 'text-midnight/20 cursor-not-allowed' : 'text-midnight/40 hover:text-gold');
            } else {
                pagination.classList.add('hidden');
            }
        }
    })
    .catch(function() {
        tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-xs text-rose-400">' + window.t('nav.error_loading') + '</td></tr>';
    });
}

function setToggle(id, val) {
    var el = document.getElementById(id);
    if (el) el.checked = val == 1 || val === true;
}

// ================================================================
// PHONE AREA CODES CRUD
// ================================================================
var allPhoneAreaCodes = [];
var pacCurrentCountryFilter = '';
var pacCurrentSearchFilter = '';

function loadPhoneAreaCodes() {
    fetch('/api/phone-area-codes/all')
    .then(function(r) { return r.json(); })
    .then(function(data) {
        allPhoneAreaCodes = data.codes || [];
        renderPacCountryFilters();
        renderPhoneAreaCodes();
    });
}

function renderPacCountryFilters() {
    var container = document.getElementById('pac-country-filters');
    if (!container) return;
    var countries = {};
    allPhoneAreaCodes.forEach(function(c) {
        countries[c.country_code] = (countries[c.country_code] || 0) + 1;
    });
    var html = '<button onclick="filterPacByCountry(\'\')" class="report-filter-chip ' + (!pacCurrentCountryFilter ? 'report-filter-active' : '') + '" data-filter="all">' + window.t('admin.filter_all') + '</button>';
    Object.keys(countries).sort().forEach(function(cc) {
        var active = pacCurrentCountryFilter === cc ? ' report-filter-active' : '';
        html += '<button onclick="filterPacByCountry(\'' + cc + '\')" class="report-filter-chip' + active + '" data-filter="' + cc + '">' + cc + ' (' + countries[cc] + ')</button>';
    });
    container.innerHTML = html;
}

function filterPacByCountry(cc) {
    pacCurrentCountryFilter = cc;
    renderPacCountryFilters();
    renderPhoneAreaCodes();
}

function filterPhoneAreaCodes(query) {
    pacCurrentSearchFilter = query.toLowerCase().trim();
    renderPhoneAreaCodes();
}

function renderPhoneAreaCodes() {
    var tbody = document.getElementById('phone-area-codes-tbody');
    if (!tbody) return;
    var filtered = allPhoneAreaCodes;
    if (pacCurrentCountryFilter) {
        filtered = filtered.filter(function(c) { return c.country_code === pacCurrentCountryFilter; });
    }
    if (pacCurrentSearchFilter) {
        filtered = filtered.filter(function(c) {
            return c.code.toLowerCase().indexOf(pacCurrentSearchFilter) !== -1 ||
                   c.city.toLowerCase().indexOf(pacCurrentSearchFilter) !== -1 ||
                   c.province.toLowerCase().indexOf(pacCurrentSearchFilter) !== -1 ||
                   c.country.toLowerCase().indexOf(pacCurrentSearchFilter) !== -1;
        });
    }
    var countEl = document.getElementById('pac-results-count');
    if (countEl) {
        countEl.textContent = filtered.length + ' / ' + allPhoneAreaCodes.length + ' ' + window.t('pac.codes');
    }
    if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-midnight/60">' + window.t('pac.no_results') + '</td></tr>';
        return;
    }
    var html = '';
    filtered.forEach(function(c) {
        var activeLabel = c.is_active ? '<span class="text-emerald-600 font-bold">' + window.t('admin.active') + '</span>' : '<span class="text-rose-500 font-bold">' + window.t('admin.inactive') + '</span>';
        html += '<tr class="hover:bg-paper-dark/50 transition-colors">' +
            '<td class="text-[13px] text-midnight/50 px-4 py-3 font-mono font-bold">' + escapeHtml(c.code) + '</td>' +
            '<td class="text-[13px] text-midnight/50 px-4 py-3">' + escapeHtml(c.city) + '</td>' +
            '<td class="text-[13px] text-midnight/50 px-4 py-3">' + escapeHtml(c.province || '-') + '</td>' +
            '<td class="text-[13px] text-midnight/50 px-4 py-3">' + escapeHtml(c.country) + ' <span class="text-[10px] text-midnight/30">' + escapeHtml(c.country_code) + '</span></td>' +
            '<td class="text-[13px] text-midnight/50 px-4 py-3">' + c.sort_order + '</td>' +
            '<td class="text-[13px] px-4 py-3">' + activeLabel + '</td>' +
            '<td class="text-right px-4 py-3">' +
                '<button onclick="openEditAreaCodeModal(' + c.id + ')" class="text-midnight/30 hover:text-gold transition-colors mr-2" title="' + window.t('admin.edit') + '"><i data-lucide="pencil" class="w-3 h-3 inline"></i></button>' +
                '<button onclick="deletePhoneAreaCode(' + c.id + ')" class="text-midnight/30 hover:text-rose-500 transition-colors" title="' + window.t('admin.delete') + '"><i data-lucide="trash-2" class="w-3 h-3 inline"></i></button>' +
            '</td></tr>';
    });
    tbody.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function openCreateAreaCodeModal() {
    var modal = document.getElementById('areaCodeModal');
    if (!modal) return;
    document.getElementById('pac-modal-title').textContent = window.t('pac.new_area_code');
    document.getElementById('pac-area-id').value = '';
    document.getElementById('pac-code').value = '';
    document.getElementById('pac-city').value = '';
    document.getElementById('pac-province').value = '';
    document.getElementById('pac-country').value = 'Argentina';
    document.getElementById('pac-country-code').value = '+54';
    document.getElementById('pac-sort-order').value = '0';
    document.getElementById('pac-is-active').checked = true;
    openModalAnim(modal);
}

function openEditAreaCodeModal(id) {
    var c = allPhoneAreaCodes.find(function(x) { return x.id === id; });
    if (!c) return;
    var modal = document.getElementById('areaCodeModal');
    if (!modal) return;
    document.getElementById('pac-modal-title').textContent = window.t('pac.edit_area_code');
    document.getElementById('pac-area-id').value = c.id;
    document.getElementById('pac-code').value = c.code;
    document.getElementById('pac-city').value = c.city;
    document.getElementById('pac-province').value = c.province;
    document.getElementById('pac-country').value = c.country;
    document.getElementById('pac-country-code').value = c.country_code;
    document.getElementById('pac-sort-order').value = c.sort_order;
    document.getElementById('pac-is-active').checked = c.is_active === 1;
    openModalAnim(modal);
}

function closeAreaCodeModal() {
    var modal = document.getElementById('areaCodeModal');
    if (modal) closeModalAnim(modal);
}

function saveAreaCode() {
    var id = document.getElementById('pac-area-id').value;
    var data = {
        code: document.getElementById('pac-code').value.trim(),
        city: document.getElementById('pac-city').value.trim(),
        province: document.getElementById('pac-province').value.trim(),
        country: document.getElementById('pac-country').value.trim(),
        country_code: document.getElementById('pac-country-code').value.trim(),
        sort_order: parseInt(document.getElementById('pac-sort-order').value) || 0,
        is_active: document.getElementById('pac-is-active').checked ? 1 : 0
    };
    if (!data.code || !data.city) {
        if (typeof showToast !== 'undefined') showToast(window.t('pac.missing_fields'), 'error');
        return;
    }
    var url = id ? '/api/phone-area-codes/' + id : '/api/phone-area-codes';
    var method = id ? 'PUT' : 'POST';
    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken ? csrfToken.content : '' },
        body: JSON.stringify(data)
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
        if (res.error) {
            if (typeof showToast !== 'undefined') showToast(res.error, 'error');
            return;
        }
        closeAreaCodeModal();
        loadPhoneAreaCodes();
        if (typeof showToast !== 'undefined') showToast(window.t('pac.saved'), 'success');
    })
    .catch(function() {
        if (typeof showToast !== 'undefined') showToast(window.t('pac.save_error'), 'error');
    });
}

function deletePhoneAreaCode(id) {
    if (!confirm(window.t('pac.confirm_delete'))) return;
    var csrfToken = document.querySelector('meta[name="csrf-token"]');
    fetch('/api/phone-area-codes/' + id, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrfToken ? csrfToken.content : '' }
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
        if (res.error) {
            if (typeof showToast !== 'undefined') showToast(res.error, 'error');
            return;
        }
        loadPhoneAreaCodes();
        if (typeof showToast !== 'undefined') showToast(window.t('pac.deleted'), 'success');
    })
    .catch(function() {
        if (typeof showToast !== 'undefined') showToast(window.t('pac.delete_error'), 'error');
    });
}

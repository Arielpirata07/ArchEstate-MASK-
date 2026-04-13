/**
 * LÓGICA SPA - ARCHESTATE (Versión Monopágina)
 */

// Inicializar iconos al cargar
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
});

function showView(viewId) {
    document.querySelectorAll('.view-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById('view-' + viewId).classList.add('active');
    
    const navLogout = document.getElementById('nav-logout');
    if (viewId === 'landing') {
        navLogout.classList.add('hidden');
    } else {
        navLogout.classList.remove('hidden');
    }

    if (viewId === 'professional') loadLeads();
    if (viewId === 'admin') loadProfessionals();
}

function validateEmail(val) {
    const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    const errorEl = document.getElementById('email-error');
    const inputEl = document.getElementById('email-input');
    const iconEl = document.getElementById('mail-icon');

    if (!isValid && val.length > 0) {
        errorEl.classList.remove('hidden');
        inputEl.classList.add('border-rose-300', 'text-rose-900');
        iconEl.classList.add('text-rose-500');
    } else {
        errorEl.classList.add('hidden');
        inputEl.classList.remove('border-rose-300', 'text-rose-900');
        iconEl.classList.remove('text-rose-500');
    }
    return isValid;
}

function handleUserSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('email-input').value;
    if (!validateEmail(email)) return;
    
    alert("¡Solicitud enviada! Los profesionales se contactarán contigo.");
    showView('landing');
}

function loadLeads() {
    const leads = [
        {id: "AE-9421", type: "Construcción Villa", zone: "Marbella, Málaga", budget: "€1.2M - €1.5M", phone: "+34 612 345 678"},
        {id: "AE-8832", type: "Compra Penthouse", zone: "Barcelona, Eixample", budget: "€850k - €1M", phone: "+34 699 887 766"},
        {id: "AE-7540", type: "Remodelación Mansión", zone: "Madrid, La Moraleja", budget: "€500k+", phone: "+34 655 443 322"}
    ];
    const tbody = document.getElementById('leads-table-body');
    if (!tbody) return;

    tbody.innerHTML = leads.map(lead => `
        <tr class="border-b border-midnight/5 hover:bg-paper transition-colors group">
            <td class="p-4 font-mono text-xs text-midnight/60">${lead.id}</td>
            <td class="p-4 font-medium">${lead.type}</td>
            <td class="p-4 text-sm text-midnight/70">${lead.zone}</td>
            <td class="p-4 font-serif italic text-gold">${lead.budget}</td>
            <td class="p-4 text-right">
                <button onclick="revealPhone(this, '${lead.phone}')" class="inline-flex items-center gap-2 px-4 py-2 bg-midnight text-white rounded text-[10px] font-bold uppercase tracking-widest hover:bg-gold transition-all">
                    <i data-lucide="eye" class="w-3 h-3"></i> Ver Teléfono
                </button>
            </td>
        </tr>
    `).join('');
    lucide.createIcons();
}

function revealPhone(btn, phone) {
    btn.innerHTML = `<i data-lucide="phone" class="w-3 h-3"></i> ${phone}`;
    lucide.createIcons();
}

function loadProfessionals() {
    const pros = [
        {name: "Arq. Carlos Méndez", license: "COAM-12948"},
        {name: "Inmobiliaria Prime S.L.", license: "API-4402"}
    ];
    const tbody = document.getElementById('professionals-table-body');
    if (!tbody) return;

    tbody.innerHTML = pros.map(pro => `
        <tr class="border-b border-midnight/5 hover:bg-paper transition-colors">
            <td class="p-4 font-medium">${pro.name}</td>
            <td class="p-4 font-mono text-xs text-midnight/60">${pro.license}</td>
        </tr>
    `).join('');
    lucide.createIcons();
}

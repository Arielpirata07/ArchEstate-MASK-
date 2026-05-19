/**
 * LÓGICA FRONTEND - ARCHESTATE
 */

// Inicializar iconos al cargar
document.addEventListener('DOMContentLoaded', () => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    // Inicializar moneda por defecto
    selectedCurrency = '€';
    updateCurrencyButtons();
});

// Variable global para la moneda seleccionada
let selectedCurrency = '€';

// Función para cambiar la moneda
function setCurrency(currency) {
    selectedCurrency = currency;
    updateCurrencyButtons();
}

// Función para actualizar los botones de moneda
function updateCurrencyButtons() {
    document.getElementById('btn-eur').classList.toggle('selected', selectedCurrency === '€');
    document.getElementById('btn-usd').classList.toggle('selected', selectedCurrency === 'USD');
    document.getElementById('btn-ars').classList.toggle('selected', selectedCurrency === 'ARS');
}


// Validación de Email en tiempo real (Se usa en user.html y register.html)
function validateEmail(val) {
    const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    const errorEl = document.getElementById('email-error');
    const inputEl = document.getElementById('email-input');
    const iconEl = document.getElementById('mail-icon');

    if (!isValid && val.length > 0) {
        if(errorEl) errorEl.classList.remove('hidden');
        if(inputEl) inputEl.classList.add('border-rose-300', 'text-rose-900');
        if(iconEl) iconEl.classList.add('text-rose-500');
    } else {
        if(errorEl) errorEl.classList.add('hidden');
        if(inputEl) inputEl.classList.remove('border-rose-300', 'text-rose-900');
        if(iconEl) iconEl.classList.remove('text-rose-500');
    }
    
    return isValid; // ¡Clave para que no se bloquee el formulario!
}

function validatePhoneInput(val) {
    const digits = val.replace(/\D/g, '');
    const isValid = digits.length >= 8 && digits.length <= 15;
    const errorEl = document.getElementById('phone-error');
    const inputEl = document.getElementById('phone-input');
    const iconEl = document.getElementById('phone-icon');

    if (!isValid && val.length > 0) {
        if (errorEl) errorEl.classList.remove('hidden');
        if (inputEl) inputEl.classList.add('border-rose-300', 'text-rose-900');
        if (iconEl) iconEl.classList.add('text-rose-500');
    } else {
        if (errorEl) errorEl.classList.add('hidden');
        if (inputEl) inputEl.classList.remove('border-rose-300', 'text-rose-900');
        if (iconEl) iconEl.classList.remove('text-rose-500');
    }

    return isValid;
}

function handleUserSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('email-input').value;
    if (!validateEmail(email)) return;

    const phone = document.getElementById('phone-input').value;
    if (!validatePhoneInput(phone)) return;
    
    // Recoger datos del formulario
    const formData = {
        type: document.getElementById('type-select').value,
        budget: selectedCurrency + ' ' + document.getElementById('budget-input').value,
        zone: document.getElementById('zone-input').value,
        phone: document.getElementById('phone-input').value,
        email: email
    };
    
    // Enviar a la API
    fetch('/api/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert("¡Solicitud enviada! Los profesionales se contactarán contigo.");
            showView('landing');
        } else {
            alert("Error: " + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Error al enviar la solicitud. Inténtalo de nuevo.");
    });
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

// Función para revelar el teléfono en el panel del profesional
function revealPhone(btn, phone) {
    // Agregamos un efecto de carga para que se sienta premium
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> Desencriptando...`;
    lucide.createIcons();

    setTimeout(() => {
        btn.innerHTML = `<i data-lucide="phone" class="w-3 h-3"></i> ${phone}`;
        btn.classList.remove('bg-midnight', 'hover:bg-gold');
        btn.classList.add('bg-emerald-700', 'text-white');
        lucide.createIcons();
    }, 600); // Pequeña demora para simular seguridad
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

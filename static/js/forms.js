/* forms.js — extraído de main.js (FASE 5.2). Carga después de main.js. */
(function () {

function validateEmail(val) {
    const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
    const errorEl = document.getElementById('email-error');
    const inputEl = document.getElementById('email-input');
    const iconEl = document.getElementById('mail-icon');

    if (!errorEl || !inputEl || !iconEl) return isValid;

    if (!isValid && val.length > 0) {
        errorEl.classList.remove('hidden');
        inputEl.classList.add('border-rose-300');
        iconEl.classList.add('text-rose-500');
    } else {
        errorEl.classList.add('hidden');
        inputEl.classList.remove('border-rose-300');
        iconEl.classList.remove('text-rose-500');
    }
    return isValid;
}

/**
 * Validacion de Telefono con deteccion de pais
 */


const PHONE_RULES = {
    '+54':  { min: 10, max: 15, label: 'Argentina' },
    '+598': { min: 10, max: 13, label: 'Uruguay' },
    '+56':  { min: 9,  max: 12, label: 'Chile' },
    '+55':  { min: 10, max: 13, label: 'Brasil' },
    '+595': { min: 9,  max: 12, label: 'Paraguay' },
    '+591': { min: 8,  max: 11, label: 'Bolivia' },
    '+57':  { min: 10, max: 12, label: 'Colombia' },
    '+52':  { min: 10, max: 12, label: 'México' },
    '+34':  { min: 9,  max: 11, label: 'España' },
    '+1':   { min: 10, max: 11, label: 'EE.UU./Canadá' },
};


function validatePhone(val) {
    if (!val) return false;
    const phoneDigits = val.replace(/\D/g, '');
    const countrySelect = document.getElementById('country-code-select');
    const cc = countrySelect ? countrySelect.value : '+54';
    const rules = PHONE_RULES[cc] || { min: 8, max: 15, label: '' };

    const isValid = phoneDigits.length >= rules.min && phoneDigits.length <= rules.max;
    const errorEl = document.getElementById('phone-error');
    const inputEl = document.getElementById('phone-input');
    if (!errorEl || !inputEl) return isValid;

    if (!isValid && val.length > 0) {
        errorEl.textContent = rules.label
            ? t('validator.phone_format_country', {label: rules.label, min: rules.min})
            : t('validator.phone_length');
        errorEl.classList.remove('hidden');
        inputEl.classList.add('border-rose-300');
    } else {
        errorEl.classList.add('hidden');
        inputEl.classList.remove('border-rose-300');
    }
    return isValid;
}

/**
 * Validacion de Presupuesto
 */


function validateZone(val) {
    if (!val) return false;
    const isValid = val.trim().length >= 2 && val.trim().length <= 100;
    const errorEl = document.getElementById('zone-error');
    const inputEl = document.getElementById('zone-input');
    if (!errorEl || !inputEl) return isValid;
    if (!isValid && val.length > 0) {
        errorEl.classList.remove('hidden');
        inputEl.classList.add('border-rose-300');
    } else {
        errorEl.classList.add('hidden');
        inputEl.classList.remove('border-rose-300');
    }
    return isValid;
}

/**
 * Combina código de país + prefijo de área + teléfono en formato E.164
 * legible (`+54 9 <área> <abonado>` para AR). Orden: área → móvil → área,
 * para no duplicar el área ni perder el prefijo (Fase 0 ítem 1).
 * Función pura para poder testearla en Node sin DOM.
 */


function combineCountryAreaPhone(countryCode, provincePrefix, phone) {
    const codeDigits = String(countryCode || '').replace('+', '');
    const digits = String(phone || '').replace(/\D/g, '');
    let localDigits = digits;
    if (localDigits.startsWith(codeDigits)) {
        localDigits = localDigits.substring(codeDigits.length);
    }
    if (provincePrefix && localDigits) {
        let local = localDigits;
        const stripArea = () => {
            for (const c of [provincePrefix, `0${provincePrefix}`]) {
                if (local.startsWith(c)) { local = local.substring(c.length); break; }
            }
        };
        stripArea();
        if (local.startsWith('9')) local = local.substring(1);
        else if (local.startsWith('15')) local = local.substring(2);
        stripArea();
        return `${countryCode} 9 ${provincePrefix} ${local}`;
    }
    if (countryCode === '+54') {
        let d = localDigits;
        d = d.replace(/^0(?=\d)/, '');
        if (d.startsWith('9')) d = d.substring(1);
        else if (d.startsWith('15')) d = d.substring(2);
        if (!d.startsWith('9')) d = '9' + d;
        return `${countryCode} ${d}`;
    }
    return `${countryCode} ${phone}`;
}

/**
 * Inicializacion del formulario de usuario
 * Nota: user.html tiene su propio setPropertyType() que maneja 5 tipos.
 * Esta funcion solo inicializa validaciones y autocomplete.
 */


function initUserForm() {
    const form = document.getElementById('userForm');
    const emailInput = document.getElementById('email-input');

    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateEmail(this.value);
        });
    }

    initZoneAutocomplete();
    initArchitecturalStyleAutocomplete();
    initCountrySelector();
    initBudgetPopup();

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            // Guard anti-doble-submit: misma sesión, doble click o Enter
            // repetido. El backend además deduplica por idempotency key.
            if (form.dataset.submitting === '1') return;
            form.dataset.submitting = '1';
            // Una key por intento de formulario: los reintentos tras error
            // reutilizan la misma key para que el backend no duplique el lead.
            if (!form.dataset.idemKey && window.crypto && crypto.randomUUID) {
                form.dataset.idemKey = crypto.randomUUID();
            }
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            if (form.dataset.idemKey) data.idempotency_key = form.dataset.idemKey;

            // Recolectar amenities seleccionadas
            const amenitiesCheckboxes = document.querySelectorAll('input[name="amenities"]:checked');
            data.amenities = Array.from(amenitiesCheckboxes).map(cb => cb.value).join(', ');

            // Combinar código de país + prefijo de provincia + teléfono
            const countryCodeSelect = document.getElementById('country-code-select');
            const provinceSelect = document.getElementById('phone-province');
            const phoneInput = document.getElementById('phone-input');
            if (countryCodeSelect && phoneInput && phoneInput.value) {
                const countryCode = countryCodeSelect.value;
                const phone = phoneInput.value.trim();
                const provincePrefix = (countryCode === '+54' && provinceSelect && !provinceSelect.classList.contains('hidden')) ? provinceSelect.value : '';
                data.phone = combineCountryAreaPhone(countryCode, provincePrefix, phone);
            }

            // Validacion de area para casas
            const landArea = parseFloat(data.land_area || '0');
            const builtArea = parseFloat(data.built_area || '0');
            if (data.property_type === 'casa' && landArea > 0 && builtArea > 0) {
                if (builtArea > landArea * 0.8) {
                    showToast(t('validator.built_area_exceeds'), 'error');
                    form.dataset.submitting = '0';
                    return;
                }
            }

            // Validacion rapida en cliente
            var submitBtn = form.querySelector('button[type="submit"]');

            if (!validateEmail(data.email)) {
                setLoading(submitBtn, false);
                if (window.lucide) lucide.createIcons();
                showToast(t('validator.email_empty_or_invalid'), 'error');
                form.dataset.submitting = '0';
                return;
            }

            // Validacion cruzada de moneda vs presupuesto
            var budgetValidation = validateBudgetForCurrency(data.budget, data.currency);
            if (!budgetValidation.isValid) {
                setLoading(submitBtn, false);
                if (window.lucide) lucide.createIcons();
                showToast(budgetValidation.message, 'error');
                form.dataset.submitting = '0';
                return;
            }

            // Estado de carga
            setLoading(submitBtn, true, t('action.processing'));

            try {
                const headers = { 'Content-Type': 'application/json' };
                if (form.dataset.idemKey) headers['X-Idempotency-Key'] = form.dataset.idemKey;
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    sessionStorage.setItem('submit_success', 'true');
                    setTimeout(() => {
                        window.location.href = "/";
                    }, 1500);
                } else {
                    form.dataset.submitting = '0';
                    setLoading(submitBtn, false);
                    if (window.lucide) lucide.createIcons();
                    showToast(result.message, 'error');
                }
            } catch (error) {
                form.dataset.submitting = '0';
                setLoading(submitBtn, false);
                if (window.lucide) lucide.createIcons();
                console.error("Error al enviar el formulario:", error);
                showToast(t('error.server_connection'), 'error');
            }
        });
    }
}


function selectPropertyType(propertyType) {
    const propertyTypeInput = document.getElementById('property-type-input');
    const operationSelect = document.getElementById('operation-select');
    const departmentDetails = document.getElementById('department-details');
    const houseDetails = document.getElementById('house-details');
    const departmentBtn = document.getElementById('btn-department');
    const houseBtn = document.getElementById('btn-house');

    if (!propertyTypeInput || !operationSelect || !departmentDetails || !houseDetails) return;

    propertyTypeInput.value = propertyType;

    const departmentOptions = [
        { value: 'Comprar Propiedad', text: t('operation.buy') },
        { value: 'Remodelación Integral', text: t('operation.remodel') }
    ];
    const houseOptions = [
        { value: 'Comprar Propiedad', text: t('operation.buy') },
        { value: 'Construir desde Cero', text: t('operation.build') },
        { value: 'Remodelación Integral', text: t('operation.remodel') }
    ];

    const options = propertyType === 'casa' ? houseOptions : departmentOptions;
    operationSelect.innerHTML = options.map(opt => `<option value="${opt.value}">${opt.text}</option>`).join('');

    departmentDetails.classList.toggle('hidden', propertyType !== 'departamento');
    houseDetails.classList.toggle('hidden', propertyType !== 'casa');

    if (departmentBtn && houseBtn) {
        departmentBtn.classList.toggle('bg-gold', propertyType === 'departamento');
        departmentBtn.classList.toggle('text-white', propertyType === 'departamento');
        departmentBtn.classList.toggle('bg-white', propertyType !== 'departamento');
        departmentBtn.classList.toggle('text-midnight', propertyType !== 'departamento');

        houseBtn.classList.toggle('bg-gold', propertyType === 'casa');
        houseBtn.classList.toggle('text-white', propertyType === 'casa');
        houseBtn.classList.toggle('bg-paper-dark', propertyType !== 'casa');
        houseBtn.classList.toggle('text-midnight', propertyType !== 'casa');
    }

    // Control de Piscina Infinity (solo para casas)
    const poolCheckbox = document.getElementById('pool-checkbox');
    const infinityPoolLabel = document.getElementById('infinity-pool-label');
    const infinityPoolCheckbox = document.getElementById('infinity-pool-checkbox');

    if (propertyType === 'casa' && poolCheckbox && infinityPoolLabel && infinityPoolCheckbox) {
        poolCheckbox.removeEventListener('change', toggleInfinityPool);
        poolCheckbox.addEventListener('change', toggleInfinityPool);
    } else if (infinityPoolLabel && infinityPoolCheckbox) {
        infinityPoolLabel.classList.add('hidden');
        infinityPoolCheckbox.disabled = true;
        infinityPoolCheckbox.checked = false;
    }
}

/**
 * Controla la visibilidad y habilitacion de la opcion Piscina Infinity
 */


function toggleInfinityPool() {
    const poolCheckbox = document.getElementById('pool-checkbox');
    const infinityPoolLabel = document.getElementById('infinity-pool-label');
    const infinityPoolCheckbox = document.getElementById('infinity-pool-checkbox');

    if (!poolCheckbox || !infinityPoolLabel || !infinityPoolCheckbox) return;

    if (poolCheckbox.checked) {
        infinityPoolLabel.classList.remove('hidden');
        infinityPoolLabel.classList.remove('opacity-50');
        infinityPoolLabel.classList.remove('cursor-not-allowed');
        infinityPoolCheckbox.disabled = false;
    } else {
        infinityPoolLabel.classList.add('hidden');
        infinityPoolLabel.classList.add('opacity-50');
        infinityPoolLabel.classList.add('cursor-not-allowed');
        infinityPoolCheckbox.disabled = true;
        infinityPoolCheckbox.checked = false;
    }
}


const COUNTRY_STATES = {
    'Argentina': ['Buenos Aires','CABA','Catamarca','Chaco','Chubut','Córdoba','Corrientes','Entre Ríos','Formosa','Jujuy','La Pampa','La Rioja','Mendoza','Misiones','Neuquén','Río Negro','Salta','San Juan','San Luis','Santa Cruz','Santa Fe','Santiago del Estero','Tierra del Fuego','Tucumán'],
    'Uruguay': ['Artigas','Canelones','Cerro Largo','Colonia','Durazno','Flores','Florida','Lavalleja','Maldonado','Montevideo','Paysandú','Río Negro','Rivera','Rocha','Salto','San José','Soriano','Tacuarembó','Treinta y Tres'],
    'Chile': ['Arica y Parinacota','Tarapacá','Antofagasta','Atacama','Coquimbo','Valparaíso','Metropolitana de Santiago','O\'Higgins','Maule','Ñuble','Biobío','La Araucanía','Los Ríos','Los Lagos','Aysén','Magallanes'],
    'Brasil': ['Acre','Alagoas','Amapá','Amazonas','Bahía','Ceará','Distrito Federal','Espírito Santo','Goiás','Maranhão','Mato Grosso','Mato Grosso do Sul','Minas Gerais','Pará','Paraíba','Paraná','Pernambuco','Piauí','Rio de Janeiro','Rio Grande do Norte','Rio Grande do Sul','Rondônia','Roraima','Santa Catarina','São Paulo','Sergipe','Tocantins'],
    'Paraguay': ['Asunción','Alto Paraguay','Alto Paraná','Amambay','Boquerón','Caaguazú','Caazapá','Canindeyú','Central','Concepción','Cordillera','Guairá','Itapúa','Misiones','Ñeembucú','Paraguarí','Presidente Hayes','San Pedro'],
    'Bolivia': ['Chuquisaca','Cochabamba','Beni','La Paz','Oruro','Pando','Potosí','Santa Cruz','Tarija'],
    'Colombia': ['Amazonas','Antioquia','Arauca','Atlántico','Bogotá D.C.','Bolívar','Boyacá','Caldas','Caquetá','Casanare','Cauca','Cesar','Chocó','Córdoba','Cundinamarca','Guainía','Guaviare','Huila','La Guajira','Magdalena','Meta','Nariño','Norte de Santander','Putumayo','Quindío','Risaralda','San Andrés y Providencia','Santander','Sucre','Tolima','Valle del Cauca','Vaupés','Vichada'],
    'México': ['Aguascalientes','Baja California','Baja California Sur','Campeche','Chiapas','Chihuahua','Ciudad de México','Coahuila','Colima','Durango','Estado de México','Guanajuato','Guerrero','Hidalgo','Jalisco','Michoacán','Morelos','Nayarit','Nuevo León','Oaxaca','Puebla','Querétaro','Quintana Roo','San Luis Potosí','Sinaloa','Sonora','Tabasco','Tamaulipas','Tlaxcala','Veracruz','Yucatán','Zacatecas'],
    'España': ['Andalucía','Aragón','Asturias','Islas Baleares','Canarias','Cantabria','Castilla-La Mancha','Castilla y León','Cataluña','Comunidad Valenciana','Extremadura','Galicia','La Rioja','Madrid','Murcia','Navarra','País Vasco'],
    'Estados Unidos': ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawái','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Luisiana','Maine','Maryland','Massachusetts','Míchigan','Minnesota','Misisipi','Misuri','Montana','Nebraska','Nevada','Nuevo Hampshire','Nueva Jersey','Nuevo México','Nueva York','Carolina del Norte','Dakota del Norte','Ohio','Oklahoma','Oregón','Pensilvania','Rhode Island','Carolina del Sur','Dakota del Sur','Tennessee','Texas','Utah','Vermont','Virginia','Washington','Virginia Occidental','Wisconsin','Wyoming'],
    'Portugal': ['Aveiro','Beja','Braga','Bragança','Castelo Branco','Coimbra','Évora','Faro','Guarda','Leiria','Lisboa','Portalegre','Porto','Santarém','Setúbal','Viana do Castelo','Vila Real','Viseu','Madeira','Açores']
};


const CITY_SUGGESTIONS = [
    { city: 'Córdoba', country: 'Argentina', state: 'Córdoba' },
    { city: 'Villa General Belgrano', country: 'Argentina', state: 'Córdoba' },
    { city: 'Mina Clavero', country: 'Argentina', state: 'Córdoba' },
    { city: 'Santa Rosa de Calamuchita', country: 'Argentina', state: 'Córdoba' },
    { city: 'Buenos Aires', country: 'Argentina', state: 'CABA' },
    { city: 'Rosario', country: 'Argentina', state: 'Santa Fe' },
    { city: 'Mendoza', country: 'Argentina', state: 'Mendoza' },
    { city: 'Mar del Plata', country: 'Argentina', state: 'Buenos Aires' },
    { city: 'Salta', country: 'Argentina', state: 'Salta' },
    { city: 'Merlo', country: 'Argentina', state: 'San Luis' },
    { city: 'San Luis Capital', country: 'Argentina', state: 'San Luis' },
    { city: 'Montevideo', country: 'Uruguay', state: 'Montevideo' },
    { city: 'Punta del Este', country: 'Uruguay', state: 'Maldonado' },
    { city: 'Colonia del Sacramento', country: 'Uruguay', state: 'Colonia' },
    { city: 'Santiago', country: 'Chile', state: 'Metropolitana de Santiago' },
    { city: 'Valparaíso', country: 'Chile', state: 'Valparaíso' },
    { city: 'Viña del Mar', country: 'Chile', state: 'Valparaíso' },
    { city: 'São Paulo', country: 'Brasil', state: 'São Paulo' },
    { city: 'Río de Janeiro', country: 'Brasil', state: 'Río de Janeiro' },
    { city: 'Brasília', country: 'Brasil', state: 'Distrito Federal' },
    { city: 'Asunción', country: 'Paraguay', state: 'Asunción' },
    { city: 'Ciudad del Este', country: 'Paraguay', state: 'Alto Paraná' },
    { city: 'La Paz', country: 'Bolivia', state: 'La Paz' },
    { city: 'Santa Cruz de la Sierra', country: 'Bolivia', state: 'Santa Cruz' },
    { city: 'Bogotá', country: 'Colombia', state: 'Bogotá D.C.' },
    { city: 'Medellín', country: 'Colombia', state: 'Antioquia' },
    { city: 'Cali', country: 'Colombia', state: 'Valle del Cauca' },
    { city: 'Ciudad de México', country: 'México', state: 'Ciudad de México' },
    { city: 'Cancún', country: 'México', state: 'Quintana Roo' },
    { city: 'Guadalajara', country: 'México', state: 'Jalisco' },
    { city: 'Madrid', country: 'España', state: 'Madrid' },
    { city: 'Barcelona', country: 'España', state: 'Cataluña' },
    { city: 'Sevilla', country: 'España', state: 'Andalucía' },
    { city: 'Valencia', country: 'España', state: 'Comunidad Valenciana' },
    { city: 'Málaga', country: 'España', state: 'Andalucía' },
    { city: 'Nueva York', country: 'Estados Unidos', state: 'Nueva York' },
    { city: 'Miami', country: 'Estados Unidos', state: 'Florida' },
    { city: 'Los Ángeles', country: 'Estados Unidos', state: 'California' },
    { city: 'Lisboa', country: 'Portugal', state: 'Lisboa' },
    { city: 'Oporto', country: 'Portugal', state: 'Porto' },
];


const ARCHITECTURAL_STYLES = [
    t('style.modern'), t('style.classic'), t('style.minimalist'), t('style.industrial'), t('style.rustic'),
    t('style.contemporary'), t('style.vanguard'), t('style.traditional'), t('style.mediterranean'),
    t('style.nordic'), t('style.colonial'), t('style.art_deco'), t('style.bauhaus'), t('style.organic'),
    t('style.hightech'), t('style.neoclassic'), t('style.gothic'), t('style.baroque'), t('style.renaissance'), t('style.other')
];


const STATES_TERM = {
    'Estados Unidos': { label: 'Estado', placeholder: 'Seleccionar estado' },
    'México': { label: 'Estado', placeholder: 'Seleccionar estado' },
    'Brasil': { label: 'Estado', placeholder: 'Seleccionar estado' },
};


function initCountrySelector(provinceSelectId, countrySelectId) {
    var countrySelect = document.getElementById(countrySelectId || 'country-select');
    var provinceSelect = document.getElementById(provinceSelectId || 'province-select');
    if (!countrySelect || !provinceSelect) return;

    var provinceLabel = document.getElementById(provinceSelect.id + '-label');
    if (!provinceLabel) {
        provinceLabel = document.querySelector('label[for="' + provinceSelect.id + '"]');
    }

    function getStateTerm(country) {
        var fallback = { label: window.t('user.province'), placeholder: window.t('user.select_province') };
        var lang = window.__LANG || 'es';
        if (lang === 'es') {
            return STATES_TERM[country] || fallback;
        }
        return fallback;
    }

    function updateProvinces() {
        var country = countrySelect.value;
        var currentValue = provinceSelect.value;
        var states = COUNTRY_STATES[country] || [];
        var term = getStateTerm(country);
        provinceSelect.innerHTML = '<option value="">' + term.placeholder + '</option>';
        if (provinceLabel) {
            provinceLabel.textContent = term.label;
        }
        states.forEach(function(s) {
            var opt = document.createElement('option');
            opt.value = s;
            opt.textContent = s;
            if (s === currentValue) opt.selected = true;
            provinceSelect.appendChild(opt);
        });
        var zoneInput = document.getElementById('zone-input');
        if (zoneInput && zoneInput._zoneAutocompleteUpdate) zoneInput._zoneAutocompleteUpdate();
    }

    countrySelect.addEventListener('change', updateProvinces);
    provinceSelect.addEventListener('change', function() {
        var zoneInput = document.getElementById('zone-input');
        if (zoneInput && zoneInput._zoneAutocompleteUpdate) zoneInput._zoneAutocompleteUpdate();
    });
    if (countrySelect.value) updateProvinces();
}


function initZoneAutocomplete() {
    const zoneInput = document.getElementById('zone-input');
    const suggestions = document.getElementById('zone-suggestions');

    if (!zoneInput || !suggestions) return;

    const renderSuggestions = (items, query) => {
        if (!items.length && query.length > 0) {
            suggestions.innerHTML = `<li role="option" class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="${escapeHtml(query)}">
                        <strong class="text-midnight">${escapeHtml(t('autocomplete.use_query', {query: query}))}</strong><span class="ml-2 text-[11px] text-midnight/60">${escapeHtml(t('autocomplete.free_text'))}</span>
                    </li>`;
            suggestions.classList.remove('hidden');
            return;
        }

        if (!items.length) {
            suggestions.innerHTML = '<li role="status" class="px-4 py-3 text-sm text-midnight/60">' + escapeHtml(t('autocomplete.type_zone')) + '</li>';
            suggestions.classList.remove('hidden');
            return;
        }

        suggestions.innerHTML = items.map(item => {
            var stateInfo = item.state ? ', <span class="text-midnight/40">' + escapeHtml(item.state) + '</span>' : '';
            return `<li role="option" class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="${escapeHtml(item.city)}">
                        <strong class="text-midnight">${escapeHtml(item.city)}</strong>${stateInfo}<span class="ml-2 text-[11px] text-midnight/60">${escapeHtml(item.country)}</span>
                    </li>`;
        }).join('');
        suggestions.classList.remove('hidden');
    };

    const update = () => {
        var countrySelect = document.getElementById('country-select');
        var provinceSelect = document.getElementById('province-select');
        var selectedCountry = countrySelect ? countrySelect.value : '';
        var selectedProvince = provinceSelect ? provinceSelect.value : '';
        const query = zoneInput.value.trim().toLowerCase();
        var pool = CITY_SUGGESTIONS;
        if (selectedCountry) {
            pool = pool.filter(function(item) { return item.country === selectedCountry; });
        }
        if (!selectedProvince) {
            renderSuggestions([], query);
            return;
        }
        pool = pool.filter(function(item) { return item.state === selectedProvince; });
        const items = query.length === 0
            ? pool.slice(0, 5)
            : pool.filter(item => item.city.toLowerCase().includes(query) || item.country.toLowerCase().includes(query));
        renderSuggestions(items, zoneInput.value.trim());
    };

    zoneInput._zoneAutocompleteUpdate = update;

    zoneInput.addEventListener('input', update);
    zoneInput.addEventListener('focus', update);

    document.addEventListener('click', (event) => {
        if (!suggestions.contains(event.target) && event.target !== zoneInput) {
            suggestions.classList.add('hidden');
        }
    });

    suggestions.addEventListener('click', (event) => {
        const target = event.target.closest('li[data-value]');
        if (!target) return;
        zoneInput.value = target.getAttribute('data-value');
        suggestions.classList.remove('hidden');
    });
}


function initArchitecturalStyleAutocomplete() {
    const styleInput = document.getElementById('architectural-style-input');
    const suggestions = document.getElementById('architectural-style-suggestions');

    if (!styleInput || !suggestions) return;

    const renderSuggestions = (items) => {
        if (!items.length) {
            suggestions.innerHTML = '<li role="status" class="px-4 py-3 text-sm text-midnight/60">' + escapeHtml(t('autocomplete.no_matches')) + '</li>';
            suggestions.classList.remove('hidden');
            return;
        }

        suggestions.innerHTML = items.map(item => {
            return `<li role="option" class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="${escapeHtml(item)}">
                        <strong class="text-midnight">${escapeHtml(item)}</strong>
                    </li>`;
        }).join('');
        suggestions.classList.remove('hidden');
    };

    const update = () => {
        const query = styleInput.value.trim().toLowerCase();
        const items = query.length === 0
            ? ARCHITECTURAL_STYLES.slice(0, 5)
            : ARCHITECTURAL_STYLES.filter(item => item.toLowerCase().includes(query));
        renderSuggestions(items);
    };

    styleInput.addEventListener('input', update);
    styleInput.addEventListener('focus', update);

    document.addEventListener('click', (event) => {
        if (!suggestions.contains(event.target) && event.target !== styleInput) {
            suggestions.classList.add('hidden');
        }
    });

    suggestions.addEventListener('click', (event) => {
        const target = event.target.closest('li[data-value]');
        if (!target) return;
        styleInput.value = target.getAttribute('data-value');
        suggestions.classList.add('hidden');
    });
}


function initHouseAreaValidation() {
    const landInput = document.getElementById('house-land-area');
    const builtInput = document.getElementById('house-built-area');
    const warning = document.getElementById('house-area-warning');
    if (!landInput || !builtInput || !warning) return;

    function checkArea() {
        const land = parseFloat(landInput.value || '0');
        const built = parseFloat(builtInput.value || '0');
        if (land > 0 && built > 0 && built > land * 0.8) {
            warning.classList.remove('hidden');
            builtInput.classList.add('border-rose-500');
            builtInput.classList.remove('border-midnight/20');
        } else {
            warning.classList.add('hidden');
            builtInput.classList.remove('border-rose-500');
            builtInput.classList.add('border-midnight/20');
        }
    }

    landInput.addEventListener('input', checkArea);
    builtInput.addEventListener('input', checkArea);
}


function initDuplexAreaValidation() {
    const landInput = document.getElementById('duplex-land-area');
    const builtInput = document.getElementById('duplex-built-area');
    const warning = document.getElementById('duplex-area-warning');
    if (!landInput || !builtInput || !warning) return;

    function checkArea() {
        const land = parseFloat(landInput.value || '0');
        const built = parseFloat(builtInput.value || '0');
        if (land > 0 && built > 0 && built > land * 0.8) {
            warning.classList.remove('hidden');
            builtInput.classList.add('border-rose-500');
            builtInput.classList.remove('border-midnight/20');
        } else {
            warning.classList.add('hidden');
            builtInput.classList.remove('border-rose-500');
            builtInput.classList.add('border-midnight/20');
        }
    }

    landInput.addEventListener('input', checkArea);
    builtInput.addEventListener('input', checkArea);
}

document.addEventListener('DOMContentLoaded', function() {
    initHouseAreaValidation();
    initDuplexAreaValidation();
});

/**
 * Mobile Menu Toggle — focus trap, scroll lock, click-outside
 */


/* API pública */
window.validateEmail = validateEmail;
window.validatePhone = validatePhone;
window.validateZone = validateZone;
window.combineCountryAreaPhone = combineCountryAreaPhone;
window.initUserForm = initUserForm;
window.selectPropertyType = selectPropertyType;
window.toggleInfinityPool = toggleInfinityPool;
window.initCountrySelector = initCountrySelector;
window.initZoneAutocomplete = initZoneAutocomplete;
window.initArchitecturalStyleAutocomplete = initArchitecturalStyleAutocomplete;
window.initHouseAreaValidation = initHouseAreaValidation;
window.combineCountryAreaPhone = combineCountryAreaPhone;
window.initDuplexAreaValidation = initDuplexAreaValidation;

})();

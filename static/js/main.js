/**
 * LOGICA PRINCIPAL - ARCHESTATE
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar iconos de Lucide al cargar la página
    if (window.lucide) {
        lucide.createIcons();
    }

    // Inicializar lógica específica de la vista de Usuario
    initUserForm();
});

/**
 * Sistema de Notificaciones Toast
 */
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-8 right-8 z-[100] flex flex-col gap-3';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-emerald-600' : type === 'error' ? 'bg-rose-600' : 'bg-midnight';
    const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info';

    toast.className = `${bgColor} text-white px-6 py-4 rounded shadow-2xl flex items-center gap-4 transform transition-all duration-500 translate-y-10 opacity-0 border border-white/10`;
    toast.style.minWidth = '300px';
    
    toast.innerHTML = `
        <div class="flex-shrink-0">
            <i data-lucide="${icon}" class="w-5 h-5"></i>
        </div>
        <div class="flex-grow">
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] leading-tight">${message}</p>
        </div>
    `;

    container.appendChild(toast);
    if (window.lucide) {
        lucide.createIcons({
            attrs: { class: 'lucide' },
            nameAttr: 'data-lucide',
            icons: window.lucide.icons
        });
    }

    // Animación de entrada
    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-10', 'opacity-0');
    });

    // Auto-eliminación
    setTimeout(() => {
        toast.classList.add('opacity-0', '-translate-y-2');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

/**
 * Validación de Email (Feedback visual en tiempo real)
 * Nota: La validación real y final ocurre en Python (app.py)
 */
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
 * Inicialización del formulario de usuario
 */
function initUserForm() {
    const form = document.getElementById('userForm');
    const emailInput = document.getElementById('email-input');
    const departmentBtn = document.getElementById('btn-department');
    const houseBtn = document.getElementById('btn-house');

    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateEmail(this.value);
        });
    }

    if (departmentBtn) {
        departmentBtn.addEventListener('click', () => selectPropertyType('departamento'));
    }

    if (houseBtn) {
        houseBtn.addEventListener('click', () => selectPropertyType('casa'));
    }

    selectPropertyType('departamento');
    initZoneAutocomplete();
    initArchitecturalStyleAutocomplete();
    initBudgetPopup();

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Recolectar amenities seleccionadas
            const amenitiesCheckboxes = document.querySelectorAll('input[name="amenities_values"]:checked');
            data.amenities = Array.from(amenitiesCheckboxes).map(cb => cb.value).join(', ');

            // Validación de área para casas
            const landArea = parseInt(data.land_area || '0', 10);
            const builtArea = parseInt(data.built_area || '0', 10);
            if (data.property_type === 'casa' && builtArea > landArea) {
                showToast('Los metros construidos no pueden ser mayores que los metros de terreno.', 'error');
                return;
            }

            // Validación rápida en cliente
            if (!validateEmail(data.email)) return;

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalBtnContent = submitBtn.innerHTML;
            
            // Estado de carga
            submitBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Procesando...`;
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-70');

            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    showToast("¡Solicitud enviada! Los profesionales se contactarán contigo.");
                    setTimeout(() => {
                        window.location.href = "/";
                    }, 1500);
                } else {
                    // Manejar errores devueltos por Python
                    submitBtn.innerHTML = originalBtnContent;
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('opacity-70');
                    showToast(result.message, 'error');
                }
            } catch (error) {
                submitBtn.innerHTML = originalBtnContent;
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-70');
                console.error("Error al enviar el formulario:", error);
                showToast("Error de conexión con el servidor", 'error');
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
        { value: 'Comprar Propiedad', text: 'Comprar' },
        { value: 'Remodelación Integral', text: 'Remodelación' }
    ];
    const houseOptions = [
        { value: 'Comprar Propiedad', text: 'Comprar' },
        { value: 'Construir desde Cero', text: 'Construir' },
        { value: 'Remodelación Integral', text: 'Remodelación' }
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
        // Agregar event listener al checkbox de piscina
        poolCheckbox.removeEventListener('change', toggleInfinityPool); // Remover listeners previos
        poolCheckbox.addEventListener('change', toggleInfinityPool);
    } else if (infinityPoolLabel && infinityPoolCheckbox) {
        // Ocultar piscina infinity si no es casa
        infinityPoolLabel.classList.add('hidden');
        infinityPoolCheckbox.disabled = true;
        infinityPoolCheckbox.checked = false;
    }
}

/**
 * Controla la visibilidad y habilitación de la opción Piscina Infinity
 * Solo se muestra si está seleccionada la opción "¿Tiene piscina?"
 */
function toggleInfinityPool() {
    const poolCheckbox = document.getElementById('pool-checkbox');
    const infinityPoolLabel = document.getElementById('infinity-pool-label');
    const infinityPoolCheckbox = document.getElementById('infinity-pool-checkbox');

    if (!poolCheckbox || !infinityPoolLabel || !infinityPoolCheckbox) return;

    if (poolCheckbox.checked) {
        // Mostrar y habilitar Piscina Infinity
        infinityPoolLabel.classList.remove('hidden');
        infinityPoolLabel.classList.remove('opacity-50');
        infinityPoolLabel.classList.remove('cursor-not-allowed');
        infinityPoolCheckbox.disabled = false;
    } else {
        // Ocultar y deshabilitar Piscina Infinity
        infinityPoolLabel.classList.add('hidden');
        infinityPoolLabel.classList.add('opacity-50');
        infinityPoolLabel.classList.add('cursor-not-allowed');
        infinityPoolCheckbox.disabled = true;
        infinityPoolCheckbox.checked = false;
    }
}

const CITY_SUGGESTIONS = [
    { city: 'Córdoba', country: 'Argentina' },
    { city: 'Córdoba', country: 'España' },
    { city: 'Madrid', country: 'España' },
    { city: 'Barcelona', country: 'España' },
    { city: 'Villa General Belgrano', country: 'Argentina' },
    { city: 'Mina Clavero', country: 'Argentina' },
    { city: 'Merlo', country: 'Argentina' },
    { city: 'San Luis Capital', country: 'Argentina' },
    { city: 'Santa Rosa de Calamuchita', country: 'Argentina' },
    { city: 'Lisboa', country: 'Portugal' },
    { city: 'Santiago', country: 'Chile' },
    { city: 'Punta del Este', country: 'Uruguay' }
];

const ARCHITECTURAL_STYLES = [
    'Moderno',
    'Clásico',
    'Minimalista',
    'Industrial',
    'Rústico',
    'Contemporáneo',
    'Vanguardista',
    'Tradicional',
    'Mediterráneo',
    'Nórdico',
    'Colonial',
    'Art Decó',
    'Bauhaus',
    'Orgánico',
    'High-Tech',
    'Neoclásico',
    'Gótico',
    'Barroco',
    'Renacentista',
    'Otro'
];

function initZoneAutocomplete() {
    const zoneInput = document.getElementById('zone-input');
    const suggestions = document.getElementById('zone-suggestions');

    if (!zoneInput || !suggestions) return;

    const renderSuggestions = (items) => {
        if (!items.length) {
            suggestions.innerHTML = '<li class="px-4 py-3 text-sm text-midnight/60">Sin coincidencias</li>';
            suggestions.classList.remove('hidden');
            return;
        }

        suggestions.innerHTML = items.map(item => {
            return `<li class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="${item.city}, ${item.country}">
                        <strong class="text-midnight">${item.city}</strong><span class="ml-2 text-[11px] text-midnight/60">${item.country}</span>
                    </li>`;
        }).join('');
        suggestions.classList.remove('hidden');
    };

    const update = () => {
        const query = zoneInput.value.trim().toLowerCase();
        const items = query.length === 0
            ? CITY_SUGGESTIONS.slice(0, 5)
            : CITY_SUGGESTIONS.filter(item => item.city.toLowerCase().includes(query) || item.country.toLowerCase().includes(query));
        renderSuggestions(items);
    };

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
        suggestions.classList.add('hidden');
    });
}

function initArchitecturalStyleAutocomplete() {
    const styleInput = document.getElementById('architectural-style-input');
    const suggestions = document.getElementById('architectural-style-suggestions');

    if (!styleInput || !suggestions) return;

    const renderSuggestions = (items) => {
        if (!items.length) {
            suggestions.innerHTML = '<li class="px-4 py-3 text-sm text-midnight/60">Sin coincidencias</li>';
            suggestions.classList.remove('hidden');
            return;
        }

        suggestions.innerHTML = items.map(item => {
            return `<li class="cursor-pointer px-4 py-3 border-b border-slate-100 hover:bg-slate-50" data-value="${item}">
                        <strong class="text-midnight">${item}</strong>
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

function initBudgetPopup() {
    const trigger = document.getElementById('budget-popup-trigger');
    const popup = document.getElementById('budget-popup');
    const close = document.getElementById('budget-popup-close');
    const resetBtn = document.getElementById('budget-reset');
    const acceptBtn = document.getElementById('budget-accept');
    const minSlider = document.getElementById('budget-min-slider');
    const maxSlider = document.getElementById('budget-max-slider');
    const currencySelect = document.getElementById('budget-currency-select');
    const hiddenBudget = document.getElementById('budget-hidden');
    const hiddenCurrency = document.getElementById('currency-hidden');
    const sliderFill = document.getElementById('budget-slider-fill');
    const unlimitedCheckbox = document.getElementById('budget-unlimited');

    if (!trigger || !popup || !minSlider || !maxSlider || !currencySelect || !hiddenBudget || !hiddenCurrency || !sliderFill || !unlimitedCheckbox) return;

    let budgetData = {
        min: 0,
        max: 150000000,
        ranges: []
    };

    const formatMoney = (value, currency = 'ARG') => {
        const symbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '$';
        return `${symbol}${Number(value).toLocaleString('es-AR')}`;
    };

    const setSliderPositions = () => {
        const minValue = Number(minSlider.value);
        const maxValue = Number(maxSlider.value);
        const isUnlimited = unlimitedCheckbox.checked;
        let minPercent, maxPercent;
        if (isUnlimited) {
            // Para ilimitado, usar una escala arbitraria, e.g., hasta 200M para visualización
            const visualMax = Math.max(maxValue * 1.2, 200000000);
            minPercent = (minValue / visualMax) * 100;
            maxPercent = (maxValue / visualMax) * 100;
        } else {
            minPercent = ((minValue - budgetData.min) / (budgetData.max - budgetData.min)) * 100;
            maxPercent = ((maxValue - budgetData.min) / (budgetData.max - budgetData.min)) * 100;
        }
        sliderFill.style.left = `${Math.max(minPercent, 0)}%`;
        sliderFill.style.width = `${Math.max(maxPercent - minPercent, 0)}%`;

        document.getElementById('budget-selected-range').textContent = `${formatMoney(minValue, currencySelect.value)} — ${isUnlimited && maxValue >= 150000000 ? 'Ilimitado' : formatMoney(maxValue, currencySelect.value)}`;
        hiddenCurrency.value = currencySelect.value;
    };

    const updateManualInputs = () => {
        document.getElementById('budget-min-input').value = minSlider.value;
        document.getElementById('budget-max-input').value = maxSlider.value;
    };

    const toggleUnlimited = () => {
        const isUnlimited = unlimitedCheckbox.checked;
        if (isUnlimited) {
            minSlider.removeAttribute('max');
            maxSlider.removeAttribute('max');
            document.getElementById('budget-min-input').removeAttribute('max');
            document.getElementById('budget-max-input').removeAttribute('max');
        } else {
            minSlider.max = budgetData.max;
            maxSlider.max = budgetData.max;
            document.getElementById('budget-min-input').max = budgetData.max;
            document.getElementById('budget-max-input').max = budgetData.max;
        }
    };

    const updateBudgetOutput = () => {
        const minValue = Number(minSlider.value);
        const maxValue = Number(maxSlider.value);
        const isUnlimited = unlimitedCheckbox.checked;
        hiddenBudget.value = `${minValue} - ${maxValue}`;
        if (isUnlimited) {
            trigger.textContent = "Presupuesto mayor a 150M";
        } else {
            trigger.textContent = `Presupuesto: ${formatMoney(minValue, currencySelect.value)} — ${formatMoney(maxValue, currencySelect.value)}`;
        }
        setSliderPositions();
        updateManualInputs();
    };

    const resetBudget = () => {
        minSlider.min = budgetData.min;
        minSlider.max = budgetData.max;
        maxSlider.min = budgetData.min;
        maxSlider.max = budgetData.max;
        minSlider.value = budgetData.min;
        maxSlider.value = budgetData.max;
        document.getElementById('budget-min-input').min = budgetData.min;
        document.getElementById('budget-max-input').min = budgetData.min;
        document.getElementById('budget-min-input').value = budgetData.min;
        document.getElementById('budget-max-input').value = budgetData.max;
        currencySelect.value = hiddenCurrency.value || 'ARG';
        unlimitedCheckbox.checked = false;
        toggleUnlimited();
        updateBudgetOutput();
    };

    const fetchBudgetStats = async () => {
        try {
            const response = await fetch('/api/budget-stats');
            const result = await response.json();
            budgetData = {
                min: typeof result.min === 'number' ? result.min : budgetData.min,
                max: typeof result.max === 'number' ? result.max : budgetData.max,
                ranges: result.ranges || []
            };
            currencySelect.innerHTML = (result.currency_options || ['ARG','USD','EUR']).map(code => `<option value="${code}">${code === 'USD' ? 'Dólares' : code === 'EUR' ? 'Euros' : 'Pesos'}</option>`).join('');
            resetBudget();
        } catch (error) {
            console.error('No se pudieron cargar las estadísticas de presupuesto:', error);
            budgetData = {
                min: 0,
                max: 150000000,
                ranges: []
            };
            resetBudget();
        }
    };

    const syncInputsToSliders = () => {
        const minInput = Number(document.getElementById('budget-min-input').value);
        const maxInput = Number(document.getElementById('budget-max-input').value);
        const isUnlimited = unlimitedCheckbox.checked;
        if (!Number.isFinite(minInput) || minInput < budgetData.min) return;
        if (!Number.isFinite(maxInput)) return;
        if (!isUnlimited && minInput > maxInput) return;
        if (isUnlimited && minInput > maxInput) return; // Permitir si ilimitado
        minSlider.value = minInput;
        maxSlider.value = maxInput;
        updateBudgetOutput();
    };

    const handleSliderChange = () => {
        if (Number(minSlider.value) > Number(maxSlider.value) - Number(minSlider.step)) {
            minSlider.value = Number(maxSlider.value) - Number(minSlider.step);
        }
        if (Number(maxSlider.value) < Number(minSlider.value) + Number(maxSlider.step)) {
            maxSlider.value = Number(minSlider.value) + Number(maxSlider.step);
        }
        updateBudgetOutput();
    };

    const minInputElement = document.getElementById('budget-min-input');
    const maxInputElement = document.getElementById('budget-max-input');
    if (minInputElement) {
        minInputElement.addEventListener('input', () => {
            const value = Number(minInputElement.value);
            const isUnlimited = unlimitedCheckbox.checked;
            if (Number.isFinite(value) && value >= budgetData.min && (isUnlimited || value <= Number(maxSlider.value))) {
                minSlider.value = value;
                updateBudgetOutput();
            }
        });
    }
    if (maxInputElement) {
        maxInputElement.addEventListener('input', () => {
            const value = Number(maxInputElement.value);
            const isUnlimited = unlimitedCheckbox.checked;
            if (Number.isFinite(value) && (isUnlimited || value >= Number(minSlider.value))) {
                maxSlider.value = value;
                updateBudgetOutput();
            }
        });
    }

    minSlider.addEventListener('input', handleSliderChange);
    maxSlider.addEventListener('input', handleSliderChange);
    currencySelect.addEventListener('change', updateBudgetOutput);
    unlimitedCheckbox.addEventListener('change', toggleUnlimited);
    trigger.addEventListener('click', () => {
        popup.classList.remove('hidden');
        popup.scrollTop = 0;
    });
    close.addEventListener('click', () => popup.classList.add('hidden'));
    popup.addEventListener('click', (event) => {
        if (event.target === popup) popup.classList.add('hidden');
    });
    resetBtn.addEventListener('click', resetBudget);
    acceptBtn.addEventListener('click', () => {
        updateBudgetOutput();
        popup.classList.add('hidden');
    });

    fetchBudgetStats();
}

/**
 * Alternar visibilidad del teléfono (Lógica de seguridad en Python)
 * Permite mostrar y ocultar el teléfono una vez obtenido.
 */
async function togglePhone(btn, leadId) {
    const isRevealed = btn.getAttribute('data-revealed') === 'true';

    if (isRevealed) {
        // Ocultar de nuevo
        btn.innerHTML = `<i data-lucide="eye" class="w-3 h-3"></i> Ver Teléfono`;
        btn.setAttribute('data-revealed', 'false');
        btn.classList.remove('bg-gold');
        btn.classList.add('bg-midnight');
    } else {
        // Mostrar (usar caché si ya se pidió)
        const cachedPhone = btn.getAttribute('data-phone');
        
        if (cachedPhone) {
            btn.innerHTML = `<i data-lucide="eye-off" class="w-3 h-3"></i> ${cachedPhone}`;
            btn.setAttribute('data-revealed', 'true');
            btn.classList.remove('bg-midnight');
            btn.classList.add('bg-gold');
        } else {
            // Estado de carga
            const originalContent = btn.innerHTML;
            btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i> Cargando...`;
            btn.disabled = true;
            btn.classList.add('opacity-70');

            try {
                const response = await fetch(`/api/lead/${leadId}/phone`);
                const data = await response.json();
                
                if (data.phone) {
                    btn.setAttribute('data-phone', data.phone);
                    btn.innerHTML = `<i data-lucide="eye-off" class="w-3 h-3"></i> ${data.phone}`;
                    btn.setAttribute('data-revealed', 'true');
                    btn.classList.remove('bg-midnight');
                    btn.classList.add('bg-gold');
                } else {
                    btn.innerHTML = originalContent;
                    showToast("No se pudo obtener el teléfono", 'error');
                }
            } catch (error) {
                btn.innerHTML = originalContent;
                console.error("Error al obtener teléfono:", error);
                showToast("Error de red al consultar teléfono", 'error');
            } finally {
                btn.disabled = false;
                btn.classList.remove('opacity-70');
            }
        }
    }
    
    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Actualizar estado de un profesional (Aprobar/Rechazar)
 */
async function updateProStatus(proId, status, btn) {
    const isRejection = status === 'rejected';
    const message = isRejection 
        ? "¡ADVERTENCIA! Está a punto de RECHAZAR a este profesional. Esta acción es crítica y quedará registrada permanentemente en el log de auditoría. ¿Está completamente seguro?"
        : "¿Desea aprobar a este profesional para que pueda acceder a la plataforma?";

    if (!confirm(message)) {
        return;
    }

    // Estado de carga
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>`;
    btn.disabled = true;
    btn.classList.add('opacity-50');

    try {
        const response = await fetch(`/api/admin/professional/${proId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        });

        const result = await response.json();

        if (response.ok) {
            // Animación de éxito: Escalado y cambio de color
            btn.classList.remove('opacity-50', 'text-emerald-600', 'text-rose-600');
            btn.classList.add('scale-150', 'text-emerald-500', 'transition-all', 'duration-500', 'ease-out');
            btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i>`;
            
            if (window.lucide) lucide.createIcons();
            
            showToast(result.message);
            
            // Desvanecer la fila antes de recargar
            const row = btn.closest('tr');
            if (row) {
                // Actualizar visualmente el estado en la tabla
                const statusCell = row.cells[2];
                if (statusCell) {
                    const label = status === 'approved' 
                        ? '<span class="px-2 py-1 bg-emerald-50 text-emerald-700 text-[9px] font-bold uppercase tracking-widest rounded">Aprobado</span>'
                        : '<span class="px-2 py-1 bg-rose-50 text-rose-700 text-[9px] font-bold uppercase tracking-widest rounded">Rechazado</span>';
                    statusCell.innerHTML = label;
                }

                // Ocultar botones de acción
                const actionCell = row.cells[3];
                if (actionCell) {
                    actionCell.innerHTML = '<span class="text-[10px] text-midnight/20 font-bold uppercase tracking-widest animate-pulse">Procesado</span>';
                }

                row.classList.add('transition-opacity', 'duration-1000', 'opacity-30', 'pointer-events-none');
            }

            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            btn.innerHTML = originalContent;
            btn.disabled = false;
            btn.classList.remove('opacity-50');
            showToast(result.error, 'error');
        }
    } catch (error) {
        btn.innerHTML = originalContent;
        btn.disabled = false;
        btn.classList.remove('opacity-50');
        console.error("Error al actualizar estado:", error);
        showToast("Error al conectar con el servidor", 'error');
    }
}

/**
 * LÓGICA DINÁMICA PARA EL REGISTRO
 */
document.addEventListener('DOMContentLoaded', function() {
    const roleSelect = document.querySelector('select[name="role"]');
    const licenseContainer = document.getElementById('license-container');
    const licenseInput = document.getElementById('license-input');

    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
            if (this.value === 'professional') {
                // Mostrar campo de matrícula
                licenseContainer.classList.remove('hidden');
                licenseContainer.classList.add('block');
                licenseInput.setAttribute('required', 'required');
                
                // Refrescar iconos de Lucide por si acaso
                if (window.lucide) lucide.createIcons();
            } else {
                // Ocultar campo
                licenseContainer.classList.add('hidden');
                licenseContainer.classList.remove('block');
                licenseInput.removeAttribute('required');
            }
        });
    }
});
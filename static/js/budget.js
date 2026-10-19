/* budget.js — extraído de main.js (FASE 5.2). Carga después de main.js. */
(function () {

function validateBudget(val) {
    if (!val && val !== 0) return false;
    const num = parseFloat(val);
    const isValid = !isNaN(num) && num > 0 && num <= 1000000000000;
    const errorEl = document.getElementById('budget-error');
    const inputEl = document.getElementById('budget-input');
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
 * Validacion cruzada de moneda vs presupuesto
 */


function validateBudgetForCurrency(budget, currency) {
    var RANGES = {
        ARG: { min: 100000, max: 10000000000, label: 'ARS ($)' },
        USD: { min: 10000,  max: 100000000,   label: 'USD (US$)' },
        EUR: { min: 10000,  max: 100000000,   label: 'EUR (€)' },
    };
    var range = RANGES[currency];
    if (!range) return { isValid: false, message: t('validator.currency_invalid') };
    var parts = String(budget).split(' - ');
    var minVal = parseFloat((parts[0] || '').replace(/\./g, ''));
    var maxVal = parts[1] ? parseFloat(parts[1].replace(/\./g, '')) : minVal;
    if (!Number.isFinite(minVal) || !Number.isFinite(maxVal)) {
        return { isValid: false, message: t('validator.budget_invalid') };
    }
    if (minVal === 0) return { isValid: true, message: null };
    if (minVal < range.min) {
        return { isValid: false, message: t('validator.budget_min_for_currency', {label: range.label, min: range.min.toLocaleString('es-AR')}) };
    }
    if (minVal > range.max) {
        return { isValid: false, message: t('validator.budget_max_for_currency', {label: range.label, max: range.max.toLocaleString('es-AR')}) };
    }
    if (maxVal > range.max) {
        return { isValid: false, message: t('validator.budget_max_for_currency', {label: range.label, max: range.max.toLocaleString('es-AR')}) };
    }
    return { isValid: true, message: null };
}

/**
 * Validación de Zona (texto libre)
 */


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
    const minInput = document.getElementById('budget-min-input');
    const maxInput = document.getElementById('budget-max-input');

    if (!trigger || !popup || !minSlider || !maxSlider || !currencySelect || !hiddenBudget || !hiddenCurrency || !sliderFill || !unlimitedCheckbox || !minInput || !maxInput) return;

    var CURRENCY_CONFIG = {
        ARG: { max: 10000000000, step: 10000000, label: 'ARS ($)' },
        USD: { max: 100000000,  step: 100000,   label: 'USD (US$)' },
        EUR: { max: 100000000,  step: 100000,   label: 'EUR (€)' },
    };

    let budgetData = {
        min: 0,
        max: 10000000000,
        ranges: []
    };

    const getCurrencyConfig = (code) => CURRENCY_CONFIG[code] || CURRENCY_CONFIG.ARG;

    const updateSliderRange = () => {
        var config = getCurrencyConfig(currencySelect.value);
        budgetData.max = config.max;
        var step = config.step;
        var isUnlimited = unlimitedCheckbox.checked;
        minSlider.max = budgetData.max;
        maxSlider.max = budgetData.max;
        minSlider.step = step;
        maxSlider.step = step;
        document.getElementById('budget-min-input').max = budgetData.max;
        document.getElementById('budget-max-input').max = budgetData.max;
        document.getElementById('budget-min-input').step = step;
        document.getElementById('budget-max-input').step = step;
        if (isUnlimited) {
            updateManualInputs();
            updateBudgetOutput();
            return;
        }
        if (Number(minSlider.value) > budgetData.max) minSlider.value = budgetData.max;
        if (Number(maxSlider.value) > budgetData.max) maxSlider.value = budgetData.max;
        updateManualInputs();
        updateBudgetOutput();
    };

    const formatMoney = (value, currency = 'ARG') => {
        const symbol = currency === 'USD' ? 'US$' : currency === 'EUR' ? '€' : '$';
        return `${symbol}${Number(value).toLocaleString('es-AR')}`;
    };

    const setSliderPositions = () => {
        const minValue = Number(minSlider.value);
        const maxValue = Number(maxSlider.value);
        const isUnlimited = unlimitedCheckbox.checked;
        let minPercent, maxPercent;
        if (isUnlimited) {
            const visualMax = Math.max(maxValue * 1.2, 200000000);
            minPercent = (minValue / visualMax) * 100;
            maxPercent = (maxValue / visualMax) * 100;
        } else {
            minPercent = ((minValue - budgetData.min) / (budgetData.max - budgetData.min)) * 100;
            maxPercent = ((maxValue - budgetData.min) / (budgetData.max - budgetData.min)) * 100;
        }
        sliderFill.style.left = `${Math.max(minPercent, 0)}%`;
        sliderFill.style.width = `${Math.max(maxPercent - minPercent, 0)}%`;

        document.getElementById('budget-selected-range').textContent = `${formatMoney(minValue, currencySelect.value)} — ${isUnlimited && maxValue >= budgetData.max ? t('budget.unlimited') : formatMoney(maxValue, currencySelect.value)}`;
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
        updateBudgetOutput();
    };

    const updateBudgetOutput = () => {
        const minValue = Number(minSlider.value);
        const maxValue = Number(maxSlider.value);
        const isUnlimited = unlimitedCheckbox.checked;
        // min 0 = "hasta max": el backend exige partes > 0, no enviar "0 - X".
        hiddenBudget.value = minValue > 0 ? `${minValue} - ${maxValue}` : `${maxValue}`;
        if (isUnlimited) {
            trigger.textContent = t('budget.greater_than') + formatMoney(budgetData.max, currencySelect.value);
        } else {
            trigger.textContent = `${t('budget.label')}${formatMoney(minValue, currencySelect.value)} — ${formatMoney(maxValue, currencySelect.value)}`;
        }
        setSliderPositions();
        updateManualInputs();
    };

    const resetBudget = () => {
        minSlider.min = budgetData.min;
        maxSlider.min = budgetData.min;
        minSlider.value = budgetData.min;
        maxSlider.value = budgetData.max;
        document.getElementById('budget-min-input').min = budgetData.min;
        document.getElementById('budget-max-input').min = budgetData.min;
        document.getElementById('budget-min-input').value = budgetData.min;
        document.getElementById('budget-max-input').value = budgetData.max;
        currencySelect.value = hiddenCurrency.value || 'ARG';
        unlimitedCheckbox.checked = false;
        toggleUnlimited();
        updateSliderRange();
    };

    const fetchBudgetStats = async () => {
        try {
            const response = await fetch('/estadisticas-popup');
            const result = await response.json();
            budgetData = {
                min: typeof result.min === 'number' ? result.min : budgetData.min,
                max: typeof result.max === 'number' ? result.max : budgetData.max,
                ranges: result.ranges || []
            };
            currencySelect.innerHTML = (result.currency_options || ['ARG','USD','EUR']).map(code => `<option value="${escapeHtml(code)}">${code === 'USD' ? t('currency.usd_name') : code === 'EUR' ? t('currency.eur_name') : t('currency.arg_name')}</option>`).join('');
            resetBudget();
        } catch (error) {
            console.error('No se pudieron cargar las estadisticas de presupuesto:', error);
            budgetData = { min: 0, max: 10000000000, ranges: [] };
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
        if (isUnlimited && minInput > maxInput) return;
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
            if (Number.isFinite(value) && value >= budgetData.min && (isUnlimited || value <= budgetData.max) && (isUnlimited || value <= Number(maxSlider.value))) {
                minSlider.value = value;
                updateBudgetOutput();
            }
        });
    }
    if (maxInputElement) {
        maxInputElement.addEventListener('input', () => {
            const value = Number(maxInputElement.value);
            const isUnlimited = unlimitedCheckbox.checked;
            if (Number.isFinite(value) && value >= budgetData.min && (isUnlimited || value <= budgetData.max) && (isUnlimited || value >= Number(minSlider.value))) {
                maxSlider.value = value;
                updateBudgetOutput();
            }
        });
    }

    minSlider.addEventListener('input', handleSliderChange);
    maxSlider.addEventListener('input', handleSliderChange);
    currencySelect.addEventListener('change', function() {
        updateSliderRange();
        updateBudgetOutput();
    });
    unlimitedCheckbox.addEventListener('change', toggleUnlimited);
    trigger.addEventListener('click', () => {
        openModalAnim(popup);
        popup.scrollTop = 0;
    });
    close.addEventListener('click', () => closeModalAnim(popup));
    popup.addEventListener('click', (event) => {
        if (event.target === popup) closeModalAnim(popup);
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !popup.classList.contains('hidden')) {
            closeModalAnim(popup);
        }
    });
    resetBtn.addEventListener('click', resetBudget);
    acceptBtn.addEventListener('click', () => {
        updateBudgetOutput();
        closeModalAnim(popup);
    });

    fetchBudgetStats();
}

/**
 * Alternar visibilidad del telefono
 */


/* API pública */
window.validateBudget = validateBudget;
window.validateBudgetForCurrency = validateBudgetForCurrency;
window.initBudgetPopup = initBudgetPopup;

})();

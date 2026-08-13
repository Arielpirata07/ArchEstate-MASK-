/**
 * phone-suggest.js — Motor compartido de sugerencia y formato de teléfonos multi-país.
 *
 * Fuente de datos: window.__PHONE_DB_BY_COUNTRY (inyectada por los templates desde la
 * tabla `phone_area_codes`), con fallback estático para Argentina.
 * El servidor (Google libphonenumber via validators.validate_phone) es SIEMPRE la
 * fuente de verdad final; este módulo solo ayuda al usuario a escribir un número
 * bien formateado y plausible client-side.
 *
 * API expuesta: window.PhoneSuggest
 */
(function () {
  'use strict';

  function clean(d) {
    return String(d == null ? '' : d).replace(/\D/g, '');
  }

  var AR_PHONE_AREAS = {
    '11':    { city: 'Buenos Aires / CABA', province: 'CABA' },
    '220':   { city: 'San Nicolás', province: 'Buenos Aires' },
    '221':   { city: 'La Plata', province: 'Buenos Aires' },
    '223':   { city: 'Mar del Plata', province: 'Buenos Aires' },
    '236':   { city: 'Junín', province: 'Buenos Aires' },
    '237':   { city: 'Olavarría', province: 'Buenos Aires' },
    '249':   { city: 'Tandil', province: 'Buenos Aires' },
    '2262':  { city: 'Necochea', province: 'Buenos Aires' },
    '261':   { city: 'Mendoza', province: 'Mendoza' },
    '2622':  { city: 'San Rafael', province: 'Mendoza' },
    '264':   { city: 'San Juan', province: 'San Juan' },
    '2652':  { city: 'Tupungato', province: 'Mendoza' },
    '2653':  { city: 'Tunuyán', province: 'Mendoza' },
    '2655':  { city: 'Malargüe', province: 'Mendoza' },
    '2656':  { city: 'La Paz', province: 'Mendoza' },
    '266':   { city: 'San Luis', province: 'San Luis' },
    '280':   { city: 'San Miguel de Tucumán', province: 'Tucumán' },
    '2811':  { city: 'Concepción', province: 'Tucumán' },
    '2814':  { city: 'Monteros', province: 'Tucumán' },
    '291':   { city: 'Bahía Blanca', province: 'Buenos Aires' },
    '294':   { city: 'Santiago del Estero', province: 'Santiago del Estero' },
    '298':   { city: 'San Carlos de Bariloche', province: 'Río Negro' },
    '299':   { city: 'Neuquén', province: 'Neuquén' },
    '341':   { city: 'Rosario', province: 'Santa Fe' },
    '342':   { city: 'Santa Fe', province: 'Santa Fe' },
    '343':   { city: 'Paraná', province: 'Entre Ríos' },
    '345':   { city: 'Concepción del Uruguay', province: 'Entre Ríos' },
    '346':   { city: 'Alisos', province: 'Tucumán' },
    '348':   { city: 'Venado Tuerto', province: 'Santa Fe' },
    '351':   { city: 'Córdoba', province: 'Córdoba' },
    '353':   { city: 'Villa María', province: 'Córdoba' },
    '358':   { city: 'Río Cuarto', province: 'Córdoba' },
    '362':   { city: 'Resistencia', province: 'Chaco' },
    '364':   { city: 'Formosa', province: 'Formosa' },
    '370':   { city: 'Posadas', province: 'Misiones' },
    '375':   { city: 'Goya', province: 'Corrientes' },
    '376':   { city: 'Eldorado', province: 'Misiones' },
    '3757':  { city: 'Puerto Iguazú', province: 'Misiones' },
    '378':   { city: 'Oberá', province: 'Misiones' },
    '379':   { city: 'Corrientes', province: 'Corrientes' },
    '381':   { city: 'Tucumán', province: 'Tucumán' },
    '383':   { city: 'San Fernando del Valle de Catamarca', province: 'Catamarca' },
    '385':   { city: 'La Rioja', province: 'La Rioja' },
    '387':   { city: 'San Salvador de Jujuy', province: 'Jujuy' },
    '388':   { city: 'Salta', province: 'Salta' },
    '3541':  { city: 'Villa Carlos Paz', province: 'Córdoba' },
    '3543':  { city: 'Cosquín', province: 'Córdoba' },
    '3544':  { city: 'Alta Gracia', province: 'Córdoba' },
    '3546':  { city: 'Mina Clavero', province: 'Córdoba' },
    '3547':  { city: 'Cruz del Eje', province: 'Córdoba' },
    '3563':  { city: 'Rafaela', province: 'Santa Fe' },
    '3564':  { city: 'Reconquista', province: 'Santa Fe' },
    '3571':  { city: 'Casilda', province: 'Santa Fe' },
    '3825':  { city: 'Añatuya', province: 'Santiago del Estero' },
    '3832':  { city: 'Fiambalá', province: 'Catamarca' },
    '3833':  { city: 'Andalgalá', province: 'Catamarca' },
    '3844':  { city: 'Chilecito', province: 'La Rioja' },
    '3855':  { city: 'Chacabuco', province: 'Buenos Aires' },
    '3861':  { city: 'Orán', province: 'Salta' },
    '3862':  { city: 'Tartagal', province: 'Salta' },
    '3865':  { city: 'Cafayate', province: 'Salta' },
    '3873':  { city: 'Humahuaca', province: 'Jujuy' },
    '3876':  { city: 'Tilcara', province: 'Jujuy' },
    '2901':  { city: 'Viedma', province: 'Río Negro' },
    '2920':  { city: 'Choele Choel', province: 'Río Negro' },
    '2925':  { city: 'Cipolletti', province: 'Río Negro' },
    '2926':  { city: 'General Roca', province: 'Río Negro' },
    '3751':  { city: 'Curuzú Cuatiá', province: 'Corrientes' },
    '3752':  { city: 'Paso de los Libres', province: 'Corrientes' },
    '3753':  { city: 'Monte Caseros', province: 'Corrientes' },
  };

  function getPhoneAreas(cc) {
    var db = (typeof window !== 'undefined' && window.__PHONE_DB_BY_COUNTRY) || {};
    if (db[cc] && db[cc].length) return db[cc];
    if (cc === '+54' && typeof AR_PHONE_AREAS !== 'undefined') {
      return Object.keys(AR_PHONE_AREAS).map(function (code) {
        return { code: code, city: AR_PHONE_AREAS[code].city, province: AR_PHONE_AREAS[code].province };
      });
    }
    return [];
  }

  function phoneAreaCodes(cc) {
    return getPhoneAreas(cc).map(function (a) { return a.code; })
      .sort(function (a, b) { return b.length - a.length || a.localeCompare(b); });
  }

  function phoneAreaLookup(cc) {
    var out = {};
    getPhoneAreas(cc).forEach(function (a) { out[a.code] = { city: a.city, province: a.province }; });
    return out;
  }

  function detectArea(cc, d) {
    var codes = phoneAreaCodes(cc);
    for (var i = 0; i < codes.length; i++) {
      var a = codes[i];
      if (d.indexOf(a) === 0 && d.length > a.length) return a;
    }
    return null;
  }

  function group(digits, pattern) {
    var out = [], i = 0;
    for (var k = 0; k < pattern.length && i < digits.length; k++) {
      out.push(digits.substr(i, pattern[k]));
      i += pattern[k];
    }
    if (i < digits.length) out.push(digits.substr(i));
    return out.filter(function (s) { return s !== ''; }).join(' ');
  }

  function groupSmart(local) {
    var n = local.length;
    if (n >= 8) return group(local, [4, 4]);
    if (n === 7) return group(local, [3, 4]);
    if (n === 6) return group(local, [3, 3]);
    if (n === 5) return group(local, [2, 3]);
    if (n === 4) return group(local, [2, 2]);
    return local;
  }

  var CONFIG = {
    '+54':  { nsn: [10, 11, 12] },
    '+598': { nsn: [8] },
    '+56':  { nsn: [9] },
    '+55':  { nsn: [10, 11] },
    '+595': { nsn: [8, 9] },
    '+591': { nsn: [8] },
    '+57':  { nsn: [8, 9, 10] },
    '+52':  { nsn: [10] },
    '+34':  { nsn: [9] },
    '+1':   { nsn: [10] }
  };

  function getPhoneCountry(cc) {
    return CONFIG[cc] || null;
  }

  function stripCountryCode(digits, cc) {
    var d = clean(digits);
    var cd = String(cc || '').replace('+', '');
    if (d.indexOf(cd) === 0 && d.length > cd.length) return d.substring(cd.length);
    return d;
  }

  // ============ Sugerencias por país (devuelven string con código de país o null) ============

  function suggestAR(d) {
    if (d.length < 8 || d.length > 12) return null;
    var body = d;
    if (body.indexOf('15') === 0) body = body.substring(2);
    else if (body.indexOf('9') === 0) body = body.substring(1);
    var area = detectArea('+54', body);
    if (!area) {
      for (var len = 4; len >= 2; len--) {
        if (body.length > len && body.length - len >= 6 && body.length - len <= 8) {
          area = body.substring(0, len);
          break;
        }
      }
    }
    if (!area) return null;
    var local = body.substring(area.length);
    if (local.length < 6 || local.length > 8) return null;
    return '+54 9 ' + area + ' ' + groupSmart(local);
  }

  function suggestUY(d) {
    if (d.length !== 8) return null;
    if (d[0] === '9') return '+598 ' + group(d, [2, 3, 3]);
    var area = detectArea('+598', d);
    if (!area) return null;
    return '+598 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestCL(d) {
    if (d.length !== 9) return null;
    if (d[0] === '9') return '+56 9 ' + group(d.substring(1), [4, 4]);
    var area = detectArea('+56', d);
    if (!area) return null;
    return '+56 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestBR(d) {
    if (d.length !== 10 && d.length !== 11) return null;
    var area = detectArea('+55', d);
    if (!area) return null;
    var rest = d.substring(area.length);
    if (rest[0] === '9' && d.length === 11) return '+55 ' + area + ' 9 ' + group(rest.substring(1), [4, 4]);
    return '+55 ' + area + ' ' + groupSmart(rest);
  }

  function suggestPY(d) {
    if (d.length !== 8 && d.length !== 9) return null;
    if (d[0] === '9') {
      if (d.length === 9) return '+595 ' + group(d, [2, 3, 4]);
      return '+595 ' + group(d, [2, 3, 3]);
    }
    var area = detectArea('+595', d);
    if (!area) return null;
    return '+595 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestBO(d) {
    if (d.length !== 8) return null;
    if (d[0] === '6' || d[0] === '7') return '+591 ' + d[0] + ' ' + group(d.substring(1), [3, 4]);
    var area = detectArea('+591', d);
    if (!area) return null;
    return '+591 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestCO(d) {
    if (d.length < 8 || d.length > 10) return null;
    if (d[0] === '3') return '+57 3 ' + group(d.substring(1), [3, 3, 3]);
    var area = detectArea('+57', d);
    if (!area) return null;
    return '+57 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestMX(d) {
    if (d.length !== 10) return null;
    var area = detectArea('+52', d);
    if (!area) return null;
    return '+52 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestES(d) {
    if (d.length !== 9) return null;
    if (d[0] === '6' || d[0] === '7') return '+34 ' + group(d, [3, 3, 3]);
    var area = detectArea('+34', d);
    if (!area) return null;
    return '+34 ' + area + ' ' + groupSmart(d.substring(area.length));
  }

  function suggestUS(d) {
    if (d.length !== 10) return null;
    var area = detectArea('+1', d);
    if (!area) return null;
    return '+1 (' + area + ') ' + d.substring(area.length, area.length + 3) + '-' + d.substring(area.length + 3);
  }

  function suggestNationalNumber(cc, nationalDigits) {
    if (!getPhoneCountry(cc)) return null;
    var d = clean(nationalDigits);
    if (!d) return null;
    switch (cc) {
      case '+54':  return suggestAR(d);
      case '+598': return suggestUY(d);
      case '+56':  return suggestCL(d);
      case '+55':  return suggestBR(d);
      case '+595': return suggestPY(d);
      case '+591': return suggestBO(d);
      case '+57':  return suggestCO(d);
      case '+52':  return suggestMX(d);
      case '+34':  return suggestES(d);
      case '+1':   return suggestUS(d);
      default:     return null;
    }
  }

  // ============ Formato en vivo (con código de país) ============

  function formatNational(cc, nationalDigits) {
    var d = clean(nationalDigits);
    if (!d) return cc;
    var s = suggestNationalNumber(cc, d);
    if (s) return s;
    switch (cc) {
      case '+1': {
        var out = '+1 ';
        if (d.length >= 3) {
          out += '(' + d.substring(0, 3) + ')';
          if (d.length > 3) out += ' ' + d.substring(3, 6);
          if (d.length > 6) out += '-' + d.substring(6);
        } else {
          out += d;
        }
        return out;
      }
      case '+34':
        return '+34 ' + (d.length >= 2 ? d.substring(0, 2) + ' ' : '') +
          (d.length >= 5 ? d.substring(2, 5) + ' ' : '') +
          (d.length >= 7 ? d.substring(5, 7) + ' ' : '') + d.substring(7);
      case '+54': {
        var x = d;
        if (x.indexOf('15') === 0) x = x.substring(2);
        else if (x.indexOf('9') === 0) x = x.substring(1);
        if (x.indexOf('9') !== 0) x = '9' + x;
        var body = x.substring(1);
        var area = detectArea('+54', body);
        if (area) return '+54 9 ' + area + ' ' + groupSmart(body.substring(area.length));
        return '+54 9 ' + groupSmart(body);
      }
      case '+56':
        if (d[0] === '9') return '+56 9 ' + group(d.substring(1), [4, 4]);
        return '+56 ' + groupSmart(d);
      case '+55': {
        var a2 = detectArea('+55', d);
        if (a2) return '+55 ' + a2 + ' ' + (d.substring(a2.length, a2.length + 1) === '9' ? '9 ' : '') + groupSmart(d.substring(a2.length + (d.substring(a2.length, a2.length + 1) === '9' ? 1 : 0)));
        return '+55 ' + groupSmart(d);
      }
      case '+591':
        if (d[0] === '6' || d[0] === '7') return '+591 ' + d[0] + ' ' + group(d.substring(1), [3, 4]);
        return '+591 ' + groupSmart(d);
      case '+57':
        if (d[0] === '3') return '+57 3 ' + group(d.substring(1), [3, 3, 3]);
        return '+57 ' + groupSmart(d);
      default:
        return cc + ' ' + groupSmart(d);
    }
  }

  // ============ Heurística client-side de plausibilidad ============

  function isPlausible(cc, nationalDigits) {
    var cfg = getPhoneCountry(cc);
    if (!cfg) return false;
    var d = clean(nationalDigits);
    return cfg.nsn.indexOf(d.length) !== -1;
  }

  // ============ Label de ciudad/provincia (si el número coincide con un área conocida) ============

  function stripMobilePrefix(cc, d) {
    var body = clean(d);
    if (cc === '+54') {
      if (body.indexOf('15') === 0) body = body.substring(2);
      else if (body.indexOf('9') === 0) body = body.substring(1);
    } else if (cc === '+55') {
      var a2 = body.substring(0, 2);
      if (body.length > 3 && body[2] === '9' && phoneAreaCodes('+55').indexOf(a2) !== -1) {
        body = a2 + body.substring(3);
      }
    } else if (cc === '+598' || cc === '+56' || cc === '+595') {
      if (body[0] === '9') body = body.substring(1);
    } else if (cc === '+591' || cc === '+34') {
      if (body[0] === '6' || body[0] === '7') body = body.substring(1);
    } else if (cc === '+57') {
      if (body[0] === '3') body = body.substring(1);
    }
    return body;
  }

  function getRegionInfo(cc, nationalDigits) {
    var body = stripMobilePrefix(cc, nationalDigits);
    var area = detectArea(cc, body);
    if (!area) return null;
    var lookup = phoneAreaLookup(cc);
    if (!lookup[area]) return null;
    return { code: area, city: lookup[area].city, province: lookup[area].province };
  }

  function getRegionLabel(cc, nationalDigits) {
    var info = getRegionInfo(cc, nationalDigits);
    return info ? { city: info.city, province: info.province } : null;
  }

  // ============ Poblar <select> de códigos de área por país ============

  function populateAreaSelect(select, cc) {
    if (!select || typeof document === 'undefined') return;
    var previous = '';
    for (var i = 0; i < select.options.length; i++) {
      if (select.options[i].selected) { previous = select.options[i].value; break; }
    }
    var keepOther = false;
    for (var i = 0; i < select.options.length; i++) {
      if (select.options[i].value === 'other') { keepOther = true; break; }
    }
    select.innerHTML = '';
    var areas = getPhoneAreas(cc);
    var provinces = {};
    areas.forEach(function (c) {
      if (!provinces[c.province]) provinces[c.province] = [];
      provinces[c.province].push({ code: c.code, city: c.city });
    });
    var ordered = Object.keys(provinces).sort();
    ordered.forEach(function (prov) {
      provinces[prov].forEach(function (item) {
        var opt = document.createElement('option');
        opt.value = item.code;
        opt.textContent = item.city;
        opt.setAttribute('data-state', prov);
        select.appendChild(opt);
      });
    });
    if (keepOther) {
      var otherOpt = document.createElement('option');
      otherOpt.value = 'other';
      otherOpt.textContent = 'Otra...';
      select.appendChild(otherOpt);
    }
    if (previous) {
      var found = false;
      for (var j = 0; j < select.options.length; j++) {
        if (select.options[j].value === previous) { select.options[j].selected = true; found = true; break; }
      }
      if (!found) {
        for (var k = 0; k < select.options.length; k++) {
          if (select.options[k].value === 'other') { select.options[k].selected = true; break; }
        }
      }
    }
    if (select._allOptions) delete select._allOptions;
  }

  // ============ Export ============

  window.PhoneSuggest = {
    getPhoneCountry: getPhoneCountry,
    stripCountryCode: stripCountryCode,
    getPhoneAreas: getPhoneAreas,
    phoneAreaCodes: phoneAreaCodes,
    phoneAreaLookup: phoneAreaLookup,
    detectArea: detectArea,
    suggestNationalNumber: suggestNationalNumber,
    formatNational: formatNational,
    isPlausible: isPlausible,
    getRegionLabel: getRegionLabel,
    getRegionInfo: getRegionInfo,
    populateAreaSelect: populateAreaSelect
  };
  if (typeof globalThis !== 'undefined' && globalThis && globalThis !== window) {
    globalThis.PhoneSuggest = window.PhoneSuggest;
  }
})();

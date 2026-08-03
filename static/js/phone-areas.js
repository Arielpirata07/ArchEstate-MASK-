/**
 * Mapeo de códigos de área telefónicos argentinos a ciudades.
 * Fuente única de verdad para selects de provincia, sugerencias
 * de formato y feedback de ciudad en validación de teléfono.
 *
 * Solo ciudades principales (~60). Códigos de 2-4 dígitos.
 */
const AR_PHONE_AREAS = {
  '11':    { city: 'Buenos Aires / CABA', province: 'CABA' },
  '220':   { city: 'San Nicolás', province: 'Buenos Aires' },
  '221':   { city: 'La Plata', province: 'Buenos Aires' },
  '223':   { city: 'Mar del Plata', province: 'Buenos Aires' },
  '236':   { city: 'Junín', province: 'Buenos Aires' },
  '237':   { city: 'Olavarría', province: 'Buenos Aires' },
  '239':   { city: 'Tandil', province: 'Buenos Aires' },
  '249':   { city: 'Necochea', province: 'Buenos Aires' },
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
  '346':   { city: 'San Luis', province: 'San Luis' },
  '348':   { city: 'Venado Tuerto', province: 'Santa Fe' },
  '351':   { city: 'Córdoba', province: 'Córdoba' },
  '353':   { city: 'Villa María', province: 'Córdoba' },
  '358':   { city: 'Río Cuarto', province: 'Córdoba' },
  '362':   { city: 'Resistencia', province: 'Chaco' },
  '364':   { city: 'Formosa', province: 'Formosa' },
  '370':   { city: 'Posadas', province: 'Misiones' },
  '375':   { city: 'Goya', province: 'Corrientes' },
  '376':   { city: 'Eldorado', province: 'Misiones' },
  '377':   { city: 'Puerto Iguazú', province: 'Misiones' },
  '378':   { city: 'Oberá', province: 'Misiones' },
  '379':   { city: 'Corrientes', province: 'Corrientes' },
  '381':   { city: 'Santiago del Estero', province: 'Santiago del Estero' },
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

/**
 * Array de códigos de área ordenados de mayor a menor longitud
 * (para matching greedy: 4 dígitos antes que 3, 3 antes que 2).
 */
const AR_PHONE_PREFIXES = Object.keys(AR_PHONE_AREAS)
  .sort((a, b) => b.length - a.length || a.localeCompare(b));

/**
 * Lookup rápido: devuelve { city, province } o null.
 */
function getArPhoneArea(areaCode) {
  return AR_PHONE_AREAS[areaCode] || null;
}

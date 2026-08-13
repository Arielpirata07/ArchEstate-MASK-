"""
Logica de matching entre leads y profesionales, compartida entre:
- services/assignment.py (asignacion automatica de un lead a un profesional)
- routes/professional_bp.py (badge de "coincide conmigo" en el listado)

Se basa en la cobertura configurada por el profesional (models.get_professional_coverage),
que soporta multiples zonas y especialidades, con fallback a los campos legacy
de un solo valor en la tabla professionals si el profesional no configuro nada.
"""

SPECIALTY_WEIGHT_EXACT = 100
SPECIALTY_WEIGHT_PARTIAL = 50
ZONE_WEIGHT = 30
PROVINCE_WEIGHT = 20

# Un lead solo se considera "match" si supera este piso — evita asignar
# o marcar como coincidencia un lead que no tiene ninguna relacion real
# con la cobertura del profesional.
MIN_MATCH_SCORE = 1


def score_lead_for_coverage(lead, coverage, pro_province=''):
    """
    Calcula el score de afinidad entre un lead y la cobertura de un profesional.

    lead: dict-like con 'property_type', 'zone', 'province'
    coverage: dict con 'zones' y 'specialties' (listas), ver models.get_professional_coverage
    pro_province: provincia del perfil del profesional (valor unico, legacy)

    Devuelve un score >= 0. Un score >= MIN_MATCH_SCORE se considera match real.
    """
    lead_property_type = (lead.get('property_type') or '').strip().lower()
    lead_zone = (lead.get('zone') or '').strip().lower()
    lead_province = (lead.get('province') or '').strip().lower()

    score = 0

    specialties = [s.strip().lower() for s in coverage.get('specialties', []) if s]
    if lead_property_type and specialties:
        if lead_property_type in specialties:
            score += SPECIALTY_WEIGHT_EXACT
        elif any(sp in lead_property_type or lead_property_type in sp for sp in specialties):
            score += SPECIALTY_WEIGHT_PARTIAL

    zones = [z.strip().lower() for z in coverage.get('zones', []) if z]
    if lead_zone and zones:
        if any(z == lead_zone or z in lead_zone or lead_zone in z for z in zones):
            score += ZONE_WEIGHT

    pro_province = (pro_province or '').strip().lower()
    if pro_province and lead_province and pro_province == lead_province:
        score += PROVINCE_WEIGHT

    return score


def lead_matches_coverage(lead, coverage, pro_province=''):
    """True si el lead tiene una relacion real con la cobertura del profesional
    (no solo "coincide de casualidad porque nadie configuro nada")."""
    return score_lead_for_coverage(lead, coverage, pro_province) >= MIN_MATCH_SCORE

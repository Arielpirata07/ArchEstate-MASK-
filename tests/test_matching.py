from services.matching import (
    MIN_MATCH_SCORE,
    PROVINCE_WEIGHT,
    SPECIALTY_WEIGHT_EXACT,
    SPECIALTY_WEIGHT_PARTIAL,
    ZONE_WEIGHT,
    lead_matches_coverage,
    score_lead_for_coverage,
)


def _lead(**kw):
    base = {'property_type': 'departamento', 'zone': 'Palermo', 'province': 'Buenos Aires'}
    base.update(kw)
    return base


class TestScoreLeadForCoverage:
    def test_exact_specialty(self):
        cov = {'zones': [], 'specialties': ['departamento']}
        assert score_lead_for_coverage(_lead(), cov) == SPECIALTY_WEIGHT_EXACT

    def test_partial_specialty(self):
        cov = {'zones': [], 'specialties': ['departa']}
        assert score_lead_for_coverage(_lead(), cov) == SPECIALTY_WEIGHT_PARTIAL

    def test_zone_match(self):
        cov = {'zones': ['Palermo'], 'specialties': []}
        assert score_lead_for_coverage(_lead(), cov) == ZONE_WEIGHT

    def test_zone_partial_match(self):
        cov = {'zones': ['Paler'], 'specialties': []}
        assert score_lead_for_coverage(_lead(), cov) == ZONE_WEIGHT

    def test_province_match(self):
        cov = {'zones': [], 'specialties': []}
        assert score_lead_for_coverage(_lead(), cov, 'Buenos Aires') == PROVINCE_WEIGHT

    def test_no_match_scores_zero(self):
        cov = {'zones': ['Recoleta'], 'specialties': ['casa']}
        assert score_lead_for_coverage(_lead(), cov, 'Córdoba') == 0

    def test_combined_scores_add_up(self):
        cov = {'zones': ['Palermo'], 'specialties': ['departamento']}
        total = SPECIALTY_WEIGHT_EXACT + ZONE_WEIGHT + PROVINCE_WEIGHT
        assert score_lead_for_coverage(_lead(), cov, 'Buenos Aires') == total

    def test_case_insensitive(self):
        cov = {'zones': ['PALERMO'], 'specialties': ['DEPARTAMENTO']}
        assert score_lead_for_coverage(_lead(), cov, 'BUENOS AIRES') > 0

    def test_empty_lead_fields(self):
        cov = {'zones': ['Palermo'], 'specialties': ['departamento']}
        assert score_lead_for_coverage({}, cov) == 0


class TestLeadMatchesCoverage:
    def test_match_above_threshold(self):
        assert lead_matches_coverage(_lead(), {'zones': ['Palermo'], 'specialties': []}) is True

    def test_no_match_below_threshold(self):
        assert lead_matches_coverage(_lead(), {'zones': [], 'specialties': []}) is False
        assert MIN_MATCH_SCORE == 1

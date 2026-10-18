"""Fase 0 SLA — tests del helper de primer contacto y del calculo de horas habiles."""
import uuid
from datetime import datetime, timedelta

import pytest

from services.sla import (
    SLA_SOURCES,
    SLA_RANK,
    business_hours_between,
    classify_sla_status,
    compute_sla_kpis,
    get_response_commitment,
    get_professional_reminders,
    record_first_contact,
    _commitment_from,
    _parse_ts,
)


class TestBusinessHoursBetween:
    def test_same_instant_returns_zero(self):
        dt = datetime(2026, 1, 5, 10, 0)
        assert business_hours_between(dt, dt) == 0.0

    def test_end_before_start_returns_zero(self):
        a = datetime(2026, 1, 5, 15, 0)
        b = datetime(2026, 1, 5, 10, 0)
        assert business_hours_between(a, b) == 0.0

    def test_within_same_business_window(self):
        a = datetime(2026, 1, 5, 10, 0)  # lunes 10:00
        b = datetime(2026, 1, 5, 12, 0)  # lunes 12:00
        assert business_hours_between(a, b) == 2.0

    def test_overnight_counts_only_business_hours(self):
        # Lunes 17:00 → martes 10:00 = 1h (lun) + 1h (mar) = 2h
        a = datetime(2026, 1, 5, 17, 0)
        b = datetime(2026, 1, 6, 10, 0)
        assert business_hours_between(a, b) == 2.0

    def test_weekend_is_free(self):
        # Viernes 17:00 → lunes 10:00 = 1h (vie) + 1h (lun) = 2h
        a = datetime(2026, 1, 9, 17, 0)  # viernes
        b = datetime(2026, 1, 12, 10, 0)  # lunes
        assert business_hours_between(a, b) == 2.0

    def test_full_business_day_capped_at_9h(self):
        # Lunes 00:00 → lunes 23:59 = 9h (09:00–18:00)
        a = datetime(2026, 1, 5, 0, 0)
        b = datetime(2026, 1, 5, 23, 59)
        assert business_hours_between(a, b) == 9.0

    def test_none_inputs_return_zero(self):
        assert business_hours_between(None, datetime.now()) == 0.0
        assert business_hours_between(datetime.now(), None) == 0.0

    def test_two_full_business_days(self):
        # Lunes 09:00 → Miércoles 09:00 = lun(9) + mar(9) = 18h
        a = datetime(2026, 1, 5, 9, 0)
        b = datetime(2026, 1, 7, 9, 0)
        assert business_hours_between(a, b) == 18.0


class TestClassifySlaStatus:
    '''Estado SLA para ordenar en sort=match (Fase 3).'''

    def test_contacted_wins(self):
        old = datetime(2026, 1, 5, 9, 0)
        assert classify_sla_status(old, True) == 'contacted'

    def test_fresh_is_pending(self):
        created = datetime(2026, 1, 5, 9, 0)   # lunes 09:00
        now = datetime(2026, 1, 5, 12, 0)      # 3h hábiles
        assert classify_sla_status(created, False, now=now) == 'pending'

    def test_second_half_is_at_risk(self):
        created = datetime(2026, 1, 5, 9, 0)   # lunes 09:00
        now = datetime(2026, 1, 6, 13, 0)      # martes: 9 + 4 = 13h
        assert classify_sla_status(created, False, now=now) == 'at_risk'

    def test_over_threshold_is_breached(self):
        created = datetime(2026, 1, 5, 9, 0)   # lunes 09:00
        now = datetime(2026, 1, 8, 10, 0)      # jueves: 9*3 + 1 = 28h
        assert classify_sla_status(created, False, now=now) == 'breached'

    def test_none_created_is_pending(self):
        assert classify_sla_status(None, False, now=datetime(2026, 1, 5, 12, 0)) == 'pending'

    def test_rank_orders_by_urgency(self):
        assert SLA_RANK['breached'] > SLA_RANK['at_risk'] > SLA_RANK['pending'] > SLA_RANK['contacted']


class TestProfessionalReminders:
    '''Recordatorio suave: leads asignados sin responder, en riesgo o vencidos.'''

    def _mk_lead(self, db, ts, assigned_to=None):
        cur = db.execute(
            'INSERT INTO leads (type, zone, budget, phone, email, timestamp, assigned_to) '
            "VALUES ('compra', 'CABA', '100000', '+5491100000000', 'rem@a.com', ?, ?)",
            (ts, assigned_to)
        )
        db.commit()
        return cur.lastrowid

    def _user(self, db):
        unique = uuid.uuid4().hex[:8]
        cur = db.execute(
            "INSERT INTO users (username, email, hash, role, phone, is_active) "
            "VALUES (?, ?, 'x', 'professional', '+5491100000000', 1)",
            (f'rem_{unique}', f'rem_{unique}@test.com')
        )
        db.commit()
        return cur.lastrowid

    def _contact(self, db, lead_id, pro_id, elapsed):
        db.execute(
            'INSERT INTO lead_first_contact (lead_id, professional_id, contact_at, source, business_hours_elapsed) '
            "VALUES (?, ?, datetime('now'), 'stage', ?)",
            (lead_id, pro_id, elapsed)
        )
        db.commit()

    def test_no_assigned_leads_is_empty(self, db):
        pro = self._user(db)
        assert get_professional_reminders(db, pro) == {'total': 0, 'at_risk': 0, 'breached': 0}

    def test_fresh_assigned_not_counted(self, db):
        pro = self._user(db)
        self._mk_lead(db, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), assigned_to=pro)
        assert get_professional_reminders(db, pro)['total'] == 0

    def test_breached_assigned_counted(self, db):
        pro = self._user(db)
        old = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        self._mk_lead(db, old, assigned_to=pro)
        r = get_professional_reminders(db, pro)
        assert r['breached'] == 1
        assert r['at_risk'] == 0
        assert r['total'] == 1

    def test_at_risk_counted(self, db):
        pro = self._user(db)
        created = datetime(2026, 1, 5, 9, 0)    # lunes 09:00
        now = datetime(2026, 1, 6, 13, 0)       # martes: 9 + 4 = 13h hábiles
        self._mk_lead(db, created.strftime('%Y-%m-%d %H:%M:%S'), assigned_to=pro)
        r = get_professional_reminders(db, pro, now=now)
        assert r['at_risk'] == 1
        assert r['breached'] == 0
        assert r['total'] == 1

    def test_contacted_not_counted(self, db):
        pro = self._user(db)
        old = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        lid = self._mk_lead(db, old, assigned_to=pro)
        self._contact(db, lid, pro, 30.0)
        assert get_professional_reminders(db, pro)['total'] == 0

    def test_own_tracking_contacted_not_counted(self, db):
        pro = self._user(db)
        old = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        lid = self._mk_lead(db, old, assigned_to=pro)
        db.execute(
            'INSERT INTO lead_tracking (lead_id, professional_id, contacted) VALUES (?, ?, 1)',
            (lid, pro)
        )
        db.commit()
        assert get_professional_reminders(db, pro)['total'] == 0

    def test_other_professional_leads_ignored(self, db):
        pro = self._user(db)
        other = self._user(db)
        old = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        self._mk_lead(db, old, assigned_to=other)
        assert get_professional_reminders(db, pro)['total'] == 0


class TestParseTs:
    def test_parses_datetime_string(self):
        assert _parse_ts('2026-01-05 10:00:00') == datetime(2026, 1, 5, 10, 0)
    def test_parses_date_only(self):
        assert _parse_ts('2026-01-05') == datetime(2026, 1, 5, 0, 0)

    def test_returns_none_for_invalid(self):
        assert _parse_ts('not-a-date') is None
        assert _parse_ts('') is None
        assert _parse_ts(None) is None


class TestRecordFirstContact:
    def _mk_lead(self, db, ts='2026-01-05 09:00:00'):
        cur = db.execute(
            'INSERT INTO leads (type, zone, budget, phone, email, timestamp) '
            "VALUES ('compra', 'CABA', '100000', '+5491100000000', 'a@a.com', ?)",
            (ts,)
        )
        db.commit()
        return cur.lastrowid

    def test_records_first_signal(self, db):
        lead_id = self._mk_lead(db)
        ok = record_first_contact(lead_id, 1, 'stage',
                                  when=datetime(2026, 1, 5, 10, 0))
        assert ok is True
        row = db.execute('SELECT * FROM lead_first_contact WHERE lead_id = ?', (lead_id,)).fetchone()
        assert row is not None
        assert row['source'] == 'stage'
        assert row['professional_id'] == 1

    def test_idempotent_second_signal_ignored(self, db):
        lead_id = self._mk_lead(db)
        record_first_contact(lead_id, 1, 'stage', when=datetime(2026, 1, 5, 10, 0))
        second = record_first_contact(lead_id, 2, 'reveal', when=datetime(2026, 1, 5, 11, 0))
        assert second is False
        row = db.execute('SELECT * FROM lead_first_contact WHERE lead_id = ?', (lead_id,)).fetchone()
        assert row['source'] == 'stage'
        assert row['professional_id'] == 1

    def test_unknown_source_rejected(self, db):
        lead_id = self._mk_lead(db)
        assert record_first_contact(lead_id, 1, 'bogus') is False
        row = db.execute('SELECT * FROM lead_first_contact WHERE lead_id = ?', (lead_id,)).fetchone()
        assert row is None

    def test_missing_lead_returns_false(self, db):
        assert record_first_contact(999999, 1, 'stage') is False

    def test_elapsed_business_hours_computed(self, db):
        # Lead lun 09:00, contacto lun 12:00 → 3h habiles
        lead_id = self._mk_lead(db, ts='2026-01-05 09:00:00')
        record_first_contact(lead_id, 1, 'stage', when=datetime(2026, 1, 5, 12, 0))
        row = db.execute('SELECT business_hours_elapsed FROM lead_first_contact WHERE lead_id = ?', (lead_id,)).fetchone()
        assert row['business_hours_elapsed'] == pytest.approx(3.0)

    def test_all_sources_accepted(self, db):
        for src in SLA_SOURCES:
            lead_id = self._mk_lead(db)
            assert record_first_contact(lead_id, 1, src) is True


class TestComputeSlaKpis:
    '''Separacion pending / breached / unassigned del KPI (Fase 1).'''

    def _now(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _mk_lead(self, db, ts, assigned_to=None):
        cur = db.execute(
            'INSERT INTO leads (type, zone, budget, phone, email, timestamp, assigned_to) '
            "VALUES ('compra', 'CABA', '100000', '+5491100000000', 'kpi@a.com', ?, ?)",
            (ts, assigned_to)
        )
        db.commit()
        return cur.lastrowid

    def _user(self, db, active=1):
        unique = uuid.uuid4().hex[:8]
        cur = db.execute(
            "INSERT INTO users (username, email, hash, role, phone, is_active) "
            "VALUES (?, ?, 'x', 'professional', '+5491100000000', ?)",
            (f'kpi_{unique}', f'kpi_{unique}@test.com', active)
        )
        db.commit()
        return cur.lastrowid

    def _contact(self, db, lead_id, pro_id, elapsed):
        db.execute(
            'INSERT INTO lead_first_contact (lead_id, professional_id, contact_at, source, business_hours_elapsed) '
            "VALUES (?, ?, datetime('now'), 'stage', ?)",
            (lead_id, pro_id, elapsed)
        )
        db.commit()

    def test_unassigned_counted_separately(self, db):
        base = compute_sla_kpis(db, days=30)
        self._mk_lead(db, self._now(), assigned_to=None)
        after = compute_sla_kpis(db, days=30)
        assert after['unassigned'] == base['unassigned'] + 1
        assert after['pending'] == base['pending']

    def test_assigned_recent_is_pending(self, db):
        base = compute_sla_kpis(db, days=30)
        self._mk_lead(db, self._now(), assigned_to=self._user(db))
        after = compute_sla_kpis(db, days=30)
        assert after['pending'] == base['pending'] + 1
        assert after['unassigned'] == base['unassigned']

    def test_assigned_old_without_contact_is_breached(self, db):
        base = compute_sla_kpis(db, days=30)
        past = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        self._mk_lead(db, past, assigned_to=self._user(db))
        after = compute_sla_kpis(db, days=30)
        assert after['breached'] == base['breached'] + 1
        assert after['pending'] == base['pending']

    def test_contacted_within_threshold_is_met(self, db):
        base = compute_sla_kpis(db, days=30)
        lid = self._mk_lead(db, self._now())
        self._contact(db, lid, self._user(db), 3.0)
        after = compute_sla_kpis(db, days=30)
        assert after['met'] == base['met'] + 1
        assert after['breached'] == base['breached']

    def test_contacted_late_is_breached(self, db):
        base = compute_sla_kpis(db, days=30)
        lid = self._mk_lead(db, self._now())
        self._contact(db, lid, self._user(db), 30.0)
        after = compute_sla_kpis(db, days=30)
        assert after['breached'] == base['breached'] + 1

    def test_inactive_professional_lead_is_unassigned(self, db):
        base = compute_sla_kpis(db, days=30)
        self._mk_lead(db, self._now(), assigned_to=self._user(db, active=0))
        after = compute_sla_kpis(db, days=30)
        assert after['unassigned'] == base['unassigned'] + 1
        assert after['pending'] == base['pending']

    def test_all_time_baseline_window(self, db):
        '''days=None → línea base (todo el histórico backfilleado).'''
        base = compute_sla_kpis(db, days=30)
        all_time = compute_sla_kpis(db, days=None)
        assert all_time['days'] is None
        assert set(all_time.keys()) == set(base.keys())
        assert all_time['total_leads'] >= base['total_leads']
        assert all_time['contacted'] >= base['contacted']
        assert all_time['unassigned'] >= base['unassigned']

    def test_old_lead_only_in_baseline(self, db):
        '''Un lead fuera de la ventana de 30d aparece solo en la línea base.'''
        base30 = compute_sla_kpis(db, days=30)
        base_all = compute_sla_kpis(db, days=None)
        old = (datetime.now() - timedelta(days=400)).strftime('%Y-%m-%d %H:%M:%S')
        self._mk_lead(db, old, assigned_to=self._user(db))
        after30 = compute_sla_kpis(db, days=30)
        after_all = compute_sla_kpis(db, days=None)
        assert after30['total_leads'] == base30['total_leads']
        assert after_all['total_leads'] == base_all['total_leads'] + 1


class TestGetResponseCommitment:
    '''Compromiso de respuesta que se le comunica al cliente (Fase 3).'''

    def test_empty_sample_not_available(self):
        c = _commitment_from([])
        assert c['available'] is False
        assert c['hours'] == 0
        assert c['sample'] == 0

    def test_below_min_sample_not_available(self):
        c = _commitment_from([3.0, 3.0, 3.0, 3.0], min_sample=5)
        assert c['available'] is False

    def test_available_with_enough_low_sample(self):
        c = _commitment_from([6.0] * 5)
        assert c['available'] is True
        assert c['hours'] == 6
        assert c['sample'] == 5

    def test_median_rounded(self):
        c = _commitment_from([2.0, 3.0, 4.0, 5.0, 6.0])
        assert c['available'] is True
        assert c['hours'] == 4

    def test_too_slow_not_available(self):
        c = _commitment_from([60.0] * 10, max_display=48)
        assert c['available'] is False
        assert c['hours'] == 0

    def test_zero_median_not_available(self):
        c = _commitment_from([0.0] * 10)
        assert c['available'] is False

    def test_get_response_commitment_shape(self, db):
        c = get_response_commitment(db)
        assert set(c.keys()) == {'available', 'hours', 'sample'}
        assert isinstance(c['available'], bool)
        assert isinstance(c['hours'], int)
        assert isinstance(c['sample'], int)

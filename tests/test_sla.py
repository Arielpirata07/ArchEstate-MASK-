"""Fase 0 SLA — tests del helper de primer contacto y del calculo de horas habiles."""
from datetime import datetime

import pytest

from services.sla import (
    SLA_SOURCES,
    business_hours_between,
    record_first_contact,
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

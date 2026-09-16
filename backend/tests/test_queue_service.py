from datetime import datetime, timedelta, timezone

from app.models import Ticket
from app.services.queue_service import order_queue

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def ticket(number, priority, deadline_offset, age_offset=0, status="OPEN", ticket_id=1):
    created = NOW - timedelta(hours=age_offset)
    return Ticket(id=ticket_id, ticket_number=number, priority=priority, status=status, created_at=created, sla_deadline=NOW + timedelta(hours=deadline_offset))


def test_overdue_normal_beats_non_overdue_urgent():
    result = order_queue([ticket("urgent", "URGENT", 1), ticket("normal", "NORMAL", -1)], NOW)
    assert [item.ticket_number for item in result] == ["normal", "urgent"]


def test_overdue_urgent_beats_non_overdue_urgent():
    result = order_queue([ticket("later", "URGENT", 1), ticket("breached", "URGENT", -1)], NOW)
    assert result[0].ticket_number == "breached"


def test_closer_deadline_wins_same_priority():
    result = order_queue([ticket("later", "URGENT", 2), ticket("soon", "URGENT", 1)], NOW)
    assert result[0].ticket_number == "soon"


def test_older_wins_tied_deadline():
    result = order_queue([ticket("new", "NORMAL", 2, age_offset=1), ticket("old", "NORMAL", 2, age_offset=4)], NOW)
    assert result[0].ticket_number == "old"


def test_resolved_is_excluded():
    result = order_queue([ticket("resolved", "URGENT", -4, status="RESOLVED"), ticket("active", "NORMAL", 2)], NOW)
    assert [item.ticket_number for item in result] == ["active"]


def test_exact_deadline_is_overdue():
    result = order_queue([ticket("due", "NORMAL", 0), ticket("later", "NORMAL", 1)], NOW)
    assert result[0].ticket_number == "due"

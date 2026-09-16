from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Customer, Ticket, TicketActivity, TicketStatus
from app.services.escalation_service import escalate_breached_tickets

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    customer = Customer(name="Test Customer", email="test@example.com", created_at=NOW)
    session.add(customer)
    session.flush()
    session.add_all([
        Ticket(ticket_number="HD-1", title="Normal", description="Needs help", priority="NORMAL", status="OPEN", customer_id=customer.id, created_at=NOW - timedelta(hours=25), updated_at=NOW, sla_deadline=NOW - timedelta(hours=1)),
        Ticket(ticket_number="HD-2", title="Urgent", description="Needs help", priority="URGENT", status="OPEN", customer_id=customer.id, created_at=NOW - timedelta(hours=3), updated_at=NOW, sla_deadline=NOW - timedelta(hours=1)),
        Ticket(ticket_number="HD-3", title="Resolved", description="Done", priority="NORMAL", status=TicketStatus.RESOLVED, customer_id=customer.id, created_at=NOW - timedelta(hours=25), updated_at=NOW, sla_deadline=NOW - timedelta(hours=1)),
    ])
    session.commit()
    return session


def test_breached_normal_escalates_one_level_and_logs_activity():
    session = make_session()
    ticket = session.scalar(select(Ticket).where(Ticket.ticket_number == "HD-1"))
    deadline = ticket.sla_deadline

    escalated = escalate_breached_tickets(session, NOW)

    session.refresh(ticket)
    assert [item.ticket_number for item in escalated] == ["HD-1"]
    assert ticket.priority == "HIGH"
    assert ticket.sla_deadline == deadline
    activity = session.scalar(select(TicketActivity).where(TicketActivity.ticket_id == ticket.id))
    assert (activity.action, activity.old_value, activity.new_value) == ("SLA_ESCALATED", "NORMAL", "HIGH")


def test_second_run_advances_high_to_urgent_and_urgent_stays_urgent():
    session = make_session()
    escalate_breached_tickets(session, NOW)
    escalated = escalate_breached_tickets(session, NOW)

    assert [item.ticket_number for item in escalated] == ["HD-1"]
    assert session.scalar(select(Ticket).where(Ticket.ticket_number == "HD-1")).priority == "URGENT"
    assert session.scalar(select(Ticket).where(Ticket.ticket_number == "HD-2")).priority == "URGENT"


def test_resolved_ticket_is_never_escalated():
    session = make_session()
    escalate_breached_tickets(session, NOW)

    ticket = session.scalar(select(Ticket).where(Ticket.ticket_number == "HD-3"))
    assert ticket.priority == "NORMAL"
    assert session.scalar(select(TicketActivity).where(TicketActivity.ticket_id == ticket.id)) is None

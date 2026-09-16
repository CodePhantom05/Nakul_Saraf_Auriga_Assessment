from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Priority, Ticket, TicketActivity, TicketStatus
from .sla_service import is_overdue, utc_now

ESCALATION_PATH = {
    Priority.NORMAL: Priority.HIGH,
    Priority.HIGH: Priority.URGENT,
}


def escalate_breached_tickets(
    db: Session, now: datetime | None = None, actor: str = "SLA monitor"
) -> list[Ticket]:
    """Advance each breached active ticket by one priority level per run."""
    checked_at = now or utc_now()
    tickets = db.scalars(
        select(Ticket).where(Ticket.status != TicketStatus.RESOLVED)
    ).all()
    escalated: list[Ticket] = []
    for ticket in tickets:
        next_priority = ESCALATION_PATH.get(Priority(ticket.priority))
        if next_priority is None or not is_overdue(ticket, checked_at):
            continue
        old_priority = ticket.priority
        ticket.priority = next_priority
        ticket.updated_at = checked_at
        db.add(
            TicketActivity(
                ticket_id=ticket.id,
                action="SLA_ESCALATED",
                old_value=old_priority,
                new_value=next_priority,
                performed_by=actor,
                created_at=checked_at,
            )
        )
        escalated.append(ticket)
    if escalated:
        db.commit()
    return escalated
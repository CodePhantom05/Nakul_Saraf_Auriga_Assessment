from datetime import datetime

from ..models import Ticket, TicketStatus
from .sla_service import is_overdue


def queue_key(ticket: Ticket, now: datetime) -> tuple[int, int, float, float, int]:
    """Order active work by breach state, priority, deadline, age, then id."""
    overdue_rank = 0 if is_overdue(ticket, now) else 1
    priority_rank = {"URGENT": 0, "HIGH": 1, "NORMAL": 2}.get(ticket.priority, 3)
    return (
        overdue_rank,
        priority_rank,
        ticket.sla_deadline.timestamp(),
        ticket.created_at.timestamp(),
        ticket.id,
    )


def order_queue(tickets: list[Ticket], now: datetime, include_resolved: bool = False) -> list[Ticket]:
    selected = tickets if include_resolved else [ticket for ticket in tickets if ticket.status != TicketStatus.RESOLVED]
    return sorted(selected, key=lambda ticket: queue_key(ticket, now))


def explain_ticket(ticket: Ticket, ordered: list[Ticket], now: datetime) -> list[str]:
    reasons: list[str] = []
    if is_overdue(ticket, now):
        reasons.append("SLA breached")
    if ticket.priority == "URGENT":
        reasons.append("URGENT priority")
    comparable = [other for other in ordered if other.priority == ticket.priority and is_overdue(other, now) == is_overdue(ticket, now)]
    if comparable and ticket.sla_deadline == min(item.sla_deadline for item in comparable):
        reasons.append("Closest deadline")
    if comparable and ticket.created_at == min(item.created_at for item in comparable if item.sla_deadline == ticket.sla_deadline):
        reasons.append("Waiting longer than other comparable tickets")
    return reasons

from datetime import datetime, timedelta, timezone

from ..models import Priority, Ticket

SLA_HOURS = {Priority.URGENT: 2, Priority.HIGH: 8, Priority.NORMAL: 24}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def calculate_deadline(created_at: datetime, priority: str) -> datetime:
    return created_at + timedelta(hours=SLA_HOURS[Priority(priority)])


def is_overdue(ticket: Ticket, now: datetime | None = None) -> bool:
    if ticket.status == "RESOLVED":
        return False
    return (now or utc_now()) >= as_utc(ticket.sla_deadline)

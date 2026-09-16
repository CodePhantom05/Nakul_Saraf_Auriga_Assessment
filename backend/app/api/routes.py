import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Agent, Customer, Priority, Ticket, TicketActivity, TicketStatus
from ..schemas import ActivityOut, AgentOut, CustomerCreate, CustomerOut, TicketCreate, TicketOut, TicketUpdate
from ..services.queue_service import explain_ticket, order_queue
from ..services.escalation_service import escalate_breached_tickets
from ..services.sla_service import calculate_deadline, is_overdue, utc_now

router = APIRouter(prefix="/api")


def ticket_out(ticket: Ticket, now: datetime | None = None) -> TicketOut:
    return TicketOut(
        id=ticket.id, ticket_number=ticket.ticket_number, title=ticket.title,
        description=ticket.description, priority=ticket.priority, status=ticket.status,
        customer_id=ticket.customer_id, customer_name=ticket.customer.name,
        assigned_to_id=ticket.assigned_to_id, assignee_name=ticket.assignee.name if ticket.assignee else None,
        created_at=ticket.created_at, updated_at=ticket.updated_at,
        sla_deadline=ticket.sla_deadline, resolved_at=ticket.resolved_at,
        overdue=is_overdue(ticket, now),
    )


def load_tickets(db: Session, search: str | None, priority: str | None, status: str | None, assigned_to: int | None, unassigned: bool) -> list[Ticket]:
    query = select(Ticket).options(joinedload(Ticket.customer), joinedload(Ticket.assignee))
    if search:
        term = f"%{search}%"
        query = query.join(Customer).where(or_(Customer.name.ilike(term), Ticket.title.ilike(term), Ticket.ticket_number.ilike(term)))
    if priority:
        query = query.where(Ticket.priority == priority)
    if status:
        query = query.where(Ticket.status == status)
    if assigned_to is not None:
        query = query.where(Ticket.assigned_to_id == assigned_to)
    if unassigned:
        query = query.where(Ticket.assigned_to_id.is_(None))
    return list(db.scalars(query).unique().all())


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/agents", response_model=list[AgentOut])
def agents(db: Session = Depends(get_db)) -> list[Agent]:
    return list(db.scalars(select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.name)).all())


@router.get("/customers", response_model=list[CustomerOut])
def customers(q: str | None = None, db: Session = Depends(get_db)) -> list[Customer]:
    query = select(Customer).order_by(Customer.name)
    if q:
        query = query.where(Customer.name.ilike(f"%{q}%"))
    return list(db.scalars(query).all())


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    if db.scalar(select(Customer).where(Customer.email == payload.email)):
        raise HTTPException(409, "A customer with this email already exists")
    customer = Customer(**payload.model_dump(), created_at=utc_now())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers/{customer_id}")
def customer_detail(customer_id: int, db: Session = Depends(get_db)) -> dict:
    customer = db.scalar(select(Customer).options(joinedload(Customer.tickets)).where(Customer.id == customer_id))
    if not customer:
        raise HTTPException(404, "Customer not found")
    now = utc_now()
    history = [ticket_out(ticket, now) for ticket in sorted(customer.tickets, key=lambda item: item.created_at, reverse=True)]
    return {"customer": CustomerOut.model_validate(customer), "active_count": sum(item.status != TicketStatus.RESOLVED for item in customer.tickets), "resolved_count": sum(item.status == TicketStatus.RESOLVED for item in customer.tickets), "tickets": history}


@router.get("/tickets")
def list_tickets(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = None, priority: str | None = None, status: str | None = None, assigned_to: int | None = None, unassigned: bool = False, db: Session = Depends(get_db)) -> dict:
    now = utc_now()
    escalate_breached_tickets(db, now)
    ordered = order_queue(load_tickets(db, search, priority, status, assigned_to, unassigned), now, include_resolved=status == TicketStatus.RESOLVED)
    start = (page - 1) * page_size
    return {"items": [ticket_out(ticket, now) for ticket in ordered[start:start + page_size]], "total": len(ordered), "page": page, "page_size": page_size, "explanation": explain_ticket(ordered[0], ordered, now) if ordered else []}


@router.get("/tickets/export")
def export_tickets(search: str | None = None, priority: str | None = None, status: str | None = None, assigned_to: int | None = None, unassigned: bool = False, db: Session = Depends(get_db)) -> StreamingResponse:
    now = utc_now()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket", "Customer", "Title", "Priority", "Status", "Assignee", "SLA deadline", "Overdue"])
    for ticket in order_queue(load_tickets(db, search, priority, status, assigned_to, unassigned), now):
        writer.writerow([ticket.ticket_number, ticket.customer.name, ticket.title, ticket.priority, ticket.status, ticket.assignee.name if ticket.assignee else "Unassigned", ticket.sla_deadline.isoformat(), "Yes" if is_overdue(ticket, now) else "No"])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tickets.csv"})


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)) -> TicketOut:
    ticket = db.scalar(select(Ticket).options(joinedload(Ticket.customer), joinedload(Ticket.assignee)).where(Ticket.id == ticket_id))
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket_out(ticket)


@router.get("/tickets/{ticket_id}/activities", response_model=list[ActivityOut])
def activities(ticket_id: int, db: Session = Depends(get_db)) -> list[TicketActivity]:
    return list(db.scalars(select(TicketActivity).where(TicketActivity.ticket_id == ticket_id).order_by(TicketActivity.created_at.desc())).all())


def get_ticket_for_update(ticket_id: int, db: Session) -> Ticket:
    ticket = db.scalar(select(Ticket).options(joinedload(Ticket.customer), joinedload(Ticket.assignee)).where(Ticket.id == ticket_id))
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


def record(db: Session, ticket: Ticket, action: str, old: str | None, new: str | None) -> None:
    db.add(TicketActivity(ticket_id=ticket.id, action=action, old_value=old, new_value=new, performed_by="Support team", created_at=utc_now()))


@router.post("/tickets", response_model=TicketOut, status_code=201)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)) -> TicketOut:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(400, "Customer not found")
    if payload.assigned_to_id is not None:
        agent = db.get(Agent, payload.assigned_to_id)
        if not agent or not agent.is_active:
            raise HTTPException(400, "Assignment target is not an active agent")
    now = utc_now()
    ticket = Ticket(ticket_number=f"HD-{now:%y%m%d%H%M%S}-{db.query(Ticket).count() + 1:03d}", title=payload.title, description=payload.description, priority=payload.priority, status=TicketStatus.OPEN, customer_id=payload.customer_id, assigned_to_id=payload.assigned_to_id, created_at=now, updated_at=now, sla_deadline=calculate_deadline(now, payload.priority))
    db.add(ticket)
    db.flush()
    record(db, ticket, "CREATED", None, ticket.ticket_number)
    if payload.assigned_to_id:
        record(db, ticket, "ASSIGNED", None, str(payload.assigned_to_id))
    db.commit()
    db.refresh(ticket)
    return ticket_out(ticket, now)


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)) -> TicketOut:
    ticket = get_ticket_for_update(ticket_id, db)
    changes = payload.model_dump(exclude_unset=True)
    now = utc_now()
    for field, value in changes.items():
        if field == "assigned_to_id":
            if value is not None and (not (agent := db.get(Agent, value)) or not agent.is_active):
                raise HTTPException(400, "Assignment target is not an active agent")
        old = getattr(ticket, field)
        if old != value:
            action = "REASSIGNED" if field == "assigned_to_id" else f"{field.upper()}_CHANGED"
            record(db, ticket, action, str(old) if old is not None else None, str(value) if value is not None else None)
            setattr(ticket, field, value)
            if field == "status" and value == TicketStatus.RESOLVED:
                ticket.resolved_at = now
    ticket.updated_at = now
    db.commit()
    db.refresh(ticket)
    return ticket_out(ticket, now)


@router.patch("/tickets/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(ticket_id: int, assigned_to_id: int | None = None, db: Session = Depends(get_db)) -> TicketOut:
    return update_ticket(ticket_id, TicketUpdate(assigned_to_id=assigned_to_id), db)


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
def change_status(ticket_id: int, status: TicketStatus, db: Session = Depends(get_db)) -> TicketOut:
    return update_ticket(ticket_id, TicketUpdate(status=status), db)


@router.patch("/tickets/{ticket_id}/priority", response_model=TicketOut)
def change_priority(ticket_id: int, priority: Priority, db: Session = Depends(get_db)) -> TicketOut:
    return update_ticket(ticket_id, TicketUpdate(priority=priority), db)


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)) -> dict[str, int]:
    escalate_breached_tickets(db)
    tickets = list(db.scalars(select(Ticket)).all())
    now = utc_now()
    return {"total": len(tickets), "overdue": sum(is_overdue(item, now) for item in tickets), "urgent": sum(item.priority == Priority.URGENT and item.status != TicketStatus.RESOLVED for item in tickets), "unassigned": sum(item.assigned_to_id is None and item.status != TicketStatus.RESOLVED for item in tickets), "open": sum(item.status == TicketStatus.OPEN for item in tickets), "in_progress": sum(item.status == TicketStatus.IN_PROGRESS for item in tickets), "waiting": sum(item.status == TicketStatus.WAITING for item in tickets), "resolved": sum(item.status == TicketStatus.RESOLVED for item in tickets)}


@router.post("/automation/escalate-overdue")
def escalate_overdue(db: Session = Depends(get_db)) -> dict[str, object]:
    escalated = escalate_breached_tickets(db)
    return {"escalated_count": len(escalated), "ticket_numbers": [ticket.ticket_number for ticket in escalated]}

from datetime import timedelta

from app.database import Base, SessionLocal, engine
from app.models import Agent, Customer, Priority, Ticket, TicketActivity, TicketStatus
from app.services.sla_service import calculate_deadline, utc_now

Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(Customer).count():
    now = utc_now()
    customers = [Customer(name=name, email=f"{name.lower().replace(' ', '.')}@example.com", department=department, created_at=now) for name, department in [("Rahul Mehta", "Finance"), ("Aisha Khan", "Operations"), ("Marcus Lee", "Sales"), ("Sofia Garcia", "People"), ("Noah Williams", "Engineering"), ("Maya Patel", "Finance"), ("Ethan Brown", "Marketing"), ("Olivia Chen", "Operations"), ("Liam Smith", "Sales"), ("Zoe Martin", "Engineering"), ("Daniel Kim", "Support")]]
    agents = [Agent(name=name, email=f"{name.lower().replace(' ', '.')}@helpdesk.example.com", team=team, created_at=now) for name, team in [("Alex Morgan", "Platform"), ("Jordan Bell", "Workplace"), ("Sam Rivera", "Security"), ("Taylor Brooks", "Platform"), ("Casey Nguyen", "Workplace"), ("Morgan Ellis", "Security")]]
    db.add_all(customers + agents)
    db.flush()
    patterns = [("VPN access fails after laptop update", "Cannot connect to the corporate VPN from home.", Priority.URGENT, TicketStatus.OPEN, 3, 0, -5), ("Quarterly report permissions", "Please restore access to the reporting folder.", Priority.NORMAL, TicketStatus.OPEN, 0, 1, -30), ("New starter laptop setup", "Prepare a laptop and accounts for Monday.", Priority.URGENT, TicketStatus.IN_PROGRESS, 1, 2, 1), ("Executive access review", "Review elevated access for the new finance workflow.", Priority.HIGH, TicketStatus.OPEN, 6, 4, 1), ("Printer queue stuck", "The second-floor printer is not processing jobs.", Priority.NORMAL, TicketStatus.WAITING, 2, None, 4), ("Expense portal question", "How do I update a cost center?", Priority.NORMAL, TicketStatus.RESOLVED, 5, 3, -48)]
    for index in range(55):
        title, description, priority, status, customer_index, agent_index, age_hours = patterns[index % len(patterns)]
        created = now - timedelta(hours=abs(age_hours) + (index % 7) * 2)
        ticket = Ticket(ticket_number=f"HD-{now:%y%m%d}-{index + 1:03d}", title=title if index < 5 else f"{title} #{index + 1}", description=description, priority=priority, status=status, customer_id=customers[customer_index].id, assigned_to_id=agents[agent_index].id if agent_index is not None else None, created_at=created, updated_at=now, sla_deadline=calculate_deadline(created, priority), resolved_at=created + timedelta(hours=3) if status == TicketStatus.RESOLVED else None)
        db.add(ticket)
        db.flush()
        db.add(TicketActivity(ticket_id=ticket.id, action="CREATED", new_value=ticket.ticket_number, performed_by="System", created_at=created))
    db.commit()
db.close()
print("Seed complete")

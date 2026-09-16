from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Priority(StrEnum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    department: Mapped[str] = mapped_column(String(120), default="General")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    team: Mapped[str] = mapped_column(String(120), default="Support")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="assignee")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_queue", "status", "sla_deadline", "created_at"),
        Index("ix_tickets_assignment", "assigned_to_id", "status"),
        Index("ix_tickets_customer", "customer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=TicketStatus.OPEN)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer: Mapped[Customer] = relationship(back_populates="tickets")
    assignee: Mapped[Agent | None] = relationship(back_populates="tickets")
    activities: Mapped[list["TicketActivity"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class TicketActivity(Base):
    __tablename__ = "ticket_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))
    performed_by: Mapped[str] = mapped_column(String(120), default="System")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ticket: Mapped[Ticket] = relationship(back_populates="activities")

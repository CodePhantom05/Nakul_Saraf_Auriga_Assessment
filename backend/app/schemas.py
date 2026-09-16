from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Priority, TicketStatus


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    department: str = "General"


class CustomerOut(CustomerCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AgentOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    team: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3)
    priority: Priority = Priority.NORMAL
    customer_id: int
    assigned_to_id: int | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=3)
    priority: Priority | None = None
    status: TicketStatus | None = None
    assigned_to_id: int | None = None


class TicketOut(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    priority: str
    status: str
    customer_id: int
    customer_name: str
    assigned_to_id: int | None
    assignee_name: str | None
    created_at: datetime
    updated_at: datetime
    sla_deadline: datetime
    resolved_at: datetime | None
    overdue: bool
    model_config = ConfigDict(from_attributes=True)


class ActivityOut(BaseModel):
    id: int
    action: str
    old_value: str | None
    new_value: str | None
    performed_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

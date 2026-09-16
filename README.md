# Smartdesk

**Smartdesk** is an SLA-aware IT helpdesk ticket management system designed to make the next ticket to handle immediately obvious.

The core of the system is a **server-side queue engine** that continuously determines ticket order based on SLA breach state, priority, deadline, ticket age, and a deterministic ticket-ID tie-breaker.

The application is designed for a generic IT helpdesk rather than a single user or organization.

---

## 1. Problem Statement

IT helpdesks receive tickets with different priorities and response commitments.

Examples include:

* A laptop failing immediately before a client demo.
* A VPN outage affecting an employee.
* A request for a larger monitor.
* A routine software installation request.

The main operational problem is deciding:

> **Which ticket should the support team handle next?**

Smartdesk solves this using an SLA-aware queue.

The queue automatically places overdue active tickets first and then orders the remaining tickets according to priority and time sensitivity.

---

# 2. Key Features

## Ticket Management

Users can:

* Create tickets
* View tickets
* Update tickets
* Change ticket priority
* Change ticket status
* Assign and reassign tickets
* Unassign tickets
* View ticket details
* View ticket activity history

## SLA Management

The system supports SLA deadlines based on ticket priority:

| Priority | Initial SLA |
| -------- | ----------: |
| URGENT   |     2 hours |
| HIGH     |     8 hours |
| NORMAL   |    24 hours |

The original SLA deadline is stored with the ticket and is preserved even if the ticket is escalated.

## Smart Queue

The queue automatically determines which ticket should be handled first.

The ordering logic is:

```text
1. Overdue active tickets
2. Priority
3. Nearest SLA deadline
4. Oldest creation time
5. Ticket ID as deterministic tie-breaker
```

Priority ordering is:

```text
URGENT
   ↓
HIGH
   ↓
NORMAL
```

An overdue NORMAL ticket therefore appears before a non-overdue URGENT ticket because SLA breach takes precedence.

Resolved tickets do not compete with active operational work.

## Automatic Escalation

The backend checks SLA status during relevant queue/statistics reads.

When a ticket breaches its SLA:

```text
NORMAL → HIGH
HIGH   → URGENT
```

Only one priority level is increased per escalation run.

Examples:

```text
NORMAL → HIGH
```

followed by a later escalation:

```text
HIGH → URGENT
```

An already URGENT ticket remains URGENT.

Every escalation is recorded in the ticket activity history.

## Dashboard

The dashboard provides operational statistics including:

* Total tickets
* Overdue tickets
* Urgent tickets
* Unassigned tickets
* Open tickets
* In-progress tickets
* Waiting tickets
* Resolved tickets

## Filters and Search

Tickets can be filtered by:

* Priority
* Status
* Assignee
* Overdue state
* Customer

Customer search is supported through the customer directory.

## Pagination

Tickets are returned using:

```text
FILTER
   ↓
QUEUE ORDER
   ↓
PAGINATION
```

This ensures pagination never causes a lower-priority ticket to appear before a more important ticket.

## Customer History

The customer directory provides:

* Customer information
* Active ticket count
* Resolved ticket count
* Ticket history

## SLA Countdown

The frontend displays the current SLA state, for example:

```text
Due in 1h 24m
Due in 18m
Overdue by 7m
Overdue by 2h 14m
```

The backend remains the source of truth for the actual overdue state.

## Queue Explanation

The system can explain why a ticket appears near the top of the queue.

Examples:

```text
SLA breached
URGENT priority
Closest deadline
Waiting longer than other comparable tickets
```

These explanations are derived from the same queue rules used to order tickets.

## CSV Export

The currently filtered and ordered ticket list can be exported as CSV.

---

# 3. Technology Stack

## Frontend

* React
* Vite
* Tailwind CSS
* React Router
* Lucide React
* JavaScript/JSX

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy 2.x
* Alembic
* Uvicorn

## Database

* PostgreSQL
* SQLite fallback for quick local testing

## Testing

* Pytest
* HTTPX

## Development

* GitHub Codespaces
* Git
* Docker Compose

---

# 4. Architecture

```mermaid
flowchart LR
    Browser[React + Vite + Tailwind] -->|REST API| API[FastAPI]
    API --> Queue[Queue Service]
    API --> SLA[SLA Service]
    API --> Escalation[Escalation Service]
    API --> ORM[SQLAlchemy]
    ORM --> PostgreSQL[(PostgreSQL)]
    ORM --> SQLite[(SQLite fallback)]
```

The important design decision is that **queue ordering is implemented in the backend rather than the browser**.

This prevents different clients from independently calculating inconsistent queue orders.

---

# 5. Project Structure

```text
smartdesk/
│
├── README.md
├── REASONING.md
├── AI_LOGS.md
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── backend/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── seed.py
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   │
│   │   ├── api/
│   │   │   └── routes.py
│   │   │
│   │   └── services/
│   │       ├── queue_service.py
│   │       ├── sla_service.py
│   │       └── escalation_service.py
│   │
│   └── tests/
│       ├── test_queue_service.py
│       └── test_escalation_service.py
│
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── main.jsx
        └── styles.css
```

---

# 6. Database Model

The system uses four main entities.

## Customers

Stores helpdesk customers/requesters.

Important fields:

```text
id
name
email
department
created_at
```

## Agents

Stores helpdesk agents.

Important fields:

```text
id
name
email
team
is_active
created_at
```

## Tickets

Stores support requests.

Important fields:

```text
id
ticket_number
title
description
priority
status
customer_id
assigned_to_id
created_at
updated_at
sla_deadline
resolved_at
```

## Ticket Activities

Stores the history of important ticket operations.

Examples:

```text
Ticket created
Ticket assigned
Ticket reassigned
Priority changed
Status changed
SLA escalation
```

Each activity records the relevant value change and timestamp.

---

# 7. Queue Logic

The queue engine is implemented in:

```text
backend/app/services/queue_service.py
```

The queue key is conceptually:

```text
overdue state
→ priority
→ SLA deadline
→ creation time
→ ticket ID
```

For active tickets:

```text
Overdue = highest precedence
```

Then:

```text
URGENT > HIGH > NORMAL
```

Then:

```text
earliest SLA deadline first
```

Then:

```text
oldest ticket first
```

Finally:

```text
lowest ticket ID first
```

This final ID comparison provides deterministic ordering when all other values are equal.

---

# 8. SLA Calculation

Initial SLA duration:

```text
URGENT = 2 hours
HIGH   = 8 hours
NORMAL = 24 hours
```

The deadline is calculated when the ticket is created:

```text
sla_deadline = created_at + priority SLA duration
```

The deadline is persisted in the database.

The system then checks:

```text
current_time > sla_deadline
```

to determine whether the ticket is overdue.

---

# 9. Automatic Escalation

The escalation service is located at:

```text
backend/app/services/escalation_service.py
```

Escalation follows:

```text
NORMAL → HIGH
HIGH   → URGENT
```

The escalation process:

1. Finds SLA-breached active tickets.
2. Increases priority by one level.
3. Preserves the original SLA deadline.
4. Records the change in ticket activity.
5. Does not escalate resolved tickets.
6. Never jumps more than one priority level in a single run.

---

# 10. API

The FastAPI backend exposes REST endpoints.

## Tickets

```http
GET /api/tickets
GET /api/tickets/{id}
POST /api/tickets
PATCH /api/tickets/{id}
```

## Assignment

```http
PATCH /api/tickets/{id}/assign
```

## Status

```http
PATCH /api/tickets/{id}/status
```

## Priority

```http
PATCH /api/tickets/{id}/priority
```

## Activities

```http
GET /api/tickets/{id}/activities
```

## Export

```http
GET /api/tickets/export
```

## Customers

```http
GET /api/customers?q={query}
GET /api/customers/{id}
```

## Agents

```http
GET /api/agents
```

## Dashboard

```http
GET /api/dashboard/stats
```

---

# 11. Environment Configuration

Create a local `.env` from the example file.

```bash
cp .env.example .env
```

Example configuration:

```env
DATABASE_URL=postgresql+psycopg://helpdesk:helpdesk@localhost:5432/helpdesk
CORS_ORIGINS=http://localhost:5173
```

Frontend configuration:

```env
VITE_API_URL=http://localhost:8000/api
```

Never commit real credentials or secrets.

---

# 12. Running the Project Locally

## Requirements

Install:

* Python 3.11+
* Node.js 20+
* npm
* PostgreSQL

Docker can be used instead of a locally installed PostgreSQL server.

---

## Step 1 — Clone the repository

```bash
git clone <YOUR_PUBLIC_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY>
```

---

## Step 2 — Create environment variables

```bash
cp .env.example .env
```

For the frontend:

```bash
cp frontend/.env.example frontend/.env
```

---

## Step 3 — Start PostgreSQL using Docker

```bash
docker compose up -d postgres
```

Check that the database is running:

```bash
docker compose ps
```

---

# 13. Backend Setup

Create a Python virtual environment.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS / Codespaces

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run database migrations:

```bash
alembic -c backend/alembic.ini upgrade head
```

Seed the database:

```bash
PYTHONPATH=backend python backend/seed.py
```

On Windows PowerShell, use:

```powershell
$env:PYTHONPATH="backend"
python backend/seed.py
```

Start FastAPI:

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

# 14. Frontend Setup

Open another terminal.

Install dependencies:

```bash
npm install --prefix frontend
```

Start the development server:

```bash
npm run dev --prefix frontend
```

Open:

```text
http://localhost:5173
```

---

# 15. GitHub Codespaces Setup

Open the public GitHub repository and select:

```text
Code
→ Codespaces
→ Create codespace on main
```

Inside Codespaces:

### Start PostgreSQL

```bash
docker compose up -d postgres
```

### Start backend

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend python backend/seed.py
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

### Start frontend

In another terminal:

```bash
npm install --prefix frontend
npm run dev --prefix frontend
```

Forward these ports in Codespaces:

```text
5173 → React frontend
8000 → FastAPI backend
```

Then open the forwarded frontend URL.

---

# 16. Seed Data

The repository includes realistic demo data.

The seed script creates:

* 11 customers
* 6 agents
* 55 tickets

The dataset intentionally contains combinations such as:

* overdue NORMAL tickets
* overdue HIGH tickets
* overdue URGENT tickets
* urgent tickets close to SLA
* normal tickets with longer deadlines
* assigned tickets
* unassigned tickets
* resolved tickets
* customers with multiple tickets

This makes the queue behavior easy to demonstrate.

---

# 17. Testing

Run backend tests with:

```bash
PYTHONPATH=backend python -m pytest backend/tests -q
```

The tests cover important queue behavior, including:

* overdue precedence
* priority ordering
* deadline ordering
* creation-time tie-breaking
* deterministic ticket-ID ordering
* exact deadline behavior
* resolved-ticket exclusion

Escalation tests cover:

* NORMAL → HIGH
* HIGH → URGENT
* one-level escalation
* activity logging
* SLA deadline preservation
* resolved-ticket exclusion

---

# 18. Frontend Production Build

To verify that the frontend can build successfully:

```bash
npm run build --prefix frontend
```

Preview the production build:

```bash
npm run preview --prefix frontend
```

---

# 19. Quick API Verification

After starting FastAPI, open:

```text
http://localhost:8000/docs
```

Use the interactive Swagger UI to test endpoints.

For example:

```http
GET /api/tickets
```

should return tickets in queue order.

Verify that an overdue ticket is positioned before a non-overdue ticket with a higher nominal priority.

---

# 20. Debugging

## Backend does not start

Check Python:

```bash
python --version
```

Check installed packages:

```bash
pip list
```

Reinstall:

```bash
pip install -r backend/requirements.txt
```

---

## Database connection error

Check:

```bash
docker compose ps
```

If PostgreSQL is stopped:

```bash
docker compose up -d postgres
```

Verify the `DATABASE_URL` in `.env`.

---

## Migration error

Run:

```bash
alembic -c backend/alembic.ini current
```

Then:

```bash
alembic -c backend/alembic.ini upgrade head
```

---

## Frontend cannot connect to backend

Check that FastAPI is running:

```text
http://localhost:8000/docs
```

Check:

```env
VITE_API_URL=http://localhost:8000/api
```

Also verify the backend CORS setting:

```env
CORS_ORIGINS=http://localhost:5173
```

Restart the frontend after changing environment variables.

---

## No tickets appear

Run the seed script again:

```bash
PYTHONPATH=backend python backend/seed.py
```

Then refresh the frontend.

---

## Queue order looks incorrect

First check the backend response directly:

```text
GET /api/tickets
```

Then verify:

1. Ticket status
2. SLA deadline
3. Current time
4. Priority
5. Creation time

The queue is calculated by the backend, so debugging should start with the API response rather than the React UI.

---

# 21. Recommended Demo Flow

For an evaluator demonstration:

### Step 1

Open the dashboard.

Show:

* Total tickets
* Overdue tickets
* Urgent tickets
* Unassigned tickets

### Step 2

Open the operational queue.

Show that the top ticket is the ticket that should be handled next.

### Step 3

Open the top ticket.

Demonstrate the explanation:

```text
SLA breached
URGENT priority
Closest deadline
```

### Step 4

Use the filters.

Test:

```text
Overdue
My Queue
Urgent
Normal
Unassigned
```

### Step 5

Search a customer.

Open the customer's history.

### Step 6

Assign a ticket to an agent.

Verify that it appears in that agent's queue.

### Step 7

Change a ticket status.

Open its activity history and show the recorded change.

### Step 8

Demonstrate escalation.

Use seeded or controlled SLA data to show:

```text
NORMAL → HIGH
HIGH → URGENT
```

### Step 9

Demonstrate pagination.

Confirm that the highest-priority tickets remain on the first page.

### Step 10

Export filtered tickets to CSV.

---

# 22. Core Design Principle

The most important rule in the application is:

```text
Correct queue ordering > filters > assignment > visual enhancements
```

The system should always answer:

> **Which ticket should the support team handle next?**

before adding secondary features.

---

# 23. Future Improvements

The current implementation can be extended with:

* Authentication
* Role-based permissions
* Agent-specific dashboards
* WebSocket real-time queue updates
* Redis caching
* Background SLA notification workers
* Email or Slack notifications
* Bulk ticket operations
* Advanced analytics
* Audit reporting
* Full API integration test coverage
* Production deployment
* Dockerized frontend/backend services

These features should be added only after the core queue and SLA workflows remain fully tested.

---

# 24. Required Assessment Files

The repository root must contain:

```text
README.md
REASONING.md
AI_LOGS.md
```

### README.md

Contains:

* setup instructions
* running instructions
* architecture
* API information
* testing
* debugging
* project usage

### REASONING.md

Contains the design reasoning and technical decisions behind the implementation.

### AI_LOGS.md

Must contain the complete AI-tool conversation/log required by the assessment.

**AI_LOGS.md must not be edited, summarized, reformatted, or manually cleaned.**

---

# 25. Final Verification Checklist

Before submitting the repository, verify:

```text
[ ] Repository is public
[ ] README.md exists at root
[ ] REASONING.md exists at root
[ ] AI_LOGS.md exists at root
[ ] Frontend starts
[ ] Backend starts
[ ] PostgreSQL connects
[ ] Alembic migrations work
[ ] Seed data loads
[ ] Queue tests pass
[ ] Escalation tests pass
[ ] Ticket creation works
[ ] Assignment works
[ ] Status updates work
[ ] Priority changes work
[ ] Customer search works
[ ] Filters work
[ ] Pagination works
[ ] CSV export works
[ ] SLA countdown works
[ ] Overdue ordering works
[ ] Resolved tickets are excluded from active queue
[ ] README instructions work in a fresh environment
[ ] No secrets are committed
[ ] AI_LOGS.md remains an unmodified original log
```

---

## License

This project is created as an assessment/demo project.

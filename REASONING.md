# Smartdesk — Design Reasoning

## 1. Overview

Smartdesk is an SLA-aware IT helpdesk system designed around one central operational question:

> **Which ticket should be handled next?**

The assessment emphasizes that the queue ordering rule is the heart of the application. Therefore, the design prioritizes the correctness, consistency, and testability of the queue engine before secondary features such as filtering, assignment, search, analytics, and UI enhancements.

The application is designed to be generic enough for any IT helpdesk rather than being tied to a single employee or organization.

---

# 2. Problem Understanding

A helpdesk can contain tickets with very different levels of urgency.

For example:

* A laptop has failed immediately before a customer demonstration.
* A user has lost VPN access.
* A user needs a larger monitor.
* A routine software installation is requested.

Simply sorting tickets by priority is not sufficient.

A NORMAL ticket that has already breached its SLA should not remain behind an URGENT ticket that still has significant time remaining.

Therefore, the queue must consider both:

1. **Priority**
2. **SLA state**

The requirement that overdue tickets "jump to the front" is the most important rule in the system.

---

# 3. Technology Choices

## Frontend: React

React was selected because the application is highly interactive.

The UI needs to update when:

* Tickets are assigned
* Status changes
* Priority changes
* Filters change
* Search results change
* SLA countdowns change

React's component-based architecture also makes it easy to separate reusable UI elements such as ticket rows, filters, countdowns, dashboard cards, and activity timelines.

---

# 4. Styling: Tailwind CSS

Tailwind CSS was selected to build the interface quickly while maintaining a consistent design system.

The helpdesk interface requires many visual states:

* Overdue
* Urgent
* High
* Normal
* Resolved
* Unassigned
* In progress

Tailwind makes these states easy to represent consistently across the application.

The UI does not rely exclusively on color. Text labels and status indicators are also used so that the important information remains clear.

---

# 5. Backend: FastAPI

FastAPI was selected because the application needs a clean REST API between the frontend and the backend.

It provides:

* Request validation
* Response schemas
* Automatic API documentation
* Clear routing
* Good support for asynchronous applications
* A clean structure for service-layer business logic

Most importantly, FastAPI allows the queue and SLA rules to live on the server.

This avoids relying on the browser to determine the authoritative ticket order.

---

# 6. Database: PostgreSQL

PostgreSQL was selected because the application contains strongly related entities:

```text
Customer
   ↓
Ticket
   ↓
Agent
   ↓
Ticket Activity
```

A relational database fits these relationships naturally.

PostgreSQL also provides:

* Foreign keys
* Indexes
* Transactions
* Strong data consistency
* Reliable ordering/query behavior
* Good support for production workloads

SQLite can be used as a lightweight fallback for development where appropriate, but PostgreSQL is the primary target database.

---

# 7. ORM: SQLAlchemy

SQLAlchemy was selected to provide a structured database-access layer.

Using an ORM gives the application:

* Python database models
* Relationships between entities
* Reusable queries
* Transaction handling
* Better separation between persistence and business logic

It also makes it easier to change or extend the database schema as the project grows.

---

# 8. Database Design

The initial database contains four major entities.

## Customers

Stores information about users requesting help.

Important fields include:

```text
id
name
email
department
created_at
```

## Agents

Stores helpdesk staff.

Important fields include:

```text
id
name
email
team
is_active
created_at
```

## Tickets

Stores the actual support requests.

Important fields include:

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

Stores a history of important operations.

Examples:

```text
Ticket created
Ticket assigned
Ticket reassigned
Priority changed
Status changed
SLA escalated
```

This separation keeps the data model normalized and makes it possible to display an audit timeline.

---

# 9. SLA Design

The application uses priority-dependent SLA rules.

The initial response commitments are:

| Priority |      SLA |
| -------- | -------: |
| URGENT   |  2 hours |
| HIGH     |  8 hours |
| NORMAL   | 24 hours |

The SLA deadline is calculated when a ticket is created:

```text
sla_deadline = created_at + SLA duration
```

The resulting deadline is stored with the ticket.

This is important because the original SLA commitment should remain stable even if the ticket is later escalated.

For example:

```text
Ticket created:
NORMAL
SLA = 24 hours
```

If the ticket later becomes HIGH because the SLA is breached, its original deadline is not reset to a new 8-hour period.

---

# 10. Why the Queue Engine Is Server-Side

The queue is the most important piece of business logic in the system.

If the ordering were implemented only in React, different clients could potentially display different queues or apply inconsistent rules.

Instead:

```text
React
   ↓
FastAPI
   ↓
Queue Service
   ↓
PostgreSQL
```

The server determines the authoritative ordering.

The frontend is responsible for displaying that order.

This creates a single source of truth.

---

# 11. Queue Ordering Strategy

The queue follows this priority hierarchy:

```text
1. Overdue state
2. Priority
3. SLA deadline
4. Creation time
5. Ticket ID
```

Conceptually:

```text
OVERDUE
   ↓
URGENT
   ↓
HIGH
   ↓
NORMAL
```

However, overdue state has precedence over priority.

Therefore:

```text
Overdue NORMAL
```

must appear before:

```text
Non-overdue URGENT
```

because the assessment explicitly requires overdue tickets to jump to the front.

---

# 12. Detailed Queue Algorithm

For each active ticket:

### Step 1 — Determine overdue state

```text
current_time > sla_deadline
```

If true:

```text
overdue = true
```

Otherwise:

```text
overdue = false
```

### Step 2 — Compare overdue tickets first

All overdue tickets are placed before tickets that have not breached their SLA.

### Step 3 — Compare priority

Within the same overdue state:

```text
URGENT > HIGH > NORMAL
```

### Step 4 — Compare SLA deadline

If two tickets have the same priority, the ticket with the nearest deadline comes first.

### Step 5 — Compare creation time

If their deadlines are equal, the older ticket comes first.

### Step 6 — Use ticket ID as a deterministic tie-breaker

If all previous values are identical, ticket ID provides deterministic ordering.

This prevents unstable or random ordering.

---

# 13. Why Deterministic Ordering Matters

Suppose two tickets have:

* Same overdue state
* Same priority
* Same SLA deadline
* Same creation time

Without another tie-breaker, their order could change between requests.

That makes the application harder to reason about and test.

Using ticket ID as the final comparison ensures:

```text
Same input → Same output
```

which is useful for both users and automated tests.

---

# 14. Active vs Resolved Tickets

Resolved tickets should not compete with active operational work.

Therefore, the operational queue excludes resolved tickets.

A resolved ticket can still be viewed through:

* Ticket history
* Customer history
* Search
* Reporting
* Dashboard statistics

but it should not appear as the next ticket to handle.

---

# 15. Escalation Design

Automatic escalation is separate from queue ordering.

The escalation system detects SLA breaches and increases priority one level at a time:

```text
NORMAL → HIGH
HIGH   → URGENT
```

The escalation service intentionally does not jump multiple levels during one execution.

For example:

```text
NORMAL
```

does not become:

```text
URGENT
```

in one run.

Instead:

```text
NORMAL → HIGH
```

and a later run may move it to:

```text
HIGH → URGENT
```

This makes escalation predictable and auditable.

---

# 16. SLA Preservation During Escalation

Escalation changes the priority, but it does not reset the original SLA deadline.

This distinction is important.

Without this rule, a ticket could continuously receive a new response window whenever it escalates, defeating the purpose of SLA enforcement.

Therefore:

```text
Priority changes
        ↓
Original SLA deadline remains
```

---

# 17. Activity Logging

Every important state-changing operation is recorded.

For example:

```text
Ticket #1042 created
Ticket #1042 assigned to Priya
Ticket #1042 changed from NORMAL to HIGH
Ticket #1042 status changed from OPEN to IN_PROGRESS
```

This provides an audit trail and allows the UI to display a timeline.

It also makes automatic escalation transparent to the user.

---

# 18. Why Filters Are Applied Before Pagination

A major implementation decision is:

```text
FILTER
   ↓
QUEUE ORDER
   ↓
PAGINATION
```

rather than:

```text
PAGINATION
   ↓
FILTER
   ↓
SORT
```

The first approach ensures that the first page represents the true highest-priority tickets within the selected dataset.

For example, if there are 500 tickets and only 20 are shown per page, the first page must contain the first 20 tickets according to the queue rules—not merely the first 20 records inserted into the database.

---

# 19. Why Queue Logic Is Kept Separate From API Routes

The queue algorithm is implemented as a dedicated service instead of being embedded directly inside a FastAPI route.

This provides several benefits:

* Easier testing
* Reusable business logic
* Cleaner API handlers
* Easier future optimization
* Less coupling between HTTP and business rules

Conceptually:

```text
API Route
    ↓
Queue Service
    ↓
Queue Algorithm
```

The service can therefore be tested without needing to start a web server.

---

# 20. Search and Filtering

Search and filters are treated as views over the same queue.

For example:

```text
All tickets
```

may become:

```text
My tickets
```

or:

```text
Overdue tickets
```

or:

```text
URGENT tickets
```

But once the result set is selected, the same queue ordering rules still apply.

This keeps behavior consistent throughout the application.

---

# 21. Customer History

Customer history is designed separately from operational queueing.

A support agent may need to answer:

> "What tickets has this customer raised previously?"

The customer view therefore focuses on:

* Ticket history
* Current active tickets
* Resolved tickets
* Status
* Recent activity

This complements the queue rather than changing how the queue works.

---

# 22. "Why Is This Ticket First?"

An additional usability feature is the queue explanation.

Rather than simply displaying a ticket at position one, the system can explain the factors responsible for its position.

Examples:

```text
SLA breached
URGENT priority
Closest deadline
Oldest matching ticket
```

This improves transparency and makes the queue behavior easier to understand during a demo.

The explanation should be derived from actual queue data rather than hardcoded.

---

# 23. Testing Strategy

The queue engine is the most important area to test.

Core cases include:

### Test 1 — Overdue precedence

```text
NORMAL + overdue
```

must appear before:

```text
URGENT + not overdue
```

### Test 2 — Priority

Within the same SLA state:

```text
URGENT > HIGH > NORMAL
```

### Test 3 — Deadline

Two tickets with the same priority are ordered by nearest SLA deadline.

### Test 4 — Creation time

Identical deadlines are resolved using creation time.

### Test 5 — Deterministic tie-breaking

Identical previous values are resolved using ticket ID.

### Test 6 — Resolved tickets

Resolved tickets are excluded from the operational queue.

### Test 7 — Escalation

Verify:

```text
NORMAL → HIGH
HIGH → URGENT
```

### Test 8 — SLA preservation

Escalation must not reset the original SLA deadline.

### Test 9 — Filtering

Filtering must preserve queue ordering.

### Test 10 — Pagination

Pagination must happen after filtering and ordering.

---

# 24. Error Handling

The backend should return appropriate HTTP responses for invalid requests.

Examples:

```text
400 — Invalid input
404 — Ticket/customer/agent not found
422 — Validation error
500 — Unexpected server error
```

The frontend should provide:

* Loading states
* Error states
* Empty states
* Clear user-facing messages

Internal database errors should not be exposed unnecessarily to end users.

---

# 25. Security Considerations

The project should:

* Keep credentials in environment variables.
* Never commit the real `.env`.
* Validate incoming API data.
* Use SQLAlchemy/parameterized queries rather than constructing raw SQL from user input.
* Configure CORS explicitly.
* Avoid returning sensitive internal errors.
* Keep inactive agents from receiving new assignments.

Authentication and role-based authorization can be added as future enhancements.

---

# 26. Development Strategy

The project is intentionally built in phases.

## Phase 1 — Infrastructure

Set up:

* GitHub repository
* Codespace
* React
* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic

## Phase 2 — Core Logic

Implement:

* Database models
* SLA calculation
* Overdue detection
* Queue engine
* Escalation service
* Tests

## Phase 3 — Core Application

Implement:

* Ticket creation
* Ticket listing
* Ticket details
* Assignment
* Status management

## Phase 4 — Required Queue Features

Implement:

* Overdue filtering
* My Queue
* Priority filtering
* Status filtering
* Customer search
* Pagination

## Phase 5 — User Experience

Implement:

* SLA countdown
* Queue explanation
* Activity timeline
* Customer history
* Dashboard statistics
* CSV export

## Phase 6 — Optional Advanced Features

Only after the core behavior is stable:

* Authentication
* WebSockets
* Redis
* Background notification workers

---

# 27. Trade-Offs

## Why not put everything in React?

Because the queue is business-critical logic.

Keeping it on the backend provides one authoritative result for every client.

## Why not use MongoDB?

A relational database fits the relationships between customers, tickets, agents, and activities more naturally.

## Why PostgreSQL instead of SQLite only?

PostgreSQL is more representative of a production helpdesk environment and handles relational constraints and concurrent usage more robustly.

SQLite remains useful for lightweight development.

## Why not introduce Redis immediately?

Redis could improve performance or enable caching, but it adds infrastructure complexity without being necessary for the core assessment.

The first goal is correctness.

## Why not use a complicated microservice architecture?

The project does not require it.

A clear frontend/API/database architecture is easier to develop, test, debug, and evaluate.

---

# 28. Expected System Behavior

Given tickets such as:

```text
Ticket A → NORMAL → overdue
Ticket B → URGENT → due in 20 minutes
Ticket C → HIGH → due in 40 minutes
Ticket D → NORMAL → due tomorrow
```

the operational queue should be:

```text
A
B
C
D
```

because the SLA breach takes precedence over nominal priority.

If A is resolved:

```text
B
C
D
```

becomes the active queue.

If C later becomes overdue:

```text
C
B
D
```

depending on the resulting overdue/priority/deadline comparisons.

This demonstrates that the queue is dynamic rather than static.

---

# 29. Maintainability Principles

The implementation should follow:

* Single responsibility
* Reusable services
* Reusable React components
* Typed/validated API schemas
* Database constraints
* Automated tests
* Clear naming
* Small functions
* Minimal duplication
* Business logic separate from presentation

The queue engine should remain independently testable.

---

# 30. Final Design Principle

The central design principle is:

> **The application should make the next ticket to handle obvious, explainable, and consistently ordered.**

Everything else—filters, search, assignment, customer history, pagination, dashboard statistics, and visual polish—supports this objective.

The most important implementation priority is therefore:

```text
Correct SLA logic
       ↓
Correct queue ordering
       ↓
Correct tests
       ↓
Correct API
       ↓
Filters and assignment
       ↓
UI enhancements
```

A visually impressive interface is not useful if the wrong ticket is placed at the top.

Therefore, correctness of the server-side queue engine is the primary success criterion of the system.

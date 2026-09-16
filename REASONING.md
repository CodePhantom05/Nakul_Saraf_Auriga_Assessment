## Solution rationale

### Starting point

The repository began as an empty assessment shell, so the implementation was built around the highest-risk requirement first: the SLA queue ordering engine. The API is the source of truth for ordering and overdue state; the React client displays and mutates that state but does not sort tickets itself.

### Queue model

Active tickets are ordered after filtering, before pagination. The sort key is:

1. SLA breach state, with overdue tickets first.
2. Priority, ordered `URGENT`, `HIGH`, then `NORMAL`.
3. Nearest persisted SLA deadline.
4. Oldest creation timestamp.
5. Ticket ID as a deterministic final tie-breaker.

Resolved tickets are excluded from the operational queue, but remain available through the explicit Resolved filter and dashboard history counts. This keeps the “next ticket” view operational without hiding historical work.

### SLA and escalation

Ticket creation persists one deadline using the priority at creation time: 2 hours for urgent, 8 hours for high, and 24 hours for normal. Overdue state is then calculated by comparing the current UTC time with that stored deadline. Database timestamps are normalized to UTC at the service boundary so PostgreSQL and SQLite behave consistently.

The escalation service runs against breached active tickets. It advances normal to high and high to urgent, never more than one level in a single run. Urgent and resolved tickets do not escalate. The original deadline is deliberately preserved, and each change creates a `SLA_ESCALATED` activity record. Queue and dashboard reads run the check automatically, while `/api/automation/escalate-overdue` supports a scheduler or manual run.

### Domain and API choices

Customers, agents, tickets, and ticket activities are normalized relational models. Assignment, status, priority, customer creation, ticket creation, and ticket editing are validated in FastAPI schemas and routes. Meaningful mutations are recorded in activity history. The frontend can select an existing customer or create a new one inline, and shared ticket editing supports title, description, priority, and status changes.

### Delivery choices

PostgreSQL is the documented deployment database, with Docker Compose for reproducibility. SQLite remains the default fallback for a quick Codespaces demo and isolated tests. The React build is served by FastAPI when `frontend/dist` exists, so one forwarded port exposes both the UI and API; API requests use same-origin `/api` paths to work through Codespaces forwarding.

### Verification

The backend has focused tests for overdue precedence, priority/deadline/age tie-breakers, resolved exclusion, exact deadlines, and one-level escalation with logging and deadline preservation. The frontend is verified with a Vite production build. Migration, seed data, API smoke checks, customer creation, assignment, unassignment, status changes, and live frontend serving were also exercised during implementation.

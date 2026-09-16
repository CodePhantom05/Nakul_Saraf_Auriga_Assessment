import { useEffect, useState } from "react";
import {
  Link,
  Route,
  Routes,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Download,
  Inbox,
  LayoutDashboard,
  Pencil,
  Plus,
  Search,
  Users,
  X,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "/api";
const filters = [
  ["", "All tickets"],
  ["OPEN", "Open"],
  ["IN_PROGRESS", "In progress"],
  ["WAITING", "Waiting"],
  ["RESOLVED", "Resolved"],
];

function useApi(path, options) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    fetch(`${API}${path}`, options)
      .then((r) => {
        if (!r.ok) throw new Error("Unable to load helpdesk data");
        return r.json();
      })
      .then((value) => active && setData(value))
      .catch((e) => active && setError(e.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [path]);
  return { data, error, loading };
}

function formatSla(deadline, overdue) {
  const delta = new Date(deadline).getTime() - Date.now();
  const minutes = Math.max(1, Math.round(Math.abs(delta) / 60000));
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  const value = hours ? `${hours}h ${rest}m` : `${rest}m`;
  return overdue ? `Overdue by ${value}` : `Due in ${value}`;
}
function Header() {
  return (
    <header className="topbar">
      <Link className="brand" to="/">
        <span className="brand-mark">S</span>
        <span>
          smart<span className="brand-accent">desk</span>
        </span>
      </Link>
      <nav>
        <Link to="/">Queue</Link>
        <Link to="/customers">Customers</Link>
      </nav>
      <div className="header-user">
        <span className="status-dot" /> <span>Support team</span>
        <span className="avatar">ST</span>
      </div>
    </header>
  );
}
function Stat({ icon: Icon, label, value, tone }) {
  return (
    <div className={`stat stat-${tone}`}>
      <div className="stat-icon">
        <Icon size={18} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value ?? "—"}</strong>
      </div>
    </div>
  );
}
function Stats({ stats }) {
  return (
    <section className="stats-grid">
      <Stat
        icon={Inbox}
        label="Total tickets"
        value={stats?.total}
        tone="ink"
      />
      <Stat
        icon={AlertCircle}
        label="Overdue now"
        value={stats?.overdue}
        tone="red"
      />
      <Stat
        icon={ArrowUpRight}
        label="Urgent active"
        value={stats?.urgent}
        tone="amber"
      />
      <Stat
        icon={Users}
        label="Unassigned"
        value={stats?.unassigned}
        tone="blue"
      />
      <Stat icon={Clock3} label="Open" value={stats?.open} tone="mint" />
      <Stat
        icon={CheckCircle2}
        label="Resolved"
        value={stats?.resolved}
        tone="gray"
      />
    </section>
  );
}
function Badge({ children, type }) {
  return (
    <span className={`badge badge-${type?.toLowerCase().replace("_", "-")}`}>
      {children?.replace("_", " ")}
    </span>
  );
}
function TicketRow({ ticket, top }) {
  const navigate = useNavigate();
  return (
    <button
      className={`ticket-row ${top ? "ticket-top" : ""}`}
      onClick={() => navigate(`/tickets/${ticket.id}`)}
    >
      <div className="ticket-main">
        <div className="ticket-number">
          {ticket.ticket_number}{" "}
          {top && <span className="next-label">NEXT UP</span>}
        </div>
        <h3>{ticket.title}</h3>
        <p>
          {ticket.customer_name} <span>·</span>{" "}
          {ticket.assignee_name || "Unassigned"}
        </p>
      </div>
      <div className="ticket-meta">
        <Badge type={ticket.priority}>{ticket.priority}</Badge>
        <Badge type={ticket.status}>{ticket.status}</Badge>
        <span className={`sla ${ticket.overdue ? "sla-overdue" : ""}`}>
          <Clock3 size={14} />
          {formatSla(ticket.sla_deadline, ticket.overdue)}
        </span>
      </div>
      <ArrowUpRight className="row-arrow" size={18} />
    </button>
  );
}
function CreateTicket({ onClose }) {
  const customers = useApi("/customers");
  const [form, setForm] = useState({
    title: "",
    description: "",
    customer_id: "",
    priority: "NORMAL",
  });
  const [newCustomer, setNewCustomer] = useState(false);
  const [customerForm, setCustomerForm] = useState({
    name: "",
    email: "",
    department: "General",
  });
  const [message, setMessage] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    let customerId = form.customer_id;
    if (newCustomer) {
      const customerResponse = await fetch(`${API}/customers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(customerForm),
      });
      if (!customerResponse.ok) {
        setMessage("Enter a unique customer name and valid email.");
        return;
      }
      customerId = (await customerResponse.json()).id;
    }
    const response = await fetch(`${API}/tickets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, customer_id: customerId }),
    });
    if (response.ok) {
      setMessage("Ticket created and added to the queue.");
      setTimeout(() => window.location.reload(), 700);
    } else setMessage("Please check the required fields.");
  };
  return (
    <div className="modal-backdrop">
      <form className="modal" onSubmit={submit}>
        <button type="button" className="icon-button close" onClick={onClose}>
          <X size={18} />
        </button>
        <span className="eyebrow">NEW REQUEST</span>
        <h2>Create a ticket</h2>
        <p className="modal-subtitle">
          It will be placed automatically using SLA urgency and priority.
        </p>
        <label>
          Customer name
          {!newCustomer ? (
            <select
              required
              disabled={customers.loading}
              value={form.customer_id}
              onChange={(e) =>
                setForm({ ...form, customer_id: Number(e.target.value) })
              }
            >
              <option value="">Select an existing customer</option>
              {customers.data?.map((customer) => (
                <option value={customer.id} key={customer.id}>
                  {customer.name} · {customer.department}
                </option>
              ))}
            </select>
          ) : (
            <input
              required
              value={customerForm.name}
              onChange={(e) =>
                setCustomerForm({ ...customerForm, name: e.target.value })
              }
              placeholder="Full name"
            />
          )}
        </label>
        <button
          type="button"
          className="customer-toggle"
          onClick={() => setNewCustomer(!newCustomer)}
        >
          {newCustomer ? "Use an existing customer" : "New customer? Add them"}
        </button>
        {newCustomer && (
          <>
            <label>
              Email
              <input
                required
                type="email"
                value={customerForm.email}
                onChange={(e) =>
                  setCustomerForm({ ...customerForm, email: e.target.value })
                }
                placeholder="name@company.com"
              />
            </label>
            <label>
              Department
              <input
                value={customerForm.department}
                onChange={(e) =>
                  setCustomerForm({
                    ...customerForm,
                    department: e.target.value,
                  })
                }
                placeholder="Department"
              />
            </label>
          </>
        )}
        <label>
          Title
          <input
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="What needs attention?"
          />
        </label>
        <label>
          Description
          <textarea
            required
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Add useful context for the team..."
          />
        </label>
        <label>
          Priority
          <select
            value={form.priority}
            onChange={(e) => setForm({ ...form, priority: e.target.value })}
          >
            <option>NORMAL</option>
            <option>HIGH</option>
            <option>URGENT</option>
          </select>
        </label>
        {message && <p className="form-message">{message}</p>}
        <button className="primary-button" type="submit">
          <Plus size={17} /> Create ticket
        </button>
      </form>
    </div>
  );
}
function Queue() {
  const [params, setParams] = useSearchParams();
  const [showCreate, setShowCreate] = useState(false);
  const [tick, setTick] = useState(0);
  const page = Number(params.get("page") || 1);
  const search = params.get("search") || "";
  const status = params.get("status") || "";
  const priority = params.get("priority") || "";
  const query = `/tickets?page=${page}&page_size=8&search=${encodeURIComponent(search)}&status=${status}&priority=${priority}`;
  const queue = useApi(query);
  const stats = useApi("/dashboard/stats");
  useEffect(() => {
    const id = setInterval(() => setTick((value) => value + 1), 30000);
    return () => clearInterval(id);
  }, []);
  const update = (key, value) => {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    next.delete("page");
    setParams(next);
  };
  return (
    <>
      <Header />
      <main className="shell">
        <div className="page-heading">
          <div>
            <span className="eyebrow">OPERATIONS / LIVE QUEUE</span>
            <h1>Good morning, keep work moving.</h1>
            <p className="lede">
              The next ticket is always determined by the SLA clock.
            </p>
          </div>
          <button
            className="primary-button"
            onClick={() => setShowCreate(true)}
          >
            <Plus size={17} /> New ticket
          </button>
        </div>
        <Stats stats={stats.data} />
        <section className="queue-section">
          <div className="queue-heading">
            <div>
              <span className="eyebrow">HANDLING ORDER</span>
              <h2>Operational queue</h2>
            </div>
            {queue.data && (
              <span className="count-label">
                {queue.data.total} active tickets
              </span>
            )}
          </div>
          <div className="controls">
            <div className="search-control">
              <Search size={17} />
              <input
                value={search}
                onChange={(e) => update("search", e.target.value)}
                placeholder="Search ticket, title, or customer..."
              />
            </div>
            <select
              value={priority}
              onChange={(e) => update("priority", e.target.value)}
            >
              <option value="">All priorities</option>
              <option value="URGENT">Urgent only</option>
              <option value="HIGH">High only</option>
              <option value="NORMAL">Normal only</option>
            </select>
            <div className="filter-pills">
              {filters.map(([value, label]) => (
                <button
                  key={value}
                  className={status === value ? "active" : ""}
                  onClick={() => update("status", value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <a className="export-link" href={`${API}/tickets/export`}>
              <Download size={15} /> Export
            </a>
          </div>
          {queue.loading ? (
            <div className="empty-state">Loading the live queue...</div>
          ) : queue.error ? (
            <div className="empty-state error-state">
              {queue.error}. Start the API at port 8000.
            </div>
          ) : (
            <>
              {queue.data?.items?.length ? (
                <div className="ticket-list">
                  {queue.data.items.map((ticket, index) => (
                    <TicketRow
                      key={ticket.id}
                      ticket={ticket}
                      top={index === 0 && page === 1}
                    />
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  No tickets match these filters.
                </div>
              )}
              <div className="queue-footer">
                <span>
                  Showing {queue.data?.items.length ? (page - 1) * 8 + 1 : 0}–
                  {Math.min(page * 8, queue.data?.total || 0)} of{" "}
                  {queue.data?.total || 0}
                </span>
                <div>
                  <button
                    className="page-button"
                    disabled={page === 1}
                    onClick={() => update("page", String(page - 1))}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="page-number">{page}</span>
                  <button
                    className="page-button"
                    disabled={page * 8 >= (queue.data?.total || 0)}
                    onClick={() => update("page", String(page + 1))}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </main>
      {showCreate && <CreateTicket onClose={() => setShowCreate(false)} />}
    </>
  );
}
function TicketDetail() {
  const [params] = useSearchParams();
  const path = window.location.pathname;
  const ticketId = path.split("/").pop();
  const ticket = useApi(`/tickets/${ticketId}`);
  const activity = useApi(`/tickets/${ticketId}/activities`);
  const agents = useApi("/agents");
  const [updating, setUpdating] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const updateStatus = async (status) => {
    setUpdating(true);
    const response = await fetch(`${API}/tickets/${ticketId}/status?status=${status}`, {
      method: "PATCH",
    });
    if (response.ok) window.location.reload();
    setUpdating(false);
  };
  const updateAssignee = async (assignedToId) => {
    setAssigning(true);
    const value = assignedToId ? `?assigned_to_id=${assignedToId}` : "";
    const response = await fetch(`${API}/tickets/${ticketId}/assign${value}`, {
      method: "PATCH",
    });
    if (response.ok) window.location.reload();
    setAssigning(false);
  };
  const saveTicket = async (event) => {
    event.preventDefault();
    setSaving(true);
    const form = new FormData(event.currentTarget);
    const response = await fetch(`${API}/tickets/${ticketId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: form.get("title"),
        description: form.get("description"),
        priority: form.get("priority"),
        status: form.get("status"),
      }),
    });
    if (response.ok) window.location.reload();
    setSaving(false);
  };
  if (ticket.loading)
    return (
      <>
        <Header />
        <main className="shell">
          <div className="empty-state">Loading ticket...</div>
        </main>
      </>
    );
  if (ticket.error)
    return (
      <>
        <Header />
        <main className="shell">
          <div className="empty-state error-state">{ticket.error}</div>
        </main>
      </>
    );
  const item = ticket.data;
  return (
    <>
      <Header />
      <main className="shell detail-shell">
        <Link to="/" className="back-link">
          <ChevronLeft size={16} /> Back to queue
        </Link>
        <div className="detail-header">
          <div>
            <span className="eyebrow">{item.ticket_number}</span>
            <h1>{item.title}</h1>
            <p className="lede">
              {item.customer_name} · opened{" "}
              {new Date(item.created_at).toLocaleString()}
            </p>
          </div>
          <div className={`detail-sla ${item.overdue ? "is-overdue" : ""}`}>
            <Clock3 size={20} />
            <span>{formatSla(item.sla_deadline, item.overdue)}</span>
            <small>
              SLA deadline {new Date(item.sla_deadline).toLocaleString()}
            </small>
          </div>
          <div className="detail-actions">
            <button className="edit-ticket-button" onClick={() => setEditing(!editing)}>
              <Pencil size={14} /> {editing ? "Close editor" : "Edit ticket"}
            </button>
            <span>Update status</span>
            <div>
              {[
                ["IN_PROGRESS", "Start work"],
                ["WAITING", "Mark waiting"],
                ["RESOLVED", "Resolve ticket"],
              ].map(([status, label]) => (
                <button
                  className={item.status === status ? "selected" : ""}
                  disabled={updating || item.status === status}
                  key={status}
                  onClick={() => updateStatus(status)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="detail-grid">
          <article className="detail-card">
            {editing && (
              <form className="edit-ticket-form" onSubmit={saveTicket}>
                <h3>Edit ticket</h3>
                <label>
                  Title
                  <input name="title" defaultValue={item.title} required />
                </label>
                <label>
                  Description
                  <textarea name="description" defaultValue={item.description} required />
                </label>
                <div className="edit-fields">
                  <label>
                    Priority
                    <select name="priority" defaultValue={item.priority}>
                      <option>NORMAL</option>
                      <option>HIGH</option>
                      <option>URGENT</option>
                    </select>
                  </label>
                  <label>
                    Status
                    <select name="status" defaultValue={item.status}>
                      <option>OPEN</option>
                      <option>IN_PROGRESS</option>
                      <option>WAITING</option>
                      <option>RESOLVED</option>
                    </select>
                  </label>
                </div>
                <button className="primary-button" disabled={saving} type="submit">
                  {saving ? "Saving..." : "Save changes"}
                </button>
              </form>
            )}
            <div className="detail-badges">
              <Badge type={item.priority}>{item.priority}</Badge>
              <Badge type={item.status}>{item.status}</Badge>
            </div>
            <p className="description">{item.description}</p>
            <h3>Ticket activity</h3>
            <div className="timeline">
              {activity.data?.map((event) => (
                <div className="timeline-item" key={event.id}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{event.action.replace("_", " ")}</strong>
                    <p>
                      {event.new_value || "Recorded"} · {event.performed_by}
                    </p>
                    <time>{new Date(event.created_at).toLocaleString()}</time>
                  </div>
                </div>
              ))}
            </div>
          </article>
          <aside className="detail-card facts">
            <h3>Details</h3>
            <dl>
              <dt>Status</dt>
              <dd>{item.status.replace("_", " ")}</dd>
              <dt>Assigned to</dt>
              <dd>
                <select
                  className="assignment-select"
                  disabled={assigning || !agents.data}
                  value={item.assigned_to_id || ""}
                  onChange={(event) => updateAssignee(event.target.value)}
                >
                  <option value="">Unassigned</option>
                  {agents.data?.map((agent) => (
                    <option value={agent.id} key={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </dd>
              <dt>Customer</dt>
              <dd>{item.customer_name}</dd>
              <dt>Last updated</dt>
              <dd>{new Date(item.updated_at).toLocaleString()}</dd>
            </dl>
          </aside>
        </div>
      </main>
    </>
  );
}
function Customers() {
  const [search, setSearch] = useState("");
  const customers = useApi(`/customers?q=${encodeURIComponent(search)}`);
  return (
    <>
      <Header />
      <main className="shell">
        <div className="page-heading">
          <div>
            <span className="eyebrow">DIRECTORY</span>
            <h1>Customers</h1>
            <p className="lede">Search customer history and active work.</p>
          </div>
        </div>
        <div className="search-control wide-search">
          <Search size={17} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by customer name..."
          />
        </div>
        <div className="customer-grid">
          {customers.data?.map((customer) => (
            <div className="customer-card" key={customer.id}>
              <div className="customer-avatar">
                {customer.name
                  .split(" ")
                  .map((x) => x[0])
                  .join("")}
              </div>
              <div>
                <h3>{customer.name}</h3>
                <p>{customer.email}</p>
                <span>{customer.department}</span>
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Queue />} />
      <Route path="/tickets/:id" element={<TicketDetail />} />
      <Route path="/customers" element={<Customers />} />
    </Routes>
  );
}

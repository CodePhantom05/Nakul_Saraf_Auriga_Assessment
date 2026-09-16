from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("customers", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("department", sa.String(120)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("agents", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("team", sa.String(120)), sa.Column("is_active", sa.Boolean, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("tickets", sa.Column("id", sa.Integer, primary_key=True), sa.Column("ticket_number", sa.String(30), nullable=False, unique=True), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text, nullable=False), sa.Column("priority", sa.String(20), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=False), sa.Column("assigned_to_id", sa.Integer, sa.ForeignKey("agents.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True)))
    op.create_index("ix_tickets_queue", "tickets", ["status", "sla_deadline", "created_at"])
    op.create_index("ix_tickets_assignment", "tickets", ["assigned_to_id", "status"])
    op.create_index("ix_tickets_customer", "tickets", ["customer_id", "created_at"])
    op.create_table("ticket_activities", sa.Column("id", sa.Integer, primary_key=True), sa.Column("ticket_id", sa.Integer, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False), sa.Column("action", sa.String(40), nullable=False), sa.Column("old_value", sa.String(255)), sa.Column("new_value", sa.String(255)), sa.Column("performed_by", sa.String(120)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

def downgrade():
    op.drop_table("ticket_activities")
    op.drop_index("ix_tickets_customer", table_name="tickets")
    op.drop_index("ix_tickets_assignment", table_name="tickets")
    op.drop_index("ix_tickets_queue", table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("agents")
    op.drop_table("customers")

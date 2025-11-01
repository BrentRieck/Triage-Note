"""create users table

Revision ID: 20240909_0001
Revises: 
Create Date: 2024-09-09 00:00:00.000000

"""

from alembic import op

from app.models.user import User


# revision identifiers, used by Alembic.
revision = "20240909_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    User.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    User.__table__.drop(bind=bind, checkfirst=True)

"""Ensure required PostgreSQL extensions are created

This migration ensures all required PostgreSQL extensions exist.
These extensions may not have been created properly if the initial migration
ran before azure.extensions was correctly configured on Azure PostgreSQL.

Revision ID: 20260123_15
Revises: 20260120_14
Create Date: 2026-01-23

"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260123_15"
down_revision = "20260120_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create required PostgreSQL extensions if they don't exist.

    These extensions must be allowed in Azure PostgreSQL's azure.extensions
    parameter. The Bicep infrastructure configures: pg_trgm,uuid-ossp,vector

    Extensions:
    - uuid-ossp: UUID generation for primary keys
    - pg_trgm: Text similarity functions for fuzzy search
    - vector: pgvector for embedding storage and similarity search
    """
    # uuid-ossp: Required for UUID generation (uuid_generate_v4())
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # pg_trgm: Required for similarity() function used in recipe search
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # vector: Required for recipe embeddings (already in 20260120_14 but
    # ensuring it here for completeness)
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')


def downgrade() -> None:
    """Extensions are not dropped on downgrade.

    Dropping extensions could cause data loss and break other applications
    using the same database. Extensions should be managed at the infrastructure
    level.
    """
    pass

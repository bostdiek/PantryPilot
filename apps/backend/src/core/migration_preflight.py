"""Validate dev database state against the selected deployment's migration tree."""

from collections.abc import Sequence

from alembic.script import ScriptDirectory


def validate_dev_migration_state(
    scripts: ScriptDirectory,
    current_revisions: Sequence[str],
    *,
    sessions_absent: bool,
) -> None:
    """Reject unknown revisions and preserve the rollback for its original tree.

    The exact schema assertion applies only while the selected tree ends at
    20260928_20. Newer trees may upgrade recognized ancestors or redeploy their
    own revisions; Alembic remains responsible for applying those migrations.

    Raises:
        RuntimeError: The rollback state is inconsistent or the selected tree
            does not recognize the database revisions.
    """
    revisions = set(current_revisions)
    if set(scripts.get_heads()) == {"20260928_20"}:
        if revisions != {"20260928_20"} or not sessions_absent:
            raise RuntimeError(
                "Hosting-only deployment requires revision 20260928_20 "
                "and no auth_sessions table"
            )
        return

    known_revisions = {revision.revision for revision in scripts.walk_revisions()}
    if not revisions or not revisions <= known_revisions:
        raise RuntimeError(
            "The selected ref's migration graph does not recognize "
            f"the database revisions: {sorted(revisions)}"
        )

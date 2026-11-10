"""Regression tests for selected-ref dev migration validation."""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from core.migration_preflight import validate_dev_migration_state


def _migration_tree(tmp_path: Path, head: str) -> ScriptDirectory:
    versions = tmp_path / "versions"
    versions.mkdir()
    revisions = [("20260928_19", None), ("20260928_20", "20260928_19")]
    if head != "20260928_20":
        revisions.append((head, "20260928_20"))
    for revision, parent in revisions:
        (versions / f"{revision}.py").write_text(
            f"revision = {revision!r}\ndown_revision = {parent!r}\n"
        )
    return ScriptDirectory(str(tmp_path))


def test_given_rollback_tree_when_schema_matches_then_accepts(tmp_path: Path) -> None:
    scripts = _migration_tree(tmp_path, "20260928_20")

    validate_dev_migration_state(scripts, ["20260928_20"], sessions_absent=True)


@pytest.mark.parametrize(
    ("revisions", "sessions_absent"),
    [
        (["20260928_20"], False),
        (["20260928_19"], True),
        (["20261109_22"], True),
        ([], True),
    ],
)
def test_given_rollback_tree_when_schema_differs_then_rejects(
    tmp_path: Path, revisions: list[str], sessions_absent: bool
) -> None:
    scripts = _migration_tree(tmp_path, "20260928_20")

    with pytest.raises(RuntimeError, match="Hosting-only deployment requires"):
        validate_dev_migration_state(
            scripts, revisions, sessions_absent=sessions_absent
        )


@pytest.mark.parametrize("revision", ["20260928_19", "20260928_20", "20261109_22"])
def test_given_unrelated_new_migration_when_revision_known_then_accepts(
    tmp_path: Path, revision: str
) -> None:
    scripts = _migration_tree(tmp_path, "20261109_22")

    validate_dev_migration_state(scripts, [revision], sessions_absent=True)


@pytest.mark.parametrize("sessions_absent", [True, False])
def test_given_session_tree_when_revision_known_then_leaves_schema_to_alembic(
    tmp_path: Path, sessions_absent: bool
) -> None:
    scripts = _migration_tree(tmp_path, "20261021_21")

    validate_dev_migration_state(
        scripts, ["20261021_21"], sessions_absent=sessions_absent
    )


@pytest.mark.parametrize("revisions", [[], ["unknown"], ["20260928_20", "unknown"]])
def test_given_newer_tree_when_revision_unknown_then_rejects(
    tmp_path: Path, revisions: list[str]
) -> None:
    scripts = _migration_tree(tmp_path, "20261109_22")

    with pytest.raises(RuntimeError, match="migration graph does not recognize"):
        validate_dev_migration_state(scripts, revisions, sessions_absent=True)


def test_given_selected_ref_when_rollback_matches_then_accepts_real_graph() -> None:
    config = Config(str(Path(__file__).parents[1] / "src" / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    validate_dev_migration_state(scripts, ["20260928_20"], sessions_absent=True)

"""Regression checks for migration-first production publication."""

from pathlib import Path

import pytest
import yaml


WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/deploy-prod.yml"


@pytest.mark.parametrize(
    "publication_job",
    ["deploy-infrastructure", "update-container-app", "deploy-frontend"],
)
@pytest.mark.parametrize("migration_result", ["failure", "cancelled", "skipped"])
def test_given_unsuccessful_migration_then_no_publication_path(
    publication_job: str, migration_result: str
) -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    jobs = workflow["jobs"]
    outcomes = {
        "determine-deploy-trigger": "success",
        "run-migrations": migration_result,
    }
    pending = set(jobs) - outcomes.keys()
    while pending:
        ready = []
        for name in pending:
            needs = jobs[name].get("needs", [])
            dependencies = [needs] if isinstance(needs, str) else needs
            if all(dependency in outcomes for dependency in dependencies):
                assert "if" not in jobs[name], (
                    "Publication must use default success gate"
                )
                outcomes[name] = (
                    "success"
                    if all(
                        outcomes[dependency] == "success" for dependency in dependencies
                    )
                    else "skipped"
                )
                ready.append(name)
        assert ready, "Deployment dependencies must be acyclic"
        pending.difference_update(ready)
    assert outcomes[publication_job] == "skipped"


def test_given_migration_gate_then_existing_vault_and_trigger_are_preserved() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    jobs = workflow["jobs"]
    migration = jobs["run-migrations"]
    assert migration["needs"] == "determine-deploy-trigger"
    assert jobs["deploy-infrastructure"]["needs"] == "run-migrations"
    assert "workflow_dispatch" in migration["if"]
    assert "workflow_run.conclusion == 'success'" in migration["if"]
    assert "should-deploy-on-push == 'true'" in migration["if"]
    assert migration["environment"] == "prod"
    assert migration["permissions"]["id-token"] == "write"
    secret_step = next(
        step for step in migration["steps"] if step.get("id") == "secrets"
    )
    assert (
        '--vault-name "ppkv${DEPLOY_ENV}${AZURE_UNIQUE_SUFFIX}"' in secret_step["run"]
    )
    assert "::add-mask::$DB_CONNECTION" in secret_step["run"]
    assert "needs.deploy-infrastructure" not in secret_step["run"]
    assert workflow["env"]["AZURE_UNIQUE_SUFFIX"] == "prod001"
    assert any("upgrade head" in step.get("run", "") for step in migration["steps"])

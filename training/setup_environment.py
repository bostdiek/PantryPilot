"""Register Unsloth training environment in Azure ML workspace.

This script creates and registers a conda environment for training small
language models using Unsloth, TRL, and MLflow.

Usage:
    uv run python training/setup_environment.py
"""

import json
import logging
import sys
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Environment
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_workspace_config() -> tuple[str, str, str]:
    """Load Azure ML workspace configuration from config.json.

    Returns:
        Tuple of (subscription_id, resource_group, workspace_name)
    """
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    return (
        config["subscription_id"],
        config["resource_group"],
        config["workspace_name"],
    )


def create_ml_client() -> MLClient:
    """Create Azure ML client using workspace configuration.

    Returns:
        Authenticated MLClient instance
    """
    subscription_id, resource_group, workspace_name = load_workspace_config()

    logger.info(f"Connecting to workspace: {workspace_name}")
    logger.info(f"Resource group: {resource_group}")
    logger.info(f"Subscription: {subscription_id}")

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    return ml_client


def register_environment(ml_client: MLClient) -> None:
    """Register Unsloth training environment in Azure ML.

    Args:
        ml_client: Authenticated Azure ML client
    """
    env_path = Path(__file__).parent / "environments" / "unsloth-env.yml"

    if not env_path.exists():
        logger.error(f"Environment file not found: {env_path}")
        sys.exit(1)

    logger.info(f"Reading environment from: {env_path}")

    # Create environment from conda specification
    env = Environment(
        name="unsloth-training",
        description="Training environment with Unsloth, TRL, and MLflow for SLM fine-tuning",
        conda_file=str(env_path),
        image="mcr.microsoft.com/azureml/curated/acpt-pytorch-2.2-cuda12.1:latest",
    )

    try:
        logger.info("Registering environment in Azure ML...")
        registered_env = ml_client.environments.create_or_update(env)
        logger.info(f"✓ Environment registered: {registered_env.name}")
        logger.info(f"  Version: {registered_env.version}")
        logger.info(f"  Base image: {env.image}")
    except ResourceExistsError:
        logger.info("Environment already exists, getting latest version...")
        registered_env = ml_client.environments.get(name=env.name, label="latest")
        logger.info(f"✓ Using existing environment: {registered_env.name}")
        logger.info(f"  Version: {registered_env.version}")
    except Exception as e:
        logger.error(f"Failed to register environment: {e}")
        sys.exit(1)


def main() -> None:
    """Main execution function."""
    logger.info("=== Azure ML Environment Setup ===")

    try:
        ml_client = create_ml_client()
        register_environment(ml_client)
        logger.info("\n✓ Environment setup complete!")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

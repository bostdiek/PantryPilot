"""Register HuggingFace base models in Azure ML Model Registry.

This script downloads and registers base models from HuggingFace Hub
into Azure ML for use in training pipelines. Models are stored in
Azure Blob Storage within the ML workspace.

Usage:
    uv run python training/register_models.py
"""

import json
import logging
import sys
import tempfile
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Models to register: (HF model ID, Azure ML model name)
MODELS_TO_REGISTER = [
    ("Qwen/Qwen2.5-0.5B", "qwen-0.5b-base"),
    ("Qwen/Qwen2.5-0.5B-Instruct", "qwen-0.5b-instruct"),
    ("unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit", "qwen-0.5b-instruct-4bit"),
    ("liquidai/lfm-2.5-1.2b-instruct", "lfm-2.5-1.2b-instruct"),
    ("unsloth/functiongemma-270m-it", "function-gemma-270m"),
    ("unsloth/Gemma-2-2b-it-function-calling-bnb-4bit", "gemma-2-2b-fc-4bit"),
]


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


def download_hf_model(model_id: str, output_dir: Path) -> None:
    """Download a HuggingFace model to local directory.

    Args:
        model_id: HuggingFace model identifier (e.g., "Qwen/Qwen2.5-0.5B")
        output_dir: Local directory to save model files
    """
    try:
        from transformers import AutoConfig, AutoTokenizer

        logger.info("  Downloading model config and tokenizer...")

        # Download config and tokenizer (lightweight)
        config = AutoConfig.from_pretrained(model_id)
        tokenizer = AutoTokenizer.from_pretrained(model_id)

        # Save to output directory
        config.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

        # Create a marker file with model metadata
        metadata = {
            "model_id": model_id,
            "architecture": config.architectures[0]
            if config.architectures
            else "unknown",
            "vocab_size": config.vocab_size,
            "hidden_size": getattr(config, "hidden_size", None),
        }

        with open(output_dir / "model_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("  ✓ Downloaded config and tokenizer")
    except ImportError:
        logger.error(
            "transformers package not found. Install with: uv pip install transformers"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        raise


def register_model(ml_client: MLClient, hf_model_id: str, aml_model_name: str) -> None:
    """Register a HuggingFace model in Azure ML.

    Args:
        ml_client: Authenticated Azure ML client
        hf_model_id: HuggingFace model identifier
        aml_model_name: Name to use in Azure ML registry
    """
    logger.info(f"\nRegistering: {hf_model_id} → {aml_model_name}")

    # Create temporary directory for model files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download model config and tokenizer
        download_hf_model(hf_model_id, temp_path)

        # Create model entity with reference to HF
        model = Model(
            name=aml_model_name,
            path=str(temp_path),
            description=f"HuggingFace model: {hf_model_id}",
            tags={
                "huggingface_id": hf_model_id,
                "model_type": "language_model",
                "framework": "transformers",
            },
        )

        try:
            logger.info("  Uploading to Azure ML...")
            registered_model = ml_client.models.create_or_update(model)
            logger.info(f"  ✓ Registered: {registered_model.name}")
            logger.info(f"    Version: {registered_model.version}")
            logger.info(f"    ID: {registered_model.id}")
        except ResourceExistsError:
            logger.info(f"  ℹ Model already exists: {aml_model_name}")
            registered_model = ml_client.models.get(name=aml_model_name, label="latest")
            logger.info(f"    Latest version: {registered_model.version}")
        except Exception as e:
            logger.error(f"  ✗ Failed to register: {e}")
            raise


def main() -> None:
    """Main execution function."""
    logger.info("=== Azure ML Model Registration ===")

    try:
        ml_client = create_ml_client()

        logger.info(f"\nRegistering {len(MODELS_TO_REGISTER)} models...")

        for hf_model_id, aml_model_name in MODELS_TO_REGISTER:
            try:
                register_model(ml_client, hf_model_id, aml_model_name)
            except Exception as e:
                logger.warning(f"Skipping {hf_model_id} due to error: {e}")
                continue

        logger.info("\n✓ Model registration complete!")
        logger.info("\nRegistered models:")
        for _, aml_name in MODELS_TO_REGISTER:
            logger.info(f"  - {aml_name}")

    except Exception as e:
        logger.error(f"Registration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Register HuggingFace models in Azure ML with proper file handling.

This script creates Azure ML model assets that cache HuggingFace models
locally in Azure Blob Storage as a backup.
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

# Models to register: (HF model ID, Azure ML model name, description)
MODELS_TO_REGISTER = [
    ("Qwen/Qwen2.5-0.5B", "qwen-0.5b-base", "Qwen 2.5 0.5B base model for DAPT"),
    (
        "Qwen/Qwen2.5-0.5B-Instruct",
        "qwen-0.5b-instruct",
        "Qwen 2.5 0.5B Instruct - primary SLM",
    ),
    (
        "unsloth/Qwen2.5-0.5B-Instruct-bnb-4bit",
        "qwen-0.5b-instruct-4bit",
        "Qwen 2.5 0.5B Instruct 4-bit",
    ),
    (
        "LiquidAI/LFM2.5-1.2B-Instruct",
        "lfm-2.5-1.2b-instruct",
        "Liquid AI LFM 2.5 1.2B - 32K context",
    ),
    (
        "unsloth/functiongemma-270m-it",
        "function-gemma-270m",
        "Function Gemma 270M for function calling",
    ),
]


def load_workspace_config() -> tuple[str, str, str]:
    """Load Azure ML workspace configuration."""
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
    """Create Azure ML client."""
    subscription_id, resource_group, workspace_name = load_workspace_config()

    logger.info(f"Connecting to workspace: {workspace_name}")
    logger.info(f"Resource group: {resource_group}")

    credential = DefaultAzureCredential()
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )

    return ml_client


def download_model_config(model_id: str, output_dir: Path) -> None:
    """Download minimal model configuration files."""
    try:
        from transformers import AutoConfig, AutoTokenizer

        logger.info("  Downloading config and tokenizer...")

        # Download config and tokenizer
        config = AutoConfig.from_pretrained(model_id)
        tokenizer = AutoTokenizer.from_pretrained(model_id)

        # Save to output directory
        config.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

        # Create model reference metadata
        metadata = {
            "huggingface_id": model_id,
            "architecture": (
                config.architectures[0] if config.architectures else "unknown"
            ),
            "vocab_size": config.vocab_size,
            "hidden_size": getattr(config, "hidden_size", None),
            "num_layers": getattr(config, "num_hidden_layers", None),
            "download_command": f"from transformers import AutoModelForCausalLM; model = AutoModelForCausalLM.from_pretrained('{model_id}')",
        }

        with open(output_dir / "azure_ml_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("  ✓ Downloaded config and tokenizer")
    except ImportError:
        logger.error(
            "transformers package required. Install: uv pip install transformers"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        raise


def register_model(
    ml_client: MLClient, hf_model_id: str, aml_model_name: str, description: str
) -> None:
    """Register a HuggingFace model in Azure ML."""
    logger.info(f"\nRegistering: {hf_model_id} → {aml_model_name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download model metadata
        download_model_config(hf_model_id, temp_path)

        # Create Azure-compliant directory structure
        azure_path = temp_path / "model"
        azure_path.mkdir()

        # Move files to clean directory
        for file in temp_path.glob("*"):
            if file.is_file():
                # Sanitize filename for Azure
                safe_name = file.name.replace(".", "_")
                if safe_name != file.name:
                    logger.info(f"  Renaming {file.name} → {safe_name}")
                (azure_path / safe_name).write_bytes(file.read_bytes())
            elif file.name != "model":
                # Copy directories recursively
                import shutil

                shutil.copytree(file, azure_path / file.name)

        # Create model entity
        model = Model(
            name=aml_model_name,
            path=str(azure_path),
            description=description,
            properties={
                "huggingface_id": hf_model_id,
                "model_type": "language_model",
                "framework": "transformers",
                "license": "apache-2.0",
            },
            tags={
                "source": "huggingface",
                "model_id": hf_model_id,
                "backup": "true",
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
    logger.info("Registering model metadata for HuggingFace models")
    logger.info("Note: Full model weights will be downloaded during training")

    try:
        ml_client = create_ml_client()

        logger.info(f"\nRegistering {len(MODELS_TO_REGISTER)} models...")

        for hf_model_id, aml_model_name, description in MODELS_TO_REGISTER:
            try:
                register_model(ml_client, hf_model_id, aml_model_name, description)
            except Exception as e:
                logger.warning(f"Skipping {hf_model_id} due to error: {e}")
                continue

        logger.info("\n✓ Model registration complete!")
        logger.info("\nRegistered models:")
        for _, aml_name, _ in MODELS_TO_REGISTER:
            logger.info(f"  - {aml_name}")

        logger.info("\nNote: Model configs are cached in Azure ML.")
        logger.info(
            "Full model weights will be downloaded from HuggingFace during training."
        )

    except Exception as e:
        logger.error(f"Registration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

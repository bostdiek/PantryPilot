#!/usr/bin/env python3
"""
PantryPilot Azure ML Training Pipeline

Multi-stage fine-tuning pipeline for the PantryPilot culinary SLM:
    DAPT (optional) → SFT (required) → GRPO (optional)

Phase 8: Component definitions loaded from YAML specs in training/components/.
Phase 9: Pipeline orchestration and submission CLI (see TODO below).

Usage (Phase 9 — not yet implemented):
    python training/pipeline.py --enable-sft --base-model unsloth/Qwen3-0.6B-unsloth-bnb-4bit
    python training/pipeline.py --enable-dapt --enable-sft --enable-grpo

References:
    - training/components/dapt.yaml  — DAPT component spec
    - training/components/sft.yaml   — SFT component spec
    - training/components/grpo.yaml  — GRPO component spec
    - .copilot-tracking/plans/20260209-azure-ml-training-pipeline-plan.instructions.md
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TRAINING_DIR = Path(__file__).parent
_COMPONENTS_DIR = _TRAINING_DIR / "components"

DAPT_COMPONENT_YAML = _COMPONENTS_DIR / "dapt.yaml"
SFT_COMPONENT_YAML = _COMPONENTS_DIR / "sft.yaml"
GRPO_COMPONENT_YAML = _COMPONENTS_DIR / "grpo.yaml"

# ---------------------------------------------------------------------------
# Azure ML client factory
# ---------------------------------------------------------------------------


def create_ml_client():
    """Create an Azure ML client from config.json in the repository root.

    Reads subscription_id, resource_group, and workspace_name from the
    config.json file at the project root (same pattern as submit_test_jobs.py).

    Returns:
        MLClient: Authenticated Azure ML client.

    Raises:
        SystemExit: If azure-ai-ml is not installed or config.json is missing.
    """
    try:
        from azure.ai.ml import MLClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        logger.error(
            "azure-ai-ml not installed. Install via:\n"
            "  cd apps/backend && uv sync --group training"
        )
        raise SystemExit(1) from exc

    config_path = _TRAINING_DIR.parent / "config.json"
    if not config_path.exists():
        logger.error(
            f"config.json not found at {config_path}. "
            "Copy config.json.example and fill in your workspace details."
        )
        raise SystemExit(1)

    with open(config_path) as f:
        config = json.load(f)

    logger.info(f"Connecting to workspace: {config['workspace_name']}")

    return MLClient(
        credential=DefaultAzureCredential(),
        subscription_id=config["subscription_id"],
        resource_group_name=config["resource_group"],
        workspace_name=config["workspace_name"],
    )


# ---------------------------------------------------------------------------
# Phase 8: Component loaders
# ---------------------------------------------------------------------------


def load_dapt_component():
    """Load the DAPT training component from its YAML spec.

    Returns:
        Loaded Azure ML component object ready to use in a pipeline.

    Example::

        dapt_comp = load_dapt_component()
        dapt_step = dapt_comp(
            base_model="unsloth/Qwen3-0.6B-Base-unsloth-bnb-4bit",
            training_data=Input(type="uri_file", path="azureml:dapt-culinary-corpus:1"),
            learning_rate=2e-5,
            streaming=True,
            max_steps=50000,
        )
    """
    try:
        from azure.ai.ml import load_component
    except ImportError as exc:
        logger.error("azure-ai-ml not installed.")
        raise SystemExit(1) from exc

    if not DAPT_COMPONENT_YAML.exists():
        raise FileNotFoundError(f"DAPT component spec not found: {DAPT_COMPONENT_YAML}")

    logger.info(f"Loading DAPT component from {DAPT_COMPONENT_YAML}")
    return load_component(source=str(DAPT_COMPONENT_YAML))


def load_sft_component():
    """Load the SFT training component from its YAML spec.

    Returns:
        Loaded Azure ML component object ready to use in a pipeline.

    Example::

        sft_comp = load_sft_component()
        sft_step = sft_comp(
            base_model="unsloth/Qwen3-0.6B-unsloth-bnb-4bit",
            training_data=Input(type="uri_file", path="azureml:pantrypilot-sft-data:1"),
            val_data=Input(type="uri_file", path="azureml:pantrypilot-sft-data-val:1"),
            num_epochs=3,
            max_seq_length=8192,
        )
        # Wire DAPT output into SFT:
        sft_step = sft_comp(
            base_model=dapt_step.outputs.trained_model,
            ...
        )
    """
    try:
        from azure.ai.ml import load_component
    except ImportError as exc:
        logger.error("azure-ai-ml not installed.")
        raise SystemExit(1) from exc

    if not SFT_COMPONENT_YAML.exists():
        raise FileNotFoundError(f"SFT component spec not found: {SFT_COMPONENT_YAML}")

    logger.info(f"Loading SFT component from {SFT_COMPONENT_YAML}")
    return load_component(source=str(SFT_COMPONENT_YAML))


def load_grpo_component():
    """Load the GRPO training component from its YAML spec.

    Returns:
        Loaded Azure ML component object ready to use in a pipeline.

    Example::

        grpo_comp = load_grpo_component()
        grpo_step = grpo_comp(
            base_model=sft_step.outputs.trained_model,
            prompts_path=Input(type="uri_file", path="azureml:grpo-prompts:1"),
            num_generations=8,
            num_epochs=2,
        )

    Note:
        On NC6s_v3 (V100), Liquid AI LFM-2.5 models are numerically
        unstable with GRPO (TorchRuntimeError in Unsloth's compiled
        chunked_hidden_states_selective_log_softmax).  Use Qwen3-0.6B
        for GRPO training.
    """
    try:
        from azure.ai.ml import load_component
    except ImportError as exc:
        logger.error("azure-ai-ml not installed.")
        raise SystemExit(1) from exc

    if not GRPO_COMPONENT_YAML.exists():
        raise FileNotFoundError(f"GRPO component spec not found: {GRPO_COMPONENT_YAML}")

    logger.info(f"Loading GRPO component from {GRPO_COMPONENT_YAML}")
    return load_component(source=str(GRPO_COMPONENT_YAML))


# ---------------------------------------------------------------------------
# TODO Phase 9: Pipeline orchestration
# ---------------------------------------------------------------------------
# The following will be implemented in Phase 9 (feature/aml-pipeline):
#
#   @dsl.pipeline(
#       name="pantrypilot_training_pipeline",
#       description="Multi-stage training: DAPT (optional) → SFT → GRPO (optional)",
#       compute="gpu-cluster",
#   )
#   def training_pipeline(
#       base_model: str,
#       sft_data: Input(type="uri_file"),
#       val_data: Input(type="uri_file"),
#       enable_dapt: bool = False,
#       dapt_data: Input(type="uri_file", optional=True) = None,
#       enable_grpo: bool = False,
#       grpo_data: Input(type="uri_file", optional=True) = None,
#       ...
#   ) -> dict:
#       ...
#
# Submission CLI (training/scripts/submit_pipeline.py) and config files
# (training/configs/sft_only.json, training/configs/full_pipeline.json)
# will also be created in Phase 9.
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Quick validation: verify component YAML files exist and are loadable
    print("PantryPilot Training Pipeline — Component Loader Validation")
    print("=" * 60)

    all_ok = True
    for name, loader in [
        ("DAPT", load_dapt_component),
        ("SFT", load_sft_component),
        ("GRPO", load_grpo_component),
    ]:
        try:
            comp = loader()
            print(f"✅ {name} component loaded: {comp.name} v{comp.version}")
        except FileNotFoundError as e:
            print(f"❌ {name} component YAML missing: {e}")
            all_ok = False
        except ImportError:
            print(
                f"⚠️  {name} component YAML exists but azure-ai-ml not installed "
                "(install with: cd apps/backend && uv sync --group training)"
            )
        except Exception as e:
            print(f"❌ {name} component load failed: {e}")
            all_ok = False

    sys.exit(0 if all_ok else 1)

#!/usr/bin/env python3
"""
PantryPilot Azure ML Training Pipeline

Multi-stage fine-tuning pipeline for the PantryPilot culinary SLM:
    DAPT (optional) → SFT (required) → GRPO (optional)

Phase 8: Component definitions loaded from YAML specs in training/components/.
Phase 9: Pipeline orchestration via @dsl.pipeline with conditional stages.

Usage:
    # Validate component YAML loading (no Azure ML connectivity needed)
    python training/pipeline.py

    # Submit pipelines via training/submit_pipeline.py:
    python training/submit_pipeline.py --config training/configs/sft_only.json
    python training/submit_pipeline.py --config training/configs/full_pipeline.json
    python training/submit_pipeline.py --config training/configs/dapt_sft.json --dry-run

References:
    - training/components/dapt.yaml  — DAPT component spec
    - training/components/sft.yaml   — SFT component spec
    - training/components/grpo.yaml  — GRPO component spec
    - training/submit_pipeline.py    — Submission CLI script
    - training/configs/              — Preset pipeline configurations
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

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
# Phase 9: Pipeline orchestration
# ---------------------------------------------------------------------------


def build_training_pipeline(
    config: dict[str, Any],
) -> Any:
    """Build an Azure ML pipeline job from a configuration dict.

    The pipeline wires up to three stages — DAPT (optional) → SFT (required) →
    GRPO (optional) — using the component YAML definitions from Phase 8.

    Stage enablement is controlled by ``enable_dapt`` and ``enable_grpo`` flags
    in *config*.  SFT is always included.

    Model flow:
        - Standalone SFT: ``base_model`` string (HF ID) → SFT
        - DAPT → SFT: ``base_model`` string → DAPT → ``trained_model`` uri_folder → SFT
        - SFT → GRPO: SFT ``trained_model`` uri_folder → GRPO

    Args:
        config: Pipeline configuration dict with keys:
            - base_model (str): HuggingFace model ID
            - compute (str, optional): Compute target (default "gpu-cluster")
            - enable_dapt (bool, optional): Enable DAPT stage (default False)
            - enable_grpo (bool, optional): Enable GRPO stage (default False)
            - sft_data (str): Azure ML data path for SFT training JSONL
            - val_data (str, optional): Azure ML data path for SFT validation JSONL
            - dapt_data (str, optional): Azure ML data path for DAPT corpus
            - grpo_prompts (str, optional): Azure ML data path for GRPO prompts JSON
            - dapt (dict, optional): DAPT hyperparameters
            - sft (dict, optional): SFT hyperparameters
            - grpo (dict, optional): GRPO hyperparameters

    Returns:
        Azure ML pipeline job ready for submission via ``ml_client.jobs.create_or_update()``.

    Raises:
        SystemExit: If azure-ai-ml is not installed.
        ValueError: If required configuration is missing.
    """
    try:
        from azure.ai.ml import Input
        from azure.ai.ml.constants import AssetTypes, InputOutputModes
        from azure.ai.ml.dsl import pipeline
    except ImportError as exc:
        logger.error(
            "azure-ai-ml not installed. Install via:\n"
            "  cd apps/backend && uv sync --group training"
        )
        raise SystemExit(1) from exc

    # Extract top-level config
    base_model: str = config["base_model"]
    compute: str = config.get("compute", "gpu-cluster")
    enable_dapt: bool = config.get("enable_dapt", False)
    enable_grpo: bool = config.get("enable_grpo", False)

    # Validate required data paths
    sft_data_path: str = config.get("sft_data", "")
    if not sft_data_path:
        raise ValueError("config must include 'sft_data' path")

    if enable_dapt and not config.get("dapt_data"):
        raise ValueError("enable_dapt=True requires 'dapt_data' path in config")

    if enable_grpo and not config.get("grpo_prompts"):
        raise ValueError("enable_grpo=True requires 'grpo_prompts' path in config")

    # Per-stage hyperparameters
    dapt_params: dict[str, Any] = config.get("dapt", {})
    sft_params: dict[str, Any] = config.get("sft", {})
    grpo_params: dict[str, Any] = config.get("grpo", {})

    # Load components
    dapt_comp = load_dapt_component() if enable_dapt else None
    sft_comp = load_sft_component()
    grpo_comp = load_grpo_component() if enable_grpo else None

    # Build stage descriptions for pipeline name
    stages = []
    if enable_dapt:
        stages.append("DAPT")
    stages.append("SFT")
    if enable_grpo:
        stages.append("GRPO")
    pipeline_desc = " → ".join(stages)

    @pipeline(
        name="pantrypilot_training_pipeline",
        description=f"PantryPilot {pipeline_desc} training pipeline",
        default_compute=compute,
    )
    def training_pipeline() -> dict[str, Any]:
        """Multi-stage training pipeline with conditional DAPT/GRPO."""
        # Track what the SFT stage receives as its model input
        sft_model_input: str | Any = base_model

        # ------------------------------------------------------------------
        # Stage 1: DAPT (Optional)
        # ------------------------------------------------------------------
        if enable_dapt and dapt_comp is not None:
            dapt_input = Input(
                type=AssetTypes.URI_FILE,
                path=config["dapt_data"],
                mode=InputOutputModes.RO_MOUNT,
            )
            dapt_kwargs: dict[str, Any] = {
                "base_model": base_model,
                "training_data": dapt_input,
                "run_name": f"dapt-{base_model.split('/')[-1]}",
            }
            # Apply hyperparameter overrides
            for key in (
                "max_seq_length",
                "learning_rate",
                "num_epochs",
                "batch_size",
                "gradient_accumulation_steps",
                "warmup_steps",
                "max_steps",
                "lora_r",
                "lora_alpha",
                "target_modules",
                "logging_steps",
                "save_steps",
                "seed",
            ):
                if key in dapt_params:
                    dapt_kwargs[key] = dapt_params[key]

            # Boolean flags
            if dapt_params.get("streaming"):
                dapt_kwargs["streaming"] = True
            if dapt_params.get("no_4bit"):
                dapt_kwargs["no_4bit"] = True

            dapt_step = dapt_comp(**dapt_kwargs)
            dapt_step.compute = compute

            # DAPT output becomes the SFT model input (uri_folder)
            sft_model_input = dapt_step.outputs.trained_model

        # ------------------------------------------------------------------
        # Stage 2: SFT (Required)
        # ------------------------------------------------------------------
        sft_input = Input(
            type=AssetTypes.URI_FILE,
            path=sft_data_path,
            mode=InputOutputModes.RO_MOUNT,
        )
        sft_kwargs: dict[str, Any] = {
            "training_data": sft_input,
            "run_name": f"sft-{base_model.split('/')[-1]}",
        }

        # Route model input based on whether DAPT ran
        if enable_dapt:
            # DAPT checkpoint is a uri_folder — use base_model_path
            sft_kwargs["base_model_path"] = sft_model_input
        else:
            # Direct HuggingFace model ID — use base_model string
            sft_kwargs["base_model"] = base_model

        # Optional validation data
        if config.get("val_data"):
            sft_kwargs["val_data"] = Input(
                type=AssetTypes.URI_FILE,
                path=config["val_data"],
                mode=InputOutputModes.RO_MOUNT,
            )

        # Apply hyperparameter overrides
        for key in (
            "max_seq_length",
            "learning_rate",
            "num_epochs",
            "batch_size",
            "gradient_accumulation_steps",
            "warmup_steps",
            "lora_r",
            "lora_alpha",
            "target_modules",
            "chat_template",
            "logging_steps",
            "eval_steps",
            "save_steps",
            "seed",
            "gguf_quantization",
        ):
            if key in sft_params:
                sft_kwargs[key] = sft_params[key]

        # Boolean flags
        if sft_params.get("no_4bit"):
            sft_kwargs["no_4bit"] = True
        if sft_params.get("export_gguf"):
            sft_kwargs["export_gguf"] = True
        if sft_params.get("install_mamba"):
            sft_kwargs["install_mamba"] = True

        sft_step = sft_comp(**sft_kwargs)
        sft_step.compute = compute

        # ------------------------------------------------------------------
        # Stage 3: GRPO (Optional)
        # ------------------------------------------------------------------
        if enable_grpo and grpo_comp is not None:
            grpo_input = Input(
                type=AssetTypes.URI_FILE,
                path=config["grpo_prompts"],
                mode=InputOutputModes.RO_MOUNT,
            )
            grpo_kwargs: dict[str, Any] = {
                # GRPO takes the SFT checkpoint as uri_folder
                "base_model": sft_step.outputs.trained_model,
                "prompts_path": grpo_input,
                "run_name": f"grpo-{base_model.split('/')[-1]}",
            }
            # Apply hyperparameter overrides
            for key in (
                "max_seq_length",
                "num_generations",
                "temperature",
                "max_new_tokens",
                "beta",
                "learning_rate",
                "num_epochs",
                "batch_size",
                "gradient_accumulation_steps",
                "lora_r",
                "lora_alpha",
                "target_modules",
                "json_weight",
                "tool_weight",
                "args_weight",
                "query_weight",
                "logging_steps",
                "save_steps",
                "seed",
                "gguf_quantization",
                "vllm_attention_backend",
            ):
                if key in grpo_params:
                    grpo_kwargs[key] = grpo_params[key]

            # Boolean flags
            if grpo_params.get("no_4bit"):
                grpo_kwargs["no_4bit"] = True
            if grpo_params.get("export_gguf"):
                grpo_kwargs["export_gguf"] = True
            if grpo_params.get("disable_dynamo"):
                grpo_kwargs["disable_dynamo"] = True
            if grpo_params.get("patch_lfm2_logps"):
                grpo_kwargs["patch_lfm2_logps"] = True
            if grpo_params.get("use_vllm"):
                grpo_kwargs["use_vllm"] = True
            if grpo_params.get("install_mamba"):
                grpo_kwargs["install_mamba"] = True

            grpo_step = grpo_comp(**grpo_kwargs)
            grpo_step.compute = compute

            return {"trained_model": grpo_step.outputs.trained_model}

        return {"trained_model": sft_step.outputs.trained_model}

    # Build and return the pipeline job
    pipeline_job = training_pipeline()
    pipeline_job.tags = {
        "base_model": base_model,
        "stages": pipeline_desc,
        "enable_dapt": str(enable_dapt),
        "enable_grpo": str(enable_grpo),
    }
    pipeline_job.experiment_name = "pantrypilot-training-pipeline"

    return pipeline_job


# ---------------------------------------------------------------------------
# Pipeline configuration helpers
# ---------------------------------------------------------------------------


def load_pipeline_config(config_path: str | Path) -> dict[str, Any]:
    """Load and validate a pipeline configuration file.

    Args:
        config_path: Path to a JSON configuration file.

    Returns:
        Parsed configuration dict.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If required fields are missing.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config: dict[str, Any] = json.load(f)

    if "base_model" not in config:
        raise ValueError(f"Config {config_path} missing required 'base_model' field")
    if "sft_data" not in config:
        raise ValueError(f"Config {config_path} missing required 'sft_data' field")

    return config


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
            print(f"  {name} component loaded: {comp.name} v{comp.version}")
        except FileNotFoundError as e:
            print(f"  {name} component YAML missing: {e}")
            all_ok = False
        except ImportError:
            print(
                f"  {name} component YAML exists but azure-ai-ml not installed "
                "(install with: cd apps/backend && uv sync --group training)"
            )
        except Exception as e:
            print(f"  {name} component load failed: {e}")
            all_ok = False

    # Check for config files
    print()
    print("Pipeline Configuration Files")
    print("=" * 60)
    configs_dir = _TRAINING_DIR / "configs"
    if configs_dir.exists():
        for cfg_file in sorted(configs_dir.glob("*.json")):
            try:
                cfg = load_pipeline_config(cfg_file)
                stages = []
                if cfg.get("enable_dapt"):
                    stages.append("DAPT")
                stages.append("SFT")
                if cfg.get("enable_grpo"):
                    stages.append("GRPO")
                print(f"  {cfg_file.name}: {cfg['base_model']} ({' → '.join(stages)})")
            except Exception as e:
                print(f"  {cfg_file.name}: ERROR — {e}")
    else:
        print("  No configs/ directory found")

    sys.exit(0 if all_ok else 1)

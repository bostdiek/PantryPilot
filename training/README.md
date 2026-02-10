# Azure ML Training Infrastructure

This directory contains infrastructure and scripts for training small language models (SLMs) for the PantryPilot AI agent using Azure Machine Learning.

## Workspace Configuration

- **Workspace Name**: pp-aml-dev
- **Resource Group**: rg-pantrypilot-dev
- **Subscription ID**: e341c2a7-3f10-4a7e-aa98-288584e3f57c
- **Region**: eastus2

## Compute Resources

### GPU Cluster: `gpu-cluster`

- **VM Size**: Standard_NC6s_v3
- **GPU**: NVIDIA Tesla V100 (16GB VRAM)
- **Cores**: 6
- **RAM**: 112 GB
- **Storage**: 736 GB
- **Cost**: ~$0.61/hr per node
- **Min Nodes**: 0
- **Max Nodes**: 2 (configurable)
- **Idle Scale-Down**: 10 minutes

## Training Environment

See `environments/unsloth-env.yml` for the conda environment specification used for training jobs.

Key dependencies:
- Unsloth (efficient fine-tuning with 4-bit quantization)
- TRL (Transformer Reinforcement Learning)
- MLflow (experiment tracking)
- Azure ML SDK

## Base Models

Registered models in Azure ML Model Registry:
- **Qwen/Qwen2.5-0.5B-Instruct** (primary training base - 0.5B params)
- **Qwen/Qwen2.5-0.5B** (base model for DAPT)
- **Function Gemma 270M** (tiny function-calling model - 270M params)
- **Gemma-2-2B Function Calling** (function-calling specialized - 2B params)
- **Liquid AI LFM-2.5-1.2B-Instruct** (alternative with longer context - 1.2B params)

## Setup Scripts

- `environments/unsloth-env.yml` - Training environment definition
- `setup_environment.py` - Script to register environment in Azure ML
- `register_models.py` - Script to register HuggingFace models in Azure ML

## Usage

```bash
# Set up training environment
uv run python training/setup_environment.py

# Register base models
uv run python training/register_models.py
```

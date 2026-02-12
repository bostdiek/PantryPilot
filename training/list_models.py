"""Quick script to list all models in Azure ML workspace."""

import json
import sys
from pathlib import Path

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

# Load config
config_path = Path(__file__).parent.parent / "config.json"
if not config_path.is_file():
    print(f"Error: config.json not found at {config_path}.", file=sys.stderr)
    raise SystemExit(1)
with open(config_path) as f:
    config = json.load(f)

# Create client
credential = DefaultAzureCredential()
ml_client = MLClient(
    credential=credential,
    subscription_id=config["subscription_id"],
    resource_group_name=config["resource_group"],
    workspace_name=config["workspace_name"],
)

# List all models
print("\n=== Registered Models in Azure ML ===\n")
models = ml_client.models.list()
model_dict = {}

for model in models:
    if model.name not in model_dict:
        model_dict[model.name] = []
    model_dict[model.name].append(model.version)

for name in sorted(model_dict.keys()):
    versions = sorted(model_dict[name], reverse=True)
    print(f"📦 {name}")
    print(f"   Versions: {', '.join(map(str, versions))}")
    print()

print(f"Total models: {len(model_dict)}")

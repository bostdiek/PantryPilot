# DAPT (Domain-Adaptive Pre-Training) Corpus

This directory contains scripts for preparing a commercial-use culinary corpus for domain-adaptive pre-training of language models.

## Overview

The DAPT corpus is designed for pre-training small language models (~1B parameters) on culinary domain knowledge before supervised fine-tuning on PantryPilot conversations.

## Corpus Composition

| Source | Tokens | Percentage | License |
|--------|--------|------------|---------|
| Food.com recipes | ~70M | 47% | ✅ CC0 |
| Food.com reviews | ~43M | 29% | ✅ CC0 |
| OpenRecipes | ~25M | 17% | ✅ ODC-BY |
| Co-occurrence knowledge | ~5M | 3% | ✅ Derived from CC0 |
| **Total** | **~150M** | 100% | **All Commercial** |

## Prerequisites

1. **Kaggle API credentials**: Configure `~/.kaggle/kaggle.json` with your API key
2. **Python dependencies**: Install with `uv sync` in the backend directory

## Usage

All commands should be run from the `apps/backend` directory.

### Step 1: Download Food.com Dataset

```bash
uv run python -m training.dapt.download_foodcom --output-dir ./data/foodcom
```

This downloads the Food.com dataset from Kaggle (~300MB compressed).

### Step 2: Process Food.com Data

```bash
uv run python -m training.dapt.process_foodcom \
  --input-dir ./data/foodcom \
  --output ./data/foodcom_corpus.jsonl
```

Outputs:
- `foodcom_corpus.jsonl`: JSONL with recipe text (~230K recipes)
- `foodcom_reviews.jsonl`: JSONL with substitution tips (~50K reviews)

### Step 3: Process OpenRecipes

```bash
uv run python -m training.dapt.process_openrecipes --output ./data/openrecipes_corpus.jsonl
```

### Step 4: Extract Flavor Pairing Knowledge

```bash
uv run python -m training.dapt.extract_flavor_pairs \
  --input ./data/foodcom \
  --output ./data/flavor_pairs.jsonl
```

### Step 5: Create Combined Corpus

```bash
uv run python -m training.dapt.create_corpus \
  --output ./data/commercial_culinary_corpus.jsonl
```

### Step 6: Upload to Azure

```bash
uv run python -m training.dapt.upload_to_azure \
  --corpus ./data/commercial_culinary_corpus.jsonl \
  --workspace-name pantrypilot-ml
```

## Data Format

All output files use JSONL format with a single `text` field:

```json
{"text": "# Chocolate Chip Cookies\n\nCategory: desserts, cookies\n..."}
{"text": "# Spaghetti Carbonara\n\nCategory: pasta, italian\n..."}
```

## Licenses

- **Food.com**: CC0 (Public Domain) - Free for commercial use
- **OpenRecipes**: ODC-BY (Open Data Commons Attribution) - Requires attribution
- **Derived data**: Inherits source license

## Attribution

When using this corpus, please attribute:
- Food.com data from Kaggle dataset by Shuyang Li
- OpenRecipes from the OpenRecipes project (https://github.com/fictivekin/openrecipes)

#!/bin/bash

# This script runs pytest commands using uv
cd $(dirname $0)/..
source .venv/bin/activate
python -m pytest "$@"

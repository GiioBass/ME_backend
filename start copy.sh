#!/bin/bash
echo "Starting Mystic Explorers Backend..."
cd "$(dirname "$0")"
./venv/bin/uvicorn app.main:app --reload

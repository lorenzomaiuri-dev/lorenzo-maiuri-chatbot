#!/usr/bin/env python3
"""
Exports the FastAPI OpenAPI schema to openapi.json for frontend type generation.

Usage:
    uv run scripts/export_openapi.py

On the frontend, generate TypeScript types with:
    npx openapi-typescript openapi.json -o src/types/api.ts
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Provide stub env vars so Config() doesn't raise outside a real environment
os.environ.setdefault("API_KEY", "dev")
os.environ.setdefault("GEMINI_API_KEY", "dev")

from src.app import app  # noqa: E402

output = Path("openapi.json")
output.write_text(json.dumps(app.openapi(), indent=2))
print(f"OpenAPI schema written to {output}")

import json
import os

from src.api.main import app

"""
Generates OpenAPI schema from the FastAPI app and writes it to interfaces/openapi.json.
Run this after modifying routes to keep the contract up-to-date.
"""

openapi_schema = app.openapi()

output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
    f.write("\n")

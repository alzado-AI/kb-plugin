"""Configuration for the KB CLI."""

import os
from pathlib import Path

# KB API URL — required for all operations
KB_API_URL = os.environ.get("KB_API_URL", "")

# Service key for admin/internal access (no RLS)
KB_SERVICE_KEY = os.environ.get("KB_SERVICE_KEY", "")

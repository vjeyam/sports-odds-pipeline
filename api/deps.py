from __future__ import annotations

import os
from typing import Optional


def db_target(override: Optional[str]) -> str:
    # If override is provided, use it, otherwise use DATABASE_URL, otherwise default.
    return override or os.getenv("DATABASE_URL") or "odds.sqlite"
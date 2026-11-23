import json
from functools import lru_cache
from pathlib import Path

_CONSTANTS = Path(__file__).resolve().parents[4] / "packages" / "shared" / "constants.json"


@lru_cache
def load_constants() -> dict:
    return json.loads(_CONSTANTS.read_text(encoding="utf-8"))

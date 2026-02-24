import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "registry.json"


def load_registry() -> list:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)["brokers"]


def get_broker(broker_id: str) -> dict | None:
    return next((b for b in load_registry() if b["id"] == broker_id), None)

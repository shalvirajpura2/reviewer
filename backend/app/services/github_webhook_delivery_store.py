from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.services.json_file_store import read_json_object, write_json_object


deliveries_store_file = Path(__file__).resolve().parents[2] / "data" / "github_webhook_deliveries.json"
deliveries_store_lock = Lock()


def has_processed_delivery(delivery_id: str) -> bool:
    if not delivery_id:
        return False

    with deliveries_store_lock:
        payload = read_json_object(deliveries_store_file, {"deliveries": {}})
        deliveries = payload.get("deliveries", {})
        return isinstance(deliveries, dict) and delivery_id in deliveries


def mark_processed_delivery(delivery_id: str, event_name: str, action: str, owner: str, repo: str, pull_number: int) -> None:
    if not delivery_id:
        return

    with deliveries_store_lock:
        payload = read_json_object(deliveries_store_file, {"deliveries": {}})
        deliveries = payload.get("deliveries", {})
        if not isinstance(deliveries, dict):
            deliveries = {}

        deliveries[delivery_id] = {
            "event": event_name,
            "action": action,
            "owner": owner,
            "repo": repo,
            "pull_number": pull_number,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        payload["deliveries"] = deliveries
        write_json_object(deliveries_store_file, payload)

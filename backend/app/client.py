import asyncio
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings

MASKED_KEY = "********"


@dataclass
class Relay:
    name: str
    type: str = "mock"
    url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    model: str | None = None


def _relay_path() -> Path:
    settings = get_settings()
    settings.relay_config_path.parent.mkdir(parents=True, exist_ok=True)
    return settings.relay_config_path


def _default_mock() -> Relay:
    return Relay(name="mock", type="mock", model="mock-monitor-v8")


def _read_relay_items() -> list[dict[str, Any]]:
    path = _relay_path()
    if not path.exists():
        return [asdict(_default_mock())]
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("relays", [])


def _write_relay_items(items: list[dict[str, Any]]) -> None:
    path = _relay_path()
    has_mock = any(item.get("name") == "mock" for item in items)
    if not has_mock:
        items.insert(0, asdict(_default_mock()))
    path.write_text(json.dumps({"relays": items}, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_item(item: dict[str, Any]) -> dict[str, Any]:
    allowed = {"name", "type", "url", "api_key", "api_key_env", "model"}
    cleaned = {key: value for key, value in item.items() if key in allowed and value not in (None, "")}
    if cleaned.get("name") == "mock":
        return asdict(_default_mock())
    cleaned.setdefault("type", "openai_compatible")
    return cleaned


def load_relays() -> dict[str, Relay]:
    relays = {}
    for item in _read_relay_items():
        cleaned = _clean_item(item)
        relay = Relay(**cleaned)
        relays[relay.name] = relay
    relays.setdefault("mock", _default_mock())
    return relays


def list_relay_configs(mask_keys: bool = True) -> list[dict[str, Any]]:
    configs = []
    for relay in load_relays().values():
        item = asdict(relay)
        if mask_keys and item.get("api_key"):
            item["api_key"] = MASKED_KEY
        configs.append(item)
    return sorted(configs, key=lambda item: (item["name"] != "mock", item["name"]))


def save_relay_config(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("Relay name is required")
    if name == "mock":
        raise ValueError("mock relay cannot be overwritten")

    items = [_clean_item(item) for item in _read_relay_items()]
    existing = next((item for item in items if item.get("name") == name), {})
    next_item = _clean_item({**existing, **payload, "name": name})

    if payload.get("api_key") == MASKED_KEY and existing.get("api_key"):
        next_item["api_key"] = existing["api_key"]

    items = [item for item in items if item.get("name") != name]
    items.append(next_item)
    _write_relay_items(items)

    saved = dict(next_item)
    if saved.get("api_key"):
        saved["api_key"] = MASKED_KEY
    return saved


def delete_relay_config(name: str) -> None:
    if name == "mock":
        raise ValueError("mock relay cannot be deleted")
    items = [_clean_item(item) for item in _read_relay_items()]
    _write_relay_items([item for item in items if item.get("name") != name])


async def _mock_response(prompt: str) -> dict[str, Any]:
    settings = get_settings()
    await asyncio.sleep(settings.mock_latency_ms / 1000)
    templates = [
        "Mock relay analysis: the request was processed normally. Key topic: {topic}. Confidence remains stable.",
        "Local simulated model response for '{topic}'. No external provider was called. Monitoring metadata was generated.",
        "Synthetic answer: {topic}. This sample is useful for dashboard, drift, and risk-score validation.",
    ]
    topic = prompt.strip().replace("\n", " ")[:120]
    return {
        "text": random.choice(templates).format(topic=topic),
        "raw": {"provider": "mock", "model": "mock-monitor-v8"},
    }


async def _openai_compatible_response(relay: Relay, prompt: str) -> dict[str, Any]:
    if not relay.url:
        raise ValueError(f"Relay {relay.name} is missing url")

    headers = {"Content-Type": "application/json"}
    api_key = relay.api_key
    if not api_key and relay.api_key_env:
        import os

        api_key = os.getenv(relay.api_key_env)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": relay.model or "default",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(relay.url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"text": text, "raw": data}


async def call_llm(prompt: str, relay_name: str | None = "mock") -> dict[str, Any]:
    relays = load_relays()
    relay = relays.get(relay_name or "mock", relays["mock"])

    if relay.type == "openai_compatible":
        return await _openai_compatible_response(relay, prompt)
    return await _mock_response(prompt)

"""Configuration management for human module."""
import json
import os

_DEFAULTS = {
    "provider_url": "http://127.0.0.1:8000",
    "lark_path": "lark-cli",
}
_CONFIG_PATH = os.path.expanduser("~/.config/qtadmin/human.json")


class Config:
    """Manages human module config stored as JSON."""

    def __init__(self, path: str | None = None) -> None:
        self._path = path or _CONFIG_PATH
        self._data: dict[str, str] = {}

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self._data = {k: str(v) for k, v in raw.items()}
                return
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> str:
        self._load()
        return self._data.get(key, _DEFAULTS.get(key, ""))

    def set(self, key: str, value: str) -> None:
        self._load()
        self._data[key] = value
        self._save()

    def show(self) -> dict[str, str]:
        self._load()
        merged = dict(_DEFAULTS)
        merged.update(self._data)
        return merged

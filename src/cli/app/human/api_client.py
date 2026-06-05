"""HTTP client for communicating with the qtadmin provider HR API."""
import httpx


class ApiClient:
    """Client for the qtadmin provider HR API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self._base_url = base_url.rstrip("/")

    def ingest(self, source: str, items: list[dict]) -> dict:
        """POST /ingest — push classified emails to pending queue."""
        r = httpx.post(f"{self._base_url}/ingest", json={"source": source, "items": items})
        if r.status_code != 201:
            raise RuntimeError(f"Ingest failed (HTTP {r.status_code}): {r.text}")
        return r.json()

    def get_queue_stats(self) -> dict[str, int]:
        """GET /queue/stats — get pending/confirmed/ignored counts."""
        r = httpx.get(f"{self._base_url}/queue/stats")
        if r.status_code != 200:
            raise RuntimeError(f"Queue stats failed (HTTP {r.status_code}): {r.text}")
        return r.json()

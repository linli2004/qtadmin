"""HTTP client for communicating with the qtadmin provider HR API."""
import httpx


class ApiClient:
    """Client for the qtadmin provider HR API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080") -> None:
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

    def claim_outbox(self) -> dict:
        """POST /messages/outbox/claim — claim pending outbox messages."""
        r = httpx.post(f"{self._base_url}/messages/outbox/claim", timeout=30)
        r.raise_for_status()
        return r.json()

    def get_outbox_detail(self, mid: int, lease_id: str) -> dict:
        """GET /messages/outbox/{id}?lease_id= — get full message detail."""
        r = httpx.get(
            f"{self._base_url}/messages/outbox/{mid}",
            params={"lease_id": lease_id},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def update_send_status(
        self, mid: int, lease_id: str, status: str,
        platform_message_id: str = "", failure_reason: str = "",
    ) -> int:
        """PATCH /messages/{id}/send-status — update send status.

        Returns HTTP status code (200=ok, 409=conflict).
        """
        body = {"lease_id": lease_id, "send_status": status}
        if platform_message_id:
            body["platform_message_id"] = platform_message_id
        if failure_reason:
            body["failure_reason"] = failure_reason
        r = httpx.patch(
            f"{self._base_url}/messages/{mid}/send-status",
            json=body,
            timeout=30,
        )
        return r.status_code

    def get_outbox_count(self, status: str | None = None) -> int:
        """GET /messages/outbox — count outbox messages, optionally filtered by status."""
        params = {"status": status} if status else {}
        r = httpx.get(f"{self._base_url}/messages/outbox", params=params, timeout=30)
        r.raise_for_status()
        return r.json()["count"]

    def list_dead_letters(self) -> list[dict]:
        """GET /messages/outbox/dead — list dead letters."""
        r = httpx.get(f"{self._base_url}/messages/outbox/dead", timeout=30)
        r.raise_for_status()
        return r.json()

    def requeue_dead_letter(self, message_id: int) -> dict:
        """POST /messages/outbox/{id}/requeue — reset dead letter to pending."""
        r = httpx.post(f"{self._base_url}/messages/outbox/{message_id}/requeue", timeout=30)
        r.raise_for_status()
        return r.json()

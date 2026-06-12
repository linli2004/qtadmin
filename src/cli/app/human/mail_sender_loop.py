"""systemd entry point — runs the mail sender polling loop.

Usage:
    python -m app.human.mail_sender_loop

Environment variables:
    QTADMIN_SERVER_URL — provider base URL (default: http://localhost:8080)
"""
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

if __name__ == "__main__":
    from app.human.api_client import ApiClient
    from app.human.mail_sender import run_loop

    server_url = os.environ.get("QTADMIN_SERVER_URL", "http://localhost:8080")
    api = ApiClient(base_url=server_url)
    run_loop(api)

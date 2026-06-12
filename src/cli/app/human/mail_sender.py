"""飞书邮件发送：从 outbox 获取待发邮件，通过 lark-cli 发送。"""

import json
import logging
import subprocess
import time

logger = logging.getLogger(__name__)


def _lark_send(recipient: str, subject: str, body: str) -> dict:
    """调用 lark-cli mail +send 发送邮件，返回解析后的 JSON。"""
    cmd = [
        "lark-cli", "mail", "+send",
        "--to", recipient,
        "--subject", subject,
        "--body", body,
        "--confirm-send",
        "--format", "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    result.check_returncode()
    return json.loads(result.stdout)


def send_pending(api) -> int:
    """Claim outbox messages and send them via lark-cli. Returns number sent."""
    sent_count = 0
    data = api.claim_outbox()
    claimed = data.get("claimed", [])

    if not claimed:
        logger.info("No pending messages to send.")
        return 0

    for msg in claimed:
        mid = msg["id"]
        lease_id = msg["lease_id"]
        recipient = msg.get("recipient_email", "")

        if not recipient:
            logger.warning("Message %d has no recipient_email, skipping", mid)
            continue

        detail = api.get_outbox_detail(mid, lease_id)
        body = detail.get("body_text") or detail.get("body") or ""

        try:
            logger.info("Sending message %d to %s: %s", mid, recipient, msg["subject"])
            lark_resp = _lark_send(recipient, msg["subject"], body)
            platform_id = ""
            if isinstance(lark_resp, dict):
                platform_id = lark_resp.get("data", {}).get("id", "")
            if not platform_id:
                platform_id = lark_resp.get("id", str(lark_resp))

            status_code = api.update_send_status(
                mid, lease_id, "sent",
                platform_message_id=platform_id,
            )
            if status_code == 409:
                logger.warning("Message %d lease_id mismatch (concurrent send?)", mid)
            else:
                sent_count += 1
                logger.info("Message %d sent successfully (platform_id=%s)", mid, platform_id)

        except subprocess.CalledProcessError as e:
            err_msg = e.stderr or str(e)
            logger.error("lark-cli failed for message %d: %s", mid, err_msg)
            api.update_send_status(mid, lease_id, "failed", failure_reason=err_msg[:500])
        except Exception as e:
            logger.error("Unexpected error for message %d: %s", mid, str(e))
            api.update_send_status(mid, lease_id, "failed", failure_reason=str(e)[:500])

    return sent_count


def run_loop(api, interval: int = 30):
    """Continuous send loop."""
    logger.info("Mail sender loop started (interval=%ds)", interval)
    while True:
        try:
            n = send_pending(api)
            if n:
                logger.info("Sent %d messages this cycle", n)
        except Exception as e:
            logger.error("Send cycle failed: %s", str(e))
        time.sleep(interval)

"""
tasks/notification_task.py

NOTIFICATION TASK — dispatches real-time alerts via Slack webhooks.

a single HTTP POST to a webhook URL Slack gave you when you set up the Incoming Webhook app.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


def send_slack_notification(message: str, channel_hint: str = "") -> str:
    """Sends a real-time notification to Slack via webhook.

    Args:
        message: The notification text to send to Slack.
        channel_hint: Optional note about which channel this is intended for
            (informational only — the webhook is already tied to one channel).

    Returns:
        A JSON string describing whether the notification was sent successfully.
    """
    if not SLACK_WEBHOOK_URL:
        return json.dumps({"error": "SLACK_WEBHOOK_URL is not configured in .env"})

    payload = {"text": message}

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)

        if response.status_code == 200:
            return json.dumps({
                "success": True,
                "action": "notification_sent",
                "message": message,
                "channel_hint": channel_hint or "default"
            })
        else:
            return json.dumps({
                "error": f"Slack returned status {response.status_code}: {response.text}"
            })

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to reach Slack: {str(e)}"})
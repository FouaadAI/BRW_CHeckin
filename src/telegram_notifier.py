"""Telegram Bot API helpers for immediate check-in notifications."""

import html
import os
from typing import Any

import requests


DEFAULT_TIMEOUT = 30


def send_message(
    chat_id: str | int,
    text: str,
    bot_token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Send a plain text message via the Telegram Bot API."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nicht konfiguriert")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def send_document(
    chat_id: str | int,
    file_path: str,
    caption: str = "",
    bot_token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Send a document via the Telegram Bot API."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nicht konfiguriert")

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        response = requests.post(url, files=files, data=data, timeout=timeout)
    response.raise_for_status()
    return response.json()


def format_checkin_message(
    name: str,
    station: str,
    shift: str,
    distance_m: float,
    lat: float,
    lng: float,
    timestamp: str,
) -> str:
    """Format a concise HTML check-in message for the manager."""
    maps_url = html.escape(f"https://www.google.com/maps?q={lat},{lng}")
    return (
        f"✅ <b>Check-in</b>\n"
        f"Mitarbeiter: {html.escape(name)}\n"
        f"Station: {html.escape(station)}\n"
        f"Schicht: {html.escape(shift)}\n"
        f"Distanz: {html.escape(str(distance_m))} m\n"
        f"Zeit: {html.escape(timestamp)}\n"
        f"<a href='{maps_url}'>Google Maps</a>"
    )

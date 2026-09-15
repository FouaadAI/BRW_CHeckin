"""Unit tests for Telegram notifier helpers."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.telegram_notifier import (
    DEFAULT_TIMEOUT,
    format_checkin_message,
    send_document,
    send_message,
)


def test_send_message_success():
    with patch("src.telegram_notifier.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 42}}
        mock_post.return_value = mock_response

        result = send_message(chat_id="12345", text="Hello", bot_token="fake-token")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["timeout"] == DEFAULT_TIMEOUT
        assert kwargs["json"]["chat_id"] == "12345"
        assert kwargs["json"]["text"] == "Hello"
        assert result["ok"] is True


def test_send_message_missing_token_raises():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
            send_message(chat_id="12345", text="Hello")


def test_send_message_uses_environment_token():
    with patch("src.telegram_notifier.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "env-token"}):
            send_message(chat_id="12345", text="Hello")

        args, kwargs = mock_post.call_args
        assert "env-token" in args[0]


def test_send_document_success(tmp_path):
    file_path = tmp_path / "report.xlsx"
    file_path.write_text("fake-excel")

    with patch("src.telegram_notifier.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        result = send_document(
            chat_id="12345",
            file_path=str(file_path),
            caption="Monthly report",
            bot_token="fake-token",
        )

        assert result["ok"] is True
        mock_post.assert_called_once()


def test_format_checkin_message():
    text = format_checkin_message(
        name="Max Mustermann",
        station="U Alexanderplatz",
        shift="Früh",
        distance_m=42.0,
        lat=52.52,
        lng=13.41,
        timestamp="2024-09-15T12:30:00+00:00",
    )
    assert "Max Mustermann" in text
    assert "U Alexanderplatz" in text
    assert "Früh" in text
    assert "42.0 m" in text
    assert "https://www.google.com/maps?q=52.52,13.41" in text


def test_format_checkin_message_escapes_html():
    text = format_checkin_message(
        name="Max <script>",
        station="U & More",
        shift="Früh",
        distance_m=42.0,
        lat=52.52,
        lng=13.41,
        timestamp="2024-09-15T12:30:00+00:00",
    )
    assert "Max &lt;script&gt;" in text
    assert "U &amp; More" in text
    assert "<script>" not in text

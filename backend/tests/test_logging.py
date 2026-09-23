import json
import logging

from app.logging import JsonFormatter, request_id_var


def test_json_formatter_includes_request_id():
    formatter = JsonFormatter()
    token = request_id_var.set("req-test-123")
    try:
        record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "hello", None, None)
        record.method = "GET"
        record.status_code = 200
        record.duration_ms = 3.5
        payload = json.loads(formatter.format(record))
        assert payload["message"] == "hello"
        assert payload["request_id"] == "req-test-123"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "app.test"
        assert payload["method"] == "GET"
        assert payload["status_code"] == 200
        assert payload["duration_ms"] == 3.5
        assert "timestamp" in payload
    finally:
        request_id_var.reset(token)


def test_json_formatter_defaults_request_id():
    formatter = JsonFormatter()
    record = logging.LogRecord("app.test", logging.WARNING, __file__, 1, "no context", None, None)
    payload = json.loads(formatter.format(record))
    assert payload["request_id"] == "-"

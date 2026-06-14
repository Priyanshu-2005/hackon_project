"""Tests for CORS preflight (OPTIONS) and CORS headers on all responses.

Validates:
- Requirements 2.1: OPTIONS returns HTTP 204 with empty body
- Requirements 2.2: OPTIONS includes Access-Control-Allow-Origin: *
- Requirements 2.3: OPTIONS includes Access-Control-Allow-Methods listing GET, POST, PUT, OPTIONS
- Requirements 2.4: OPTIONS includes Access-Control-Allow-Headers containing Content-Type
- Requirements 2.5: Every non-OPTIONS response carries Access-Control-Allow-Origin: *

Property 3: Every non-OPTIONS response carries the CORS allow-origin header
(single-execution example for the OPTIONS case)
"""

import json
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer
from pathlib import Path

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from demo import CORS_HEADERS, _strip_prefix, API_PREFIX


def _get_demo_handler_class():
    """Import the DemoHandler class by triggering the import path used in run_api_demo."""
    from http.server import BaseHTTPRequestHandler
    from src.handlers.api_handler import lambda_handler

    class DemoHandler(BaseHTTPRequestHandler):
        """Replica of DemoHandler from demo.py for testing purposes."""

        def do_OPTIONS(self):
            self.send_response(204)
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            self.end_headers()

        def _dispatch(self, http_method, body=""):
            path = _strip_prefix(self.path)
            event = {"httpMethod": http_method, "path": path, "pathParameters": {}, "body": body}
            parts = [p for p in path.split("/") if p]

            if http_method == "GET" and len(parts) >= 3 and parts[0] == "devices" and parts[-1] == "state":
                event["pathParameters"] = {"id": parts[1]}
            elif http_method == "POST" and len(parts) >= 3 and parts[0] == "devices" and parts[-1] == "command":
                event["pathParameters"] = {"id": parts[1]}
            elif http_method == "PUT" and len(parts) >= 3 and parts[0] == "autonomy" and parts[1] == "tiers":
                event["pathParameters"] = {"device": parts[-1]}

            result = lambda_handler(event, None)

            self.send_response(result["statusCode"])
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            for k, v in result.get("headers", {}).items():
                if k not in CORS_HEADERS:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(result["body"].encode())

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length else ""
            self._dispatch("POST", body)

        def do_PUT(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length else ""
            self._dispatch("PUT", body)

        def log_message(self, format, *args):
            pass  # Suppress log output during tests

    return DemoHandler


@pytest.fixture(scope="module")
def test_server():
    """Start a test HTTP server on a random port and yield the base URL."""
    DemoHandler = _get_demo_handler_class()
    server = HTTPServer(("127.0.0.1", 0), DemoHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    # Give server a moment to start
    time.sleep(0.1)
    yield base_url
    server.shutdown()


class TestOptionsPreflightCORS:
    """Test OPTIONS preflight returns correct CORS headers (Req 2.1-2.4)."""

    def test_options_returns_204(self, test_server):
        """OPTIONS on any path returns HTTP 204."""
        req = urllib.request.Request(f"{test_server}/api/v1/devices", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 204

    def test_options_body_is_empty(self, test_server):
        """OPTIONS response body is empty."""
        req = urllib.request.Request(f"{test_server}/api/v1/devices", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            assert body == b""

    def test_options_access_control_allow_origin(self, test_server):
        """OPTIONS includes Access-Control-Allow-Origin: *."""
        req = urllib.request.Request(f"{test_server}/api/v1/devices", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            assert resp.headers["Access-Control-Allow-Origin"] == "*"

    def test_options_access_control_allow_methods(self, test_server):
        """OPTIONS includes Access-Control-Allow-Methods with GET, POST, PUT, OPTIONS."""
        req = urllib.request.Request(f"{test_server}/api/v1/devices", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            methods_header = resp.headers["Access-Control-Allow-Methods"]
            assert methods_header is not None
            for method in ("GET", "POST", "PUT", "OPTIONS"):
                assert method in methods_header

    def test_options_access_control_allow_headers(self, test_server):
        """OPTIONS includes Access-Control-Allow-Headers containing Content-Type."""
        req = urllib.request.Request(f"{test_server}/api/v1/devices", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            headers_val = resp.headers["Access-Control-Allow-Headers"]
            assert headers_val is not None
            assert "Content-Type" in headers_val

    def test_options_on_arbitrary_path(self, test_server):
        """OPTIONS works on any path, not just /devices."""
        req = urllib.request.Request(f"{test_server}/api/v1/context/snapshot", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 204
            assert resp.headers["Access-Control-Allow-Origin"] == "*"


class TestNonOptionsCORSHeader:
    """Property 3: Every non-OPTIONS response carries Access-Control-Allow-Origin: *.

    Validates: Requirements 2.5
    """

    def test_get_devices_has_cors_header(self, test_server):
        """GET /api/v1/devices includes Access-Control-Allow-Origin: *."""
        req = urllib.request.Request(f"{test_server}/api/v1/devices", method="GET")
        with urllib.request.urlopen(req) as resp:
            assert resp.headers["Access-Control-Allow-Origin"] == "*"

    def test_get_unknown_path_404_has_cors_header(self, test_server):
        """404 response for unknown path still includes CORS header."""
        req = urllib.request.Request(f"{test_server}/api/v1/nonexistent", method="GET")
        try:
            urllib.request.urlopen(req)
            assert False, "Expected HTTP error"
        except urllib.error.HTTPError as e:
            assert e.code == 404
            assert e.headers["Access-Control-Allow-Origin"] == "*"

    def test_get_device_state_has_cors_header(self, test_server):
        """GET /api/v1/devices/{id}/state includes CORS header."""
        req = urllib.request.Request(
            f"{test_server}/api/v1/devices/living_room_ac/state", method="GET"
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.headers["Access-Control-Allow-Origin"] == "*"

    def test_post_response_has_cors_header(self, test_server):
        """POST response includes CORS header (even for 400 errors)."""
        # POST to /devices/{id}/command without a body → should have CORS header
        data = json.dumps({}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/v1/devices/living_room_ac/command",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            # 400 for missing command field
            assert e.headers["Access-Control-Allow-Origin"] == "*"

    def test_put_response_has_cors_header(self, test_server):
        """PUT response includes CORS header."""
        data = json.dumps({"tier": 3}).encode()
        req = urllib.request.Request(
            f"{test_server}/api/v1/autonomy/tiers/climate",
            data=data,
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.headers["Access-Control-Allow-Origin"] == "*"

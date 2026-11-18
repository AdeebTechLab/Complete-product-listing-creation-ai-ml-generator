"""Deployment-readiness checks: Vercel config, static frontend, security headers, rate limiting."""

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.security import SlidingWindowLimiter
from app.core.config import Settings
from app.main import create_app
from app.services.image_service import ImageService
from app.services.listing_service import ListingService
from tests.helpers import FakeVision, good_payload, jpeg_bytes

ROOT = Path(__file__).resolve().parents[1]
URL = "/api/v1/generate-listing/"


def client(*payloads, serve_frontend=False, **kw) -> TestClient:
    settings = Settings(gemini_api_key="test-key", _env_file=None, **kw)
    service = ListingService(ImageService(settings), FakeVision(*payloads), settings)
    return TestClient(create_app(settings=settings, listing_service=service, serve_frontend=serve_frontend))


def post(c: TestClient):
    return c.post(URL, files=[("images", ("a.jpg", jpeg_bytes(), "image/jpeg"))])


# ------------------------------------------------------------- vercel config
def test_vercel_json_is_valid_and_sets_function_duration():
    cfg = json.loads((ROOT / "vercel.json").read_text())
    assert cfg["functions"]["app/main.py"]["maxDuration"] >= 60
    csp = next(h["value"] for rule in cfg["headers"] for h in rule["headers"] if h["key"] == "Content-Security-Policy")
    assert "'unsafe-inline'" not in csp and "script-src 'self'" in csp


def test_runtime_requirements_have_no_dev_tools():
    reqs = (ROOT / "requirements.txt").read_text().lower()
    for dev in ("pytest", "streamlit", "uvicorn", "httpx"):
        assert dev not in reqs
    assert "fastapi" in reqs and "google-genai" in reqs


def test_vercel_entrypoint_exposes_app():
    from app.main import app

    assert app.title


def test_frontend_files_exist_and_are_csp_clean():
    html = (ROOT / "public" / "index.html").read_text()
    assert "/assets/app.js" in html and "/assets/styles.css" in html
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), "inline <script> would break the CSP"
    assert " style=" not in html, "inline style attributes would break the CSP"
    for js in ("app.js", "api.js", "images.js", "text.js"):
        assert (ROOT / "public" / "assets" / js).is_file()
    assert "innerHTML" not in (ROOT / "public" / "assets" / "app.js").read_text()


# ----------------------------------------------------------- frontend (local)
def test_frontend_served_locally_and_api_still_works():
    c = client(good_payload(), serve_frontend=True)
    home = c.get("/")
    assert home.status_code == 200 and "Vision Cart" in home.text
    assert c.get("/health").json() == {"status": "ok"}
    assert post(c).status_code == 200


def test_frontend_not_served_by_default():
    assert client().get("/").status_code == 404


# ---------------------------------------------------------- security headers
def test_security_headers_and_no_store_on_api():
    r = post(client(good_payload()))
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-request-id"]


# -------------------------------------------------------------- rate limiting
def test_limiter_window_and_reset():
    lim = SlidingWindowLimiter(2)
    assert lim.check("a", now=0) == 0 and lim.check("a", now=1) == 0
    assert lim.check("a", now=2) > 0
    assert lim.check("b", now=2) == 0  # other clients unaffected
    assert lim.check("a", now=62) == 0  # window slid


def test_limiter_disabled_when_zero():
    lim = SlidingWindowLimiter(0)
    assert all(lim.check("a", now=i) == 0 for i in range(100))


def test_api_returns_429_envelope_when_limit_exceeded():
    c = client(good_payload(), good_payload(), rate_limit_per_minute=1)
    assert post(c).status_code == 200
    r = post(c)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["retry-after"]) >= 1


def test_vercel_client_ip_header_is_used_for_limiting():
    c = client(good_payload(), good_payload(), rate_limit_per_minute=1)
    files = [("images", ("a.jpg", jpeg_bytes(), "image/jpeg"))]
    assert c.post(URL, files=files, headers={"x-vercel-forwarded-for": "1.1.1.1"}).status_code == 200
    assert c.post(URL, files=files, headers={"x-vercel-forwarded-for": "2.2.2.2"}).status_code == 200


def test_health_is_never_rate_limited():
    c = client(rate_limit_per_minute=1)
    assert all(c.get("/health").status_code == 200 for _ in range(5))


# ------------------------------------------------------------------------ CORS
def test_cors_only_for_configured_origins():
    c = client(cors_origins="https://shop.example.com/")
    ok = c.options(URL, headers={"Origin": "https://shop.example.com", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "https://shop.example.com"
    bad = c.options(URL, headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers

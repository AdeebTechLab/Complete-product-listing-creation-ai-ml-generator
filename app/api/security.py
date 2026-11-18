"""Security headers and a small best-effort rate limiter for the public AI endpoints.

The limiter is in-memory (per process). On serverless platforms each warm instance keeps its
own counters, so treat it as a courtesy brake and add a platform firewall rule for a hard cap.
"""

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request

from app.api.errors import error_response

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

_WINDOW_S = 60.0
_MAX_TRACKED_CLIENTS = 10_000


def client_key(request: Request) -> str:
    """Best available client identity. Vercel sets x-vercel-forwarded-for; it cannot be spoofed."""
    for header in ("x-vercel-forwarded-for", "x-real-ip"):
        value = request.headers.get(header, "").strip()
        if value:
            return value.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float | None = None) -> int:
        """Return 0 if allowed, otherwise the seconds to wait."""
        if self.limit <= 0:
            return 0
        now = time.monotonic() if now is None else now
        if len(self._hits) > _MAX_TRACKED_CLIENTS:
            self._hits.clear()  # crude memory bound; the limiter is only best-effort
        hits = self._hits[key]
        while hits and now - hits[0] > _WINDOW_S:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1, int(_WINDOW_S - (now - hits[0])) + 1)
        hits.append(now)
        return 0


def install_security(app: FastAPI, rate_limit_per_minute: int) -> None:
    limiter = SlidingWindowLimiter(rate_limit_per_minute)

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/api/"):
            wait = limiter.check(client_key(request))
            if wait:
                return error_response(
                    429,
                    "rate_limited",
                    "Too many requests. Please wait a moment and try again.",
                    getattr(request.state, "request_id", "-"),
                    headers={"Retry-After": str(wait)},
                )
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

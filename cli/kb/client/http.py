"""Generic HTTP client for the KB REST API.

Provides a thin wrapper around httpx that maps CLI operations to REST endpoints.
Instead of one method per CLI command, uses a generic pattern:
  client.list("programs", module="accounting")
  client.show("programs", "my-slug", full=True)
  client.create("programs", slug="my-slug", module="accounting")
  client.action("programs", "my-slug", "link-need", need_slug="some-need")
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Default timeout in seconds. Can be overridden via KB_TIMEOUT env var.
# Raised from 30 s to 60 s to accommodate endpoints that require multiple
# serial API calls before the final POST (e.g. `pipeline add-step`).
_DEFAULT_TIMEOUT = 60.0


def _resolve_timeout() -> float:
    """Return the effective client timeout from KB_TIMEOUT env var or the default."""
    raw = os.environ.get("KB_TIMEOUT", "")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_TIMEOUT


class APIError(Exception):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str, code: str = "", hint: str = ""):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.hint = hint
        super().__init__(f"API {status_code}: {detail}")


class _RetryAfterRefresh(Exception):
    """Internal: signals that a token refresh succeeded and the request should be retried."""


# Entities that use slug as lookup field (vs integer pk)
_SLUG_ENTITIES = {
    "programs", "projects", "jobs", "modules", "scripts", "templates",
    "opportunities", "account-plans", "budgets",
    "agents", "skills",
}


class KBClient:
    """HTTP client for the KB Django REST API."""

    def __init__(
        self,
        base_url: str,
        token: str = "",
        on_behalf_of: str = "",
        refresh_token: str = "",
        token_source: str = "none",
        session_file: Path | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._refresh_token = refresh_token
        self._refreshing = False
        # Where the access token came from. Drives refresh persistence
        # (only session_file is writable) and the hint shown on 401.
        self.token_source = token_source
        self.session_file = session_file
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if on_behalf_of:
            headers["X-On-Behalf-Of"] = on_behalf_of
        self.http = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers=headers,
            timeout=_resolve_timeout(),
        )

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    def list(self, entity: str, **params: Any) -> list[dict]:
        """GET /api/v1/{entity}/?param=value — auto-paginates through all pages."""
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._get(f"/{entity}/", params=clean)
        data = resp.json()
        # DRF pagination wraps in {"count", "next", "results"}
        if isinstance(data, dict) and "results" in data:
            results = list(data["results"])
            # Auto-paginate: follow next links to fetch all pages
            while data.get("next"):
                resp = self._get_absolute(data["next"])
                data = resp.json()
                results.extend(data.get("results", []))
            return results
        return data

    def show(self, entity: str, identifier: str | int, **params: Any) -> dict:
        """GET /api/v1/{entity}/{identifier}/"""
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._get(f"/{entity}/{identifier}/", params=clean)
        return resp.json()

    def create(self, entity: str, **data: Any) -> dict:
        """POST /api/v1/{entity}/"""
        clean = {k: v for k, v in data.items() if v is not None}
        resp = self._post(f"/{entity}/", json=clean)
        return resp.json()

    def update(self, entity: str, identifier: str | int, **data: Any) -> dict:
        """PATCH /api/v1/{entity}/{identifier}/"""
        clean = {k: v for k, v in data.items() if v is not None}
        resp = self._patch(f"/{entity}/{identifier}/", json=clean)
        return resp.json()

    def get(self, path: str, **params: Any) -> dict:
        """GET /api/v1/{path}/ — direct path access (e.g. 'agents/feedback-triager')."""
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._get(f"/{path.rstrip('/')}/", params=clean)
        return resp.json()

    def post(self, path: str, data: dict | None = None, timeout: float | None = None) -> dict:
        """POST /api/v1/{path}/ — direct path access (e.g. 'agents/slug/pause').

        Args:
            timeout: Per-request timeout in seconds. Defaults to the client-level
                     timeout (30 s). Pass a higher value for slow endpoints such as
                     pipeline activate (which may do heavy DB work on first call).
        """
        kwargs: dict = {"json": data or {}}
        if timeout is not None:
            kwargs["timeout"] = timeout
        resp = self._post(f"/{path.rstrip('/')}/", **kwargs)
        return resp.json()

    def delete(self, entity: str, identifier: str | int, **params: Any) -> dict:
        """DELETE /api/v1/{entity}/{identifier}/

        Extra keyword arguments are forwarded as query-string parameters so
        callers can pass e.g. ``section="codebase-navigator"`` for endpoints
        that scope deletion by an additional key.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._delete(f"/{entity}/{identifier}/", params=clean or None)
        if resp.status_code == 204:
            return {"status": "deleted"}
        return resp.json()

    # ------------------------------------------------------------------
    # Custom actions (link, unlink, etc.)
    # ------------------------------------------------------------------

    def action(
        self,
        entity: str,
        identifier: str | int,
        action_name: str,
        method: str = "POST",
        **data: Any,
    ) -> dict:
        """POST/DELETE /api/v1/{entity}/{identifier}/{action_name}/"""
        clean = {k: v for k, v in data.items() if v is not None}
        path = f"/{entity}/{identifier}/{action_name}/"
        if method.upper() == "DELETE":
            resp = self._delete(path)
        else:
            resp = self._post(path, json=clean)
        return resp.json()

    def action_nested(
        self,
        entity: str,
        identifier: str | int,
        action_name: str,
        sub_id: str | int,
        method: str = "DELETE",
    ) -> dict:
        """DELETE /api/v1/{entity}/{identifier}/{action_name}/{sub_id}/"""
        path = f"/{entity}/{identifier}/{action_name}/{sub_id}/"
        resp = self._delete(path)
        return resp.json()

    # ------------------------------------------------------------------
    # Cross-cutting endpoints
    # ------------------------------------------------------------------

    def search(self, q: str, **params: Any) -> list[dict]:
        """GET /api/v1/search/?q=keyword"""
        params["q"] = q
        resp = self._get("/search/", params=params)
        data = resp.json()
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    def query(self, query_name: str, **params: Any) -> Any:
        """GET /api/v1/query/{query_name}/"""
        clean = {k: v for k, v in params.items() if v is not None}
        resp = self._get(f"/query/{query_name}/", params=clean)
        return resp.json()

    def health(self) -> dict:
        """GET /api/v1/health/"""
        resp = self._get("/health/")
        return resp.json()

    # ------------------------------------------------------------------
    # File upload (multipart)
    # ------------------------------------------------------------------

    def upload_file(self, file_path: str, **params: Any) -> dict:
        """POST /api/v1/run-artifacts/upload/ — multipart file upload."""
        from pathlib import Path

        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        data = {k: str(v) for k, v in params.items() if v is not None}

        def _do_upload() -> httpx.Response:
            # Use a separate httpx request to avoid the JSON content-type header
            # from the client instance. Copy auth headers but let httpx set multipart boundary.
            headers = {}
            if "Authorization" in self.http.headers:
                headers["Authorization"] = str(self.http.headers["Authorization"])
            with open(p, "rb") as f:
                return httpx.post(
                    f"{str(self.http.base_url).rstrip('/')}/run-artifacts/upload/",
                    files={"file": (p.name, f)},
                    data=data,
                    headers=headers,
                    timeout=60.0,
                )

        resp = _do_upload()
        try:
            self._check(resp)
        except _RetryAfterRefresh:
            resp = _do_upload()
            self._check(resp)
        return resp.json()

    def download_file(self, file_id: int, output_path: str) -> str:
        """GET /api/v1/files/{id}/download/ → write bytes to output_path.
        Returns the absolute output path.
        """
        from pathlib import Path

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        def _do_download() -> httpx.Response:
            return self.http.get(f"/files/{file_id}/download/")

        resp = _do_download()
        try:
            self._check(resp)
        except _RetryAfterRefresh:
            resp = _do_download()
            self._check(resp)
        out.write_bytes(resp.content)
        return str(out.resolve())

    def read_file_text(self, file_id: int) -> str:
        """GET /api/v1/files/{id}/download/ → return content as decoded string.

        Use this to inline a text-based base_file (YAML, JSON, Markdown, TXT)
        directly into agent output without writing to disk. For binary files
        (xlsx, docx, etc.) use download_file instead.
        """
        def _do_download() -> httpx.Response:
            return self.http.get(f"/files/{file_id}/download/")

        resp = _do_download()
        try:
            self._check(resp)
        except _RetryAfterRefresh:
            resp = _do_download()
            self._check(resp)
        return resp.content.decode("utf-8", errors="replace")

    # ------------------------------------------------------------------
    # Content operations
    # ------------------------------------------------------------------

    def show_content(self, content_id: int, full_body: bool = False) -> dict:
        """GET /api/v1/content/{id}/?full_body=true"""
        params = {"full_body": "true"} if full_body else {}
        return self.show("content", content_id, **params)

    def push_content(self, content_id: int, body: str) -> dict:
        """PATCH /api/v1/content/{id}/"""
        return self.update("content", content_id, body=body)

    # ------------------------------------------------------------------
    # Sync operations
    # ------------------------------------------------------------------

    def sync_status(self) -> dict:
        resp = self._get("/sync/status/")
        return resp.json()

    def sync_pull(self) -> dict:
        resp = self._post("/sync/pull/")
        return resp.json()

    def sync_push(self, content_id: int, body: str) -> dict:
        resp = self._post("/sync/push/", json={"content_id": content_id, "body": body})
        return resp.json()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Execute an HTTP request with automatic retry on token refresh."""
        resp = getattr(self.http, method)(path, **kwargs)
        try:
            self._check(resp)
        except _RetryAfterRefresh:
            # Token was refreshed — retry once
            resp = getattr(self.http, method)(path, **kwargs)
            self._check(resp)
        return resp

    def _get(self, path: str, **kwargs) -> httpx.Response:
        return self._request("get", path, **kwargs)

    def _get_absolute(self, url: str) -> httpx.Response:
        """GET an absolute URL (used for following pagination next links)."""
        timeout = self.http.timeout
        resp = httpx.get(url, headers=dict(self.http.headers), timeout=timeout)
        try:
            self._check(resp)
        except _RetryAfterRefresh:
            resp = httpx.get(url, headers=dict(self.http.headers), timeout=timeout)
            self._check(resp)
        return resp

    def _post(self, path: str, **kwargs) -> httpx.Response:
        return self._request("post", path, **kwargs)

    def _patch(self, path: str, **kwargs) -> httpx.Response:
        return self._request("patch", path, **kwargs)

    def _delete(self, path: str, **kwargs) -> httpx.Response:
        return self._request("delete", path, **kwargs)

    # Retry loop for concurrent refreshes: when N parallel kb processes
    # hit an expired access token at the same time, only one actually
    # rotates; the rest need to wait briefly and re-hit the endpoint,
    # which will return the cached pair (see server-side
    # IdempotentTokenRefreshView). Jittered backoff avoids thundering
    # herd against the advisory lock.
    _REFRESH_MAX_ATTEMPTS = 3

    def _do_refresh(self) -> bool:
        """Attempt to refresh the access token. Returns True on success.

        On success the new access token replaces the Authorization header,
        and — if the original token was loaded from ``~/.kb/session.json``
        — the new pair is persisted back to disk with best-effort file
        locking so siblings processes see it.

        Retries up to ``_REFRESH_MAX_ATTEMPTS`` times with jittered
        backoff on 401, giving a concurrent refresher time to write the
        idempotent cache entry.
        """
        if not self._refresh_token or self._refreshing:
            return False
        self._refreshing = True
        try:
            for attempt in range(self._REFRESH_MAX_ATTEMPTS):
                try:
                    resp = httpx.post(
                        f"{self.base_url}/api/v1/auth/token/refresh/",
                        json={"refresh": self._refresh_token},
                        timeout=10.0,
                    )
                except httpx.RequestError:
                    return False

                if resp.status_code == 200:
                    body = resp.json()
                    new_access = body.get("access", "")
                    new_refresh = body.get("refresh", "")
                    if not new_access:
                        return False
                    self.http.headers["Authorization"] = f"Bearer {new_access}"
                    if new_refresh:
                        self._refresh_token = new_refresh
                    self._persist_tokens(new_access, new_refresh)
                    return True

                if resp.status_code == 401 and attempt < self._REFRESH_MAX_ATTEMPTS - 1:
                    # Could be a concurrent-rotation race; sleep a bit
                    # and try again — the winning rotation may have just
                    # written to the idempotency cache.
                    delay_ms = 100 + random.randint(0, 200)
                    time.sleep(delay_ms / 1000.0)
                    continue

                return False
            return False
        finally:
            self._refreshing = False

    def _persist_tokens(self, access: str, refresh: str) -> None:
        """Write the rotated token pair to ~/.kb/session.json (best effort).

        Only runs when the original access token came from
        ``session.json`` — refresh tokens injected via env live in the
        parent process and can't be updated from here.
        """
        if self.token_source != "session_file" or self.session_file is None:
            return
        from . import persist_session_tokens
        persist_session_tokens(access, refresh, self.session_file)

    def _check(self, resp: httpx.Response) -> None:
        if resp.status_code == 401 and self._refresh_token and not self._refreshing:
            if self._do_refresh():
                # Token refreshed — caller should retry
                raise _RetryAfterRefresh()
        if resp.status_code >= 400:
            code = ""
            hint = ""
            try:
                body = resp.json()
                detail = body.get("error") or body.get("detail") or resp.text
                code = body.get("code", "") or ""
                hint = body.get("hint", "") or ""
            except Exception:
                detail = resp.text
            raise APIError(resp.status_code, str(detail), code=code, hint=hint)

from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


def site_map(url: str = "", search: str | None = None) -> dict[str, Any]:
    try:
        key = os.getenv("FIRECRAWL_API_KEY")
        if not key:
            raise RuntimeError("Missing FIRECRAWL_API_KEY env var")

        if not url:
            return err("site_map", "url parameter cannot be empty")

        body: dict[str, Any] = {"url": url}
        if search:
            body["search"] = search

        response = requests.post(
            "https://api.firecrawl.dev/v1/map",
            json=body,
            headers={"Authorization": f"Bearer {key}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        links = response.json().get("links", [])

        items = [{
            "title": link,
            "url": link,
            "source": domain(link),
            "summary": f"Sub-link found on {domain(url)}",
        } for link in links[:20]]

        return {"tool": "site_map", "url": url, "search": search, "items": items}
    except Exception as exc:
        return err("site_map", exc)

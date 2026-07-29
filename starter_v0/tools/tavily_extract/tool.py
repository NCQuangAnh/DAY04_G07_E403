from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


def tavily_extract(urls: list[str] | str = "") -> dict[str, Any]:
    try:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("Missing TAVILY_API_KEY env var")

        url_list = [urls] if isinstance(urls, str) else list(urls or [])
        url_list = [u.strip() for u in url_list if u and u.strip()]
        if not url_list:
            return err("tavily_extract", "urls parameter cannot be empty")

        response = requests.post(
            "https://api.tavily.com/extract",
            json={"urls": url_list},
            headers={"Authorization": f"Bearer {key}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        items = []
        for result in data.get("results", []):
            items.append({
                "title": result.get("url"),
                "url": result.get("url"),
                "source": domain(result.get("url", "")),
                "summary": (result.get("raw_content") or "")[:4000],
            })

        return {"tool": "tavily_extract", "urls": url_list, "items": items}
    except Exception as exc:
        return err("tavily_extract", exc)

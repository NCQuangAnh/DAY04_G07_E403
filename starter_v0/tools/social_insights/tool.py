from __future__ import annotations

from collections import Counter
import re
from typing import Any

from tools._shared import err, terms
from tools.social_search.tool import _tweet_item, _twitter_get


_HASHTAG_RE = re.compile(r"(?<!\w)#([\w]+)", re.UNICODE)


def _limit(value: int) -> int:
    """Keep the live request and the returned payload at a safe size."""
    try:
        return max(1, min(int(value), 20))
    except (TypeError, ValueError):
        return 5


def _number(value: Any) -> int:
    """Normalise API metrics, which can be absent, strings, or numbers."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def analyze_social_trends(
    query: str = "", search_type: str = "Top", limit: int = 10
) -> dict[str, Any]:
    """Search X and extract transparent, rule-based conversation signals."""
    try:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("query must not be empty")
        if search_type not in {"Latest", "Top"}:
            raise ValueError("search_type must be either 'Latest' or 'Top'")

        requested_limit = _limit(limit)
        data = _twitter_get(
            "/search.php", {"query": clean_query, "search_type": search_type}
        )
        raw_posts = data.get("timeline") or data.get("tweets") or []
        raw_posts = [post for post in raw_posts if isinstance(post, dict)][
            :requested_limit
        ]
        items = [_tweet_item(post) for post in raw_posts]

        hashtags: Counter[str] = Counter()
        keywords: Counter[str] = Counter()
        total_favorites = total_retweets = total_views = 0
        for post, item in zip(raw_posts, items):
            text = item.get("summary") or ""
            hashtags.update(f"#{tag.lower()}" for tag in _HASHTAG_RE.findall(text))
            keywords.update(terms(text))
            metrics = item.get("metrics") or {}
            total_favorites += _number(metrics.get("favorites"))
            total_retweets += _number(metrics.get("retweets"))
            total_views += _number(metrics.get("views"))

        return {
            "tool": "analyze_social_trends",
            "query": clean_query,
            "search_type": search_type,
            "items": items,
            "insights": {
                "post_count": len(items),
                "top_hashtags": [
                    {"tag": tag, "count": count}
                    for tag, count in hashtags.most_common(5)
                ],
                "top_keywords": [
                    {"term": term, "count": count}
                    for term, count in keywords.most_common(8)
                ],
                "engagement": {
                    "favorites": total_favorites,
                    "retweets": total_retweets,
                    "views": total_views,
                },
            },
        }
    except Exception as exc:
        return err("analyze_social_trends", exc)

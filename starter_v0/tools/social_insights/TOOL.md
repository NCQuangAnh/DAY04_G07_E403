---
name: social_insights
track: core
kind: live_api
provider: RapidAPI Twitter API45
requires_env: [RAPIDAPI_KEY, RAPIDAPI_TWITTER_HOST]
inputs: [query, search_type, limit]
outputs: [items, insights]
side_effect: false
---
# social_insights

Searches public X posts for a topic and returns a compact, deterministic trend
summary. Use this when the user asks what themes, hashtags, or engagement are
appearing in a social-media conversation. Use `social_search` instead when the
user only needs the individual posts.

`search_type` is either `Latest` or `Top`; `limit` is capped at 20 so the
summary remains readable.

---
name: site_map
track: core
kind: live_api
provider: Firecrawl Map API
requires_env: [FIRECRAWL_API_KEY]
inputs: [url, search]
outputs: [items]
side_effect: false
---
# Tool: `site_map`

## Purpose
Khám phá và liệt kê danh sách cây liên kết (sitemap / sub-links) của một website bằng Firecrawl Map API. Dùng khi cần tìm cấu trúc đường dẫn các trang con thuộc cùng một domain.

## Contract
- **Inputs**:
  - `url` (str, required): Trang web gốc cần quét sơ đồ liên kết (vd: `https://example.com`).
  - `search` (str, optional): Từ khóa để lọc bớt đường dẫn liên quan.
- **Outputs**:
  - `tool`: `"site_map"`
  - `url`: Đã quét.
  - `items`: Danh sách các item chứa `title`, `url`, `source`.
  - `error`: `None` nếu thành công, hoặc chuỗi thông báo lỗi nếu thất bại.

## Environment Variables
- `FIRECRAWL_API_KEY`: API key của Firecrawl (bắt buộc).

---
name: tavily_extract
track: core
kind: live_api
provider: Tavily Extract API
requires_env: [TAVILY_API_KEY]
inputs: [urls]
outputs: [items]
side_effect: false
---
# Tool: `tavily_extract`

## Purpose
Trích xuất nội dung văn bản chi tiết từ một hoặc nhiều địa chỉ URL cụ thể bằng Tavily Extract API. Dùng khi cần đọc sâu nội dung của các liên kết web được cung cấp.

## Contract
- **Inputs**:
  - `urls` (list[str] hoặc str, required): Danh sách các địa chỉ URL cần trích xuất nội dung.
- **Outputs**:
  - `tool`: `"tavily_extract"`
  - `urls`: Danh sách URL đã xử lý.
  - `items`: Danh sách các item chứa `url`, `title`, `summary` (nội dung trích xuất).
  - `error`: `None` nếu thành công, hoặc chuỗi thông báo lỗi nếu thất bại.

## Environment Variables
- `TAVILY_API_KEY`: API key của Tavily (bắt buộc).

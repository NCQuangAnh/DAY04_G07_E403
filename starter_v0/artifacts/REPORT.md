# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 16:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: G07 (E403)
- Members: Quang Anh (Lead/Prompt), Trung (Tool Builder), Minh (Eval), Tuấn (UI/Deploy), Phương (QA/Report)
- Provider/model: openrouter / openai/gpt-4o-mini

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent tiếng Việt: lấy bài đăng X/Twitter theo tài khoản hoặc theo từ khóa, tra cứu tin tức/web, đọc và trích xuất nội dung URL cụ thể, khám phá sitemap của 1 domain, tổng hợp kết quả thành digest, và gửi bản tin lên Telegram sau khi hỏi xác nhận. Agent luôn hỏi lại khi thiếu thông tin (tài khoản/URL/chủ đề) thay vì tự đoán, và từ chối các yêu cầu ngoài phạm vi research (toán, code...).

**Link dùng thử (truy cập được trong showdown):**

> Chạy `streamlit run app.py` rồi `cloudflared tunnel --url http://localhost:8501`, dán URL `trycloudflare.com` sinh ra vào đây trước giờ showdown.
>
> URL: _(điền sau khi Tuấn mở tunnel)_

## A2. Tool agent có

> Liệt kê các tool agent đang dùng. Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin / xác nhận trước hành động gửi | không |
| timeline | lấy bài đăng gần đây của 1 tài khoản X/Twitter | không |
| social_search | tìm bài đăng X/Twitter theo từ khóa | không |
| social_insights | phân tích hashtag/từ khóa lặp lại/tương tác nổi bật trên X/Twitter | **có** |
| lookup | tra cứu web / tin tức chung | không |
| fetch | đọc nội dung 1 URL cụ thể | không |
| tavily_extract | trích xuất nội dung chi tiết từ 1 hoặc nhiều URL | **có** |
| site_map | khám phá sitemap/sub-link của 1 domain | **có** |
| format | trình bày dữ liệu đã có thành digest | không |
| send | gửi bản tin lên Telegram (cần xác nhận trước) | không (bonus có sẵn) |

## A3. Câu hỏi mẫu để thử

1. "Tweet mới nhất của Sam Altman là gì?" — gọi tool chính (`timeline`).
2. "Tóm tắt 5 tweet mới nhất giúp mình" — thiếu tài khoản → agent hỏi lại (`clarify`).
3. "Tìm trên web tin AI hôm nay và tìm thêm tweet về AI." — multi-tool (`lookup` + `social_search` song song).
4. "Phân tích hashtag nổi bật về OpenAI trên X" — dùng tool mới `social_insights`.
5. "Đăng bản tin này lên Telegram giúp mình" — boundary xác nhận trước khi gửi (`clarify` yes/no).

## A4. Kịch bản demo đã rehearse

> Chuẩn bị 3–5 scenario. Mỗi scenario cần cho thấy tool đã làm gì và một thay đổi cụ thể giữa các version.

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| "Tweet mới nhất của Sam Altman là gì?" | `timeline(screenname="sama", limit=1)` | Routing cơ bản, pass ở mọi version (v0→v2) | `runs/v2_B_base_openrouter_20260729T163506626873.json` case R01 |
| "Tóm tắt 5 tweet mới nhất giúp mình" | v0: tự đoán, gọi `timeline`/`social_search` ngay. v2: gọi `clarify(response_type="text")` hỏi tài khoản nào | v0 FAIL (missing_info) → v2 PASS nhờ rule "PHẢI gọi clarify" | v0: `runs/v0_B_base_openrouter_20260729T154751126566.json` case R10 · v2: `runs/v2_B_base_openrouter_20260729T163506626873.json` case R10 |
| "Tìm trên web tin AI hôm nay và tìm thêm tweet về AI." | Gọi song song `lookup(query="AI", topic="news", timeframe="day")` + `social_search(query="AI")`, giữ nguyên từ khóa | v0 FAIL (tự đổi query thành "AI news") → v2 PASS | `runs/v2_B_base_openrouter_20260729T163506626873.json` case R13 |

**Known gap để nói thẳng với coach (minh bạch, không né):** case "Đăng bản tin này lên Telegram giúp mình" (R12) vẫn còn flaky ở v2 — đôi khi agent hỏi nội dung bản tin (`clarify text`) trước thay vì hỏi xác nhận gửi (`clarify yes_no`). Đây là hypothesis cho v3 sau khi nhận feedback từ coach.

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline |  |  |  |  |  |
| v1 |  |  |  |  |  |  |
| v2 |  |  |  |  |  |  |
| v3 |  |  |  |  |  |  |

## B2. Failure analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
|  |  |  |  |  |

## B3. Team eval cases

List the 10 cases added to `data/eval_group.json`:

- 5 single-turn
- 5 multi-turn

This section is for the mandatory team-authored eval set. Optional built-ins do
not belong here.

File template để trống có chủ đích; nhóm phải tự thiết kế đủ 10 case.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
|  |  |  |  |

## B4. Live chat evidence

Use `transcripts/*.transcript.json`.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Tool capability evidence

Phân loại rõ tool mới bắt buộc, optional built-in và tool đủ điều kiện bonus. Chỉ ghi Telegram/PDF nếu nhóm thực sự dùng; base report không cần chúng.

UI is core deliverable, not bonus. Do not list it here.

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên |  |  |  |
| Optional built-in |  |  |  |
| Bonus: tool mới thứ 4 trở đi |  |  |  |

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
- Which fixes belonged in `tools.yaml`?
- Which failure needed manual review instead of automatic grading?
- What would you improve next?

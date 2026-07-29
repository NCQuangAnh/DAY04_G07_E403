from __future__ import annotations

import html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
RUNS_DIR = ROOT / "runs"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"

PROVIDER_KEYS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

SAMPLE_PROMPTS = [
    "Tin tức AI hôm nay có gì nổi bật?",
    "Lấy 3 bài đăng mới nhất của Sam Altman",
    "Tóm tắt bài này giúp mình: https://openai.com/news/",
]

SAMPLE_PROMPTS.append("Phân tích hashtag, từ khóa và tương tác nổi bật về OpenAI trên X")
SAMPLE_PROMPTS.append("Trích xuất nội dung chi tiết bài viết từ URL: https://example.com")
SAMPLE_PROMPTS.append("Liệt kê sơ đồ các trang con (sitemap) của domain https://example.com")


st.set_page_config(
    page_title="Relay · Research Agent",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #14211c;
            --muted: #65736d;
            --line: #dfe8e3;
            --paper: #f7faf8;
            --mint: #dff7eb;
            --green: #16784c;
            --green-dark: #0b5133;
            --amber: #f2b84b;
        }
        .stApp {
            background:
                radial-gradient(circle at 78% -10%, rgba(173, 238, 208, .35), transparent 26rem),
                #f7faf8;
            color: var(--ink);
        }
        [data-testid="stSidebar"] {
            background: #10241b;
            border-right: 1px solid rgba(255,255,255,.08);
        }
        [data-testid="stSidebar"] * { color: #eff8f3; }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stSlider label {
            color: #a9beb3 !important;
        }
        [data-testid="stSidebar"] input {
            color: #eff8f3 !important;
            -webkit-text-fill-color: #eff8f3 !important;
            caret-color: #7ee2ae !important;
        }
        [data-testid="stSidebar"] input::placeholder {
            color: #91a99d !important;
            -webkit-text-fill-color: #91a99d !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"],
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] {
            color: #eff8f3 !important;
            background-color: #091812 !important;
            border-color: #29483a !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] * {
            color: #eff8f3 !important;
            -webkit-text-fill-color: #eff8f3 !important;
        }
        /* Streamlit renders the selected option in a combobox input. */
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] input,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input[role="combobox"] {
            color: #eff8f3 !important;
            -webkit-text-fill-color: #eff8f3 !important;
            caret-color: #7ee2ae !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] svg {
            fill: #a9beb3 !important;
        }
        [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {
            background: #091812 !important;
            border-color: #29483a !important;
        }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #a9beb3 !important;
        }
        [data-testid="stSidebar"] [data-testid="stCodeBlock"] {
            background: #f7faf8 !important;
            border: 1px solid #d7e2dc !important;
        }
        [data-testid="stSidebar"] [data-testid="stCodeBlock"] pre,
        [data-testid="stSidebar"] [data-testid="stCodeBlock"] code,
        [data-testid="stSidebar"] [data-testid="stCodeBlock"] span {
            color: #0b5133 !important;
            -webkit-text-fill-color: #0b5133 !important;
            background: #f7faf8 !important;
        }
        [data-testid="stSidebar"] [data-testid="stCodeBlock"] button,
        [data-testid="stSidebar"] [data-testid="stCodeBlock"] button * {
            color: #0b5133 !important;
            -webkit-text-fill-color: #0b5133 !important;
        }
        [data-testid="stSidebar"] .artifact-code {
            color: #0b5133 !important;
            background: #f7faf8;
            border: 1px solid #d7e2dc;
            border-radius: .55rem;
            padding: .75rem .85rem;
            margin: .35rem 0 .7rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: .76rem;
            font-weight: 700;
            line-height: 1.45;
            overflow-wrap: anywhere;
            -webkit-text-fill-color: #0b5133 !important;
        }
        .block-container {
            max-width: 1500px;
            padding-top: 1.7rem;
            padding-bottom: 3rem;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: .7rem;
            margin: .15rem 0 1.4rem;
        }
        .brand-mark {
            width: 2.1rem;
            height: 2.1rem;
            border-radius: .65rem;
            display: grid;
            place-items: center;
            background: #7ee2ae;
            color: #10241b !important;
            font-size: 1.25rem;
            font-weight: 800;
        }
        .brand-name {
            font-size: 1.08rem;
            font-weight: 750;
            letter-spacing: -.02em;
        }
        .brand-sub {
            color: #91a99d !important;
            font-size: .72rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .eyebrow {
            color: var(--green);
            font-weight: 750;
            letter-spacing: .1em;
            text-transform: uppercase;
            font-size: .72rem;
            margin-bottom: .45rem;
        }
        .hero-title {
            font-size: clamp(2rem, 4vw, 3.55rem);
            line-height: .98;
            letter-spacing: -.055em;
            font-weight: 780;
            max-width: 760px;
            margin-bottom: .8rem;
        }
        .hero-copy {
            color: var(--muted);
            max-width: 690px;
            font-size: 1.02rem;
            line-height: 1.6;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: .45rem;
            border: 1px solid var(--line);
            background: rgba(255,255,255,.75);
            border-radius: 999px;
            padding: .38rem .72rem;
            font-size: .78rem;
            color: var(--muted);
            margin: .2rem .25rem .2rem 0;
        }
        .status-dot {
            width: .48rem;
            height: .48rem;
            border-radius: 50%;
            background: #1fa96b;
            box-shadow: 0 0 0 3px rgba(31,169,107,.13);
        }
        .status-dot.off {
            background: #d98a2b;
            box-shadow: 0 0 0 3px rgba(217,138,43,.13);
        }
        .meta-card {
            border: 1px solid var(--line);
            background: rgba(255,255,255,.72);
            border-radius: 1rem;
            padding: 1rem 1.1rem;
            min-height: 86px;
        }
        .meta-label {
            color: var(--muted);
            font-size: .7rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-bottom: .35rem;
        }
        .meta-value {
            font-size: .92rem;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        .section-title {
            font-size: .75rem;
            text-transform: uppercase;
            letter-spacing: .1em;
            color: var(--muted);
            font-weight: 750;
            margin: 1rem 0 .65rem;
        }
        .empty-state {
            border: 1px dashed #bfd0c7;
            border-radius: 1rem;
            padding: 2.2rem 1.3rem;
            text-align: center;
            color: var(--muted);
            background: rgba(255,255,255,.38);
        }
        .trace-head {
            display: flex;
            justify-content: space-between;
            gap: .75rem;
            align-items: center;
            border-bottom: 1px solid var(--line);
            padding-bottom: .65rem;
            margin-bottom: .55rem;
        }
        .trace-tool {
            color: var(--green-dark);
            background: var(--mint);
            border-radius: .45rem;
            padding: .18rem .48rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: .76rem;
            font-weight: 700;
        }
        .trace-ok, .trace-error {
            font-size: .7rem;
            border-radius: 999px;
            padding: .18rem .48rem;
            font-weight: 700;
        }
        .trace-ok { color: #0a7043; background: #dcf8e9; }
        .trace-error { color: #a1422d; background: #fde9e3; }
        [data-testid="stChatMessage"] {
            border: 1px solid var(--line);
            background: rgba(255,255,255,.72);
            border-radius: 1rem;
            padding: .35rem .55rem;
            margin-bottom: .7rem;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] span {
            color: var(--ink) !important;
        }
        [data-testid="stChatMessage"] a {
            color: var(--green) !important;
        }
        [data-testid="stMetric"] {
            background: rgba(255,255,255,.72);
            border: 1px solid var(--line);
            border-radius: .9rem;
            padding: .85rem 1rem;
        }
        .stButton > button {
            border-radius: .7rem;
            border: 1px solid #26342e;
            background: #141c19;
            color: #f4fbf7 !important;
            font-weight: 650;
        }
        .stButton > button p,
        .stButton > button span {
            color: #f4fbf7 !important;
        }
        .stButton > button:hover {
            border-color: #16784c;
            background: #1d2b25;
            color: #ffffff !important;
        }
        .stButton > button[kind="primary"] {
            background: var(--green-dark);
            border-color: var(--green-dark);
        }
        [data-testid="stExpander"] details {
            border-color: #d7e2dc !important;
            background: rgba(255,255,255,.58);
        }
        [data-testid="stExpander"] details > summary {
            background: #edf4f0 !important;
            color: var(--ink) !important;
        }
        [data-testid="stExpander"] details > summary * {
            color: var(--ink) !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] details {
            border-color: #365345 !important;
            background: transparent;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] details > summary {
            background: transparent !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] details > summary * {
            color: #eff8f3 !important;
        }
        code { color: #185c3e; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


def current_artifact(version: str) -> dict[str, str]:
    artifact = build_artifact_version(version, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    return artifact_version_dict(artifact)


def session_signature(config: dict[str, Any]) -> tuple[Any, ...]:
    return (
        config["provider"],
        config["model"],
        config["version"],
        config["history_window"],
        config["max_tool_rounds"],
    )


def reset_session() -> None:
    for key in ("history", "turns", "transcript", "transcript_path", "session_signature"):
        st.session_state.pop(key, None)


def ensure_session(config: dict[str, Any], provider: Any) -> None:
    signature = session_signature(config)
    if st.session_state.get("session_signature") == signature and "transcript" in st.session_state:
        return

    artifact = current_artifact(config["version"])
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join(
        [
            safe_slug(config["version"]),
            safe_slug(config["provider"]),
            timestamp,
        ]
    )
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    selected_model = config["model"] or getattr(provider, "default_model", None)

    st.session_state.history = []
    st.session_state.turns = []
    st.session_state.transcript_path = transcript_path
    st.session_state.session_signature = signature
    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact,
        "provider": config["provider"],
        "model": selected_model,
        "system_prompt": str(SYSTEM_PROMPT_PATH),
        "tools": str(TOOLS_PATH),
        "history_window": config["history_window"],
        "max_tool_rounds": config["max_tool_rounds"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }


def render_sidebar() -> tuple[str, dict[str, Any]]:
    with st.sidebar:
        st.markdown(
            """
            <div class="brand">
                <div class="brand-mark">R</div>
                <div>
                    <div class="brand-name">Relay</div>
                    <div class="brand-sub">Research agent lab</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Điều hướng",
            ["Playground", "Run evidence", "Transcripts"],
            label_visibility="collapsed",
        )
        st.divider()

        st.caption("CẤU HÌNH PHIÊN")
        provider = st.selectbox(
            "Provider",
            ["openrouter", "openai", "anthropic", "gemini"],
            format_func=lambda value: value.title(),
        )
        model = st.text_input("Model (tùy chọn)", placeholder="Dùng model mặc định")
        version = st.text_input("Artifact version", value="v0")

        with st.expander("Nâng cao"):
            history_window = st.slider("History window", 1, 12, 5)
            max_tool_rounds = st.slider("Max tool rounds", 1, 8, 4)

        config = {
            "provider": provider,
            "model": model.strip() or None,
            "version": version.strip() or "v0",
            "history_window": history_window,
            "max_tool_rounds": max_tool_rounds,
        }

        key_name = PROVIDER_KEYS[provider]
        connected = bool(os.getenv(key_name))
        state = "Đã nhận API key" if connected else f"Thiếu {key_name}"
        dot_class = "" if connected else " off"
        st.markdown(
            f'<div class="status-pill"><span class="status-dot{dot_class}"></span>{html.escape(state)}</div>',
            unsafe_allow_html=True,
        )

        if st.button("＋ Phiên mới", use_container_width=True):
            reset_session()
            st.rerun()

        st.divider()
        st.caption("ARTIFACT ĐANG CHẠY")
        artifact = current_artifact(config["version"])
        with st.expander("Công cụ khả dụng"):
            for declaration in load_tool_declarations(TOOLS_PATH):
                name = declaration.get("name", "unknown")
                description = declaration.get("description", "")
                st.markdown(f"**{html.escape(name)}**")
                st.caption(description)
        st.markdown(
            f'<div class="artifact-code">{html.escape(artifact["artifact_version"])}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Prompt · {artifact['prompt_hash'][:12]}")
        st.caption(f"Tools · {artifact['tools_hash'][:12]}")

    return page, config


def render_header(config: dict[str, Any], title: str, copy: str) -> None:
    connected = bool(os.getenv(PROVIDER_KEYS[config["provider"]]))
    dot_class = "" if connected else " off"
    st.markdown(
        f"""
        <div class="eyebrow">Evidence-first research</div>
        <div class="hero-title">{html.escape(title)}</div>
        <div class="hero-copy">{html.escape(copy)}</div>
        <div style="margin-top:.8rem">
            <span class="status-pill"><span class="status-dot{dot_class}"></span>{html.escape(config["provider"].title())}</span>
            <span class="status-pill">Version&nbsp; <strong>{html.escape(config["version"])}</strong></span>
            <span class="status-pill">{len(load_tool_declarations(TOOLS_PATH))} tools</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_meta_cards(transcript: dict[str, Any] | None, config: dict[str, Any]) -> None:
    artifact = current_artifact(config["version"])
    values = [
        (
            "Artifact version",
            transcript.get("artifact_version") if transcript else artifact["artifact_version"],
        ),
        ("Transcript", transcript.get("transcript_id") if transcript else "Tạo sau tin nhắn đầu tiên"),
        ("Model", (transcript or {}).get("model") or config["model"] or "Provider default"),
    ]
    columns = st.columns(3)
    for column, (label, value) in zip(columns, values):
        with column:
            st.markdown(
                f"""
                <div class="meta-card">
                    <div class="meta-label">{html.escape(label)}</div>
                    <div class="meta-value">{html.escape(str(value))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def event_has_error(event: dict[str, Any]) -> bool:
    result = event.get("result")
    return isinstance(result, dict) and bool(result.get("error"))


def render_rounds(turn: dict[str, Any], *, key_prefix: str) -> None:
    rounds = turn.get("rounds", [])
    if not rounds:
        st.caption("Không có tool round trong lượt này.")
        return

    for round_record in rounds:
        round_number = round_record.get("round", "—")
        calls = round_record.get("tool_calls", [])
        results = round_record.get("tool_results", [])
        label = f"Round {round_number} · {len(calls)} tool call"
        with st.expander(label, expanded=round_number == 1):
            assistant_text = round_record.get("assistant_text")
            if assistant_text:
                st.caption("Model reasoning / message")
                st.write(assistant_text)

            if not calls:
                st.caption("Model trả lời trực tiếp, không gọi tool.")
                continue

            for index, call in enumerate(calls):
                event = results[index] if index < len(results) else {
                    "tool": call.get("name"),
                    "args": call.get("args", {}),
                    "result": {"error": "missing_result"},
                }
                has_error = event_has_error(event)
                badge_class = "trace-error" if has_error else "trace-ok"
                badge_text = "ERROR" if has_error else "SUCCESS"
                st.markdown(
                    f"""
                    <div class="trace-head">
                        <span class="trace-tool">{html.escape(str(call.get("name", "unknown")))}</span>
                        <span class="{badge_class}">{badge_text}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                args_tab, result_tab = st.tabs(["Arguments", "Result"])
                with args_tab:
                    st.json(call.get("args", {}), expanded=True)
                with result_tab:
                    st.json(event.get("result"), expanded=False)


def render_conversation(turns: list[dict[str, Any]]) -> None:
    if not turns:
        st.markdown(
            """
            <div class="empty-state">
                <strong>Chưa có hội thoại</strong><br>
                Chọn một câu hỏi mẫu hoặc nhập yêu cầu bên dưới để bắt đầu.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for turn in turns:
        with st.chat_message("user"):
            st.write(turn.get("user", ""))
        with st.chat_message("assistant"):
            if turn.get("status") == "provider_error":
                st.error(turn.get("error", "Provider error"))
            else:
                st.markdown(turn.get("assistant_text") or "_Không có nội dung trả lời._")
            tool_count = len(turn.get("tool_events", []))
            if tool_count:
                st.caption(f"{tool_count} tool event · {turn.get('status', 'unknown')}")


def run_user_turn(prompt: str, config: dict[str, Any]) -> None:
    try:
        provider = make_provider(config["provider"])
    except Exception as exc:
        st.error(f"Không thể khởi tạo provider: {type(exc).__name__}: {exc}")
        return

    ensure_session(config, provider)
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_PATH)
    openai_tools = to_openai_tools(declarations)
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, config["history_window"]),
        {"role": "user", "content": prompt},
    ]
    turn_record: dict[str, Any] = {
        "turn_index": len(st.session_state.turns) + 1,
        "started_at": now_iso(),
        "user": prompt,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    try:
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=config["model"],
            max_tool_rounds=config["max_tool_rounds"],
        )
        turn_record.update(result)
        assistant_text = result["assistant_text"]
        st.session_state.history.extend(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_text},
            ]
        )
    except Exception as exc:
        turn_record.update(
            {
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

    turn_record["ended_at"] = now_iso()
    st.session_state.turns.append(turn_record)
    st.session_state.transcript["turns"].append(turn_record)
    write_transcript(st.session_state.transcript_path, st.session_state.transcript)


def render_playground(config: dict[str, Any]) -> None:
    render_header(
        config,
        "Research, with the receipts.",
        "Đặt câu hỏi, theo dõi từng quyết định gọi tool và lưu lại toàn bộ bằng chứng theo đúng artifact version.",
    )
    st.write("")
    active_transcript = st.session_state.get("transcript")
    render_meta_cards(active_transcript, config)
    if (
        active_transcript
        and st.session_state.get("session_signature") != session_signature(config)
    ):
        st.warning(
            "Cấu hình sidebar đã thay đổi. Tin nhắn tiếp theo sẽ bắt đầu một transcript mới "
            "để không trộn bằng chứng giữa các version."
        )

    st.markdown('<div class="section-title">Thử nhanh một scenario</div>', unsafe_allow_html=True)
    sample_columns = st.columns(len(SAMPLE_PROMPTS))
    selected_sample: str | None = None
    for index, (column, sample) in enumerate(zip(sample_columns, SAMPLE_PROMPTS)):
        with column:
            if st.button(sample, key=f"sample_{index}", use_container_width=True):
                selected_sample = sample

    st.divider()
    chat_column, trace_column = st.columns([1.35, 1], gap="large")
    turns = st.session_state.get("turns", [])

    with chat_column:
        st.markdown('<div class="section-title">Conversation</div>', unsafe_allow_html=True)
        render_conversation(turns)

    with trace_column:
        st.markdown('<div class="section-title">Live tool trace</div>', unsafe_allow_html=True)
        if not turns:
            st.markdown(
                """
                <div class="empty-state">
                    <strong>Trace sẽ xuất hiện tại đây</strong><br>
                    Mỗi round gồm tool name, arguments, status và result/error.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for turn in reversed(turns):
                with st.container(border=True):
                    st.caption(
                        f"TURN {turn.get('turn_index', '—')} · "
                        f"{str(turn.get('status', 'unknown')).upper()}"
                    )
                    render_rounds(turn, key_prefix=f"live_{turn.get('turn_index')}")

    typed_prompt = st.chat_input("Hỏi agent hoặc đưa một URL cần nghiên cứu…")
    prompt = typed_prompt or selected_sample
    if prompt:
        with st.spinner("Agent đang lập kế hoạch và chạy tool…"):
            run_user_turn(prompt, config)
        st.rerun()


def discover_transcripts() -> list[Path]:
    paths = list(TRANSCRIPTS_DIR.glob("*.transcript.json"))
    sample_dir = ROOT / "samples" / "transcripts"
    paths.extend(sample_dir.glob("*.transcript.json"))
    return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)


def render_transcripts(config: dict[str, Any]) -> None:
    render_header(
        config,
        "Every turn, inspectable.",
        "Mở lại transcript đã lưu để kiểm tra hội thoại, tool trace và artifact version khi demo hoặc review lỗi.",
    )
    st.write("")
    paths = discover_transcripts()
    if not paths:
        st.info("Chưa có transcript. Hãy chạy ít nhất một lượt trong Playground.")
        return

    selected = st.selectbox(
        "Chọn transcript",
        paths,
        format_func=lambda path: path.name,
    )
    try:
        transcript = load_json(selected)
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"Không đọc được transcript: {exc}")
        return

    values = [
        ("Artifact version", transcript.get("artifact_version", "—")),
        ("Provider / model", f"{transcript.get('provider', '—')} · {transcript.get('model', '—')}"),
        ("Updated", transcript.get("updated_at", transcript.get("created_at", "—"))),
    ]
    columns = st.columns(3)
    for column, (label, value) in zip(columns, values):
        with column:
            st.markdown(
                f"""
                <div class="meta-card">
                    <div class="meta-label">{html.escape(label)}</div>
                    <div class="meta-value">{html.escape(str(value))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    chat_column, trace_column = st.columns([1.25, 1], gap="large")
    turns = transcript.get("turns", [])
    with chat_column:
        st.markdown('<div class="section-title">Transcript</div>', unsafe_allow_html=True)
        render_conversation(turns)
    with trace_column:
        st.markdown('<div class="section-title">Trace</div>', unsafe_allow_html=True)
        for turn in turns:
            with st.container(border=True):
                st.caption(f"TURN {turn.get('turn_index', '—')} · {turn.get('status', 'unknown')}")
                render_rounds(turn, key_prefix=f"archive_{turn.get('turn_index')}")

    with st.expander("Raw transcript JSON"):
        st.json(transcript, expanded=False)


def discover_runs() -> list[Path]:
    return sorted(
        RUNS_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def render_run_evidence(config: dict[str, Any]) -> None:
    render_header(
        config,
        "Measure the improvement.",
        "Đọc bằng chứng từ run JSON: metric tổng, hash artifact và từng case fail để so sánh các vòng v0 → v3.",
    )
    st.write("")
    paths = discover_runs()
    if not paths:
        st.info("Chưa có run JSON trong thư mục `runs/`.")
        return

    selected = st.selectbox("Chọn eval run", paths, format_func=lambda path: path.name)
    try:
        run = load_json(selected)
    except (OSError, json.JSONDecodeError) as exc:
        st.error(f"Không đọc được run: {exc}")
        return

    summary = run.get("summary", {})
    metric_columns = st.columns(4)
    metrics = [
        ("Case accuracy", format_percent(summary.get("case_accuracy"))),
        ("Tool routing", format_percent(summary.get("tool_routing_accuracy"))),
        ("Arguments", format_percent(summary.get("argument_accuracy"))),
        ("Multi-turn", format_percent(summary.get("multiturn_accuracy"))),
    ]
    for column, (label, value) in zip(metric_columns, metrics):
        with column:
            st.metric(label, value)

    st.write("")
    artifact_columns = st.columns(3)
    artifact_values = [
        ("Artifact", run.get("artifact_version", "—")),
        ("Run", run.get("run_id", selected.stem)),
        (
            "Coverage",
            f"{summary.get('measured_cases', '—')} / {summary.get('total_cases', '—')} measured",
        ),
    ]
    for column, (label, value) in zip(artifact_columns, artifact_values):
        with column:
            st.markdown(
                f"""
                <div class="meta-card">
                    <div class="meta-label">{html.escape(label)}</div>
                    <div class="meta-value">{html.escape(str(value))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    results = run.get("results", [])
    failed = [item for item in results if not item.get("result", {}).get("passed", False)]
    st.markdown(
        f'<div class="section-title">Failure review · {len(failed)} case</div>',
        unsafe_allow_html=True,
    )
    if not failed:
        st.success("Không có case fail trong run này.")
    else:
        table_rows = []
        for item in failed:
            result = item.get("result", {})
            calls = result.get("actual_tool_calls", [])
            table_rows.append(
                {
                    "Case": item.get("id"),
                    "Failure type": result.get("failure_type") or item.get("failure_type"),
                    "Observed mismatch": result.get("observed_mismatch"),
                    "Actual tools": ", ".join(call.get("name", "?") for call in calls) or "none",
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        for item in failed:
            result = item.get("result", {})
            with st.expander(f"{item.get('id')} · {result.get('failure_type') or 'failed'}"):
                left, right = st.columns(2)
                with left:
                    st.caption("Expected")
                    st.json(item.get("expect", {}), expanded=True)
                with right:
                    st.caption("Observed")
                    st.json(
                        {
                            "tool_calls": result.get("actual_tool_calls", []),
                            "mismatch": result.get("observed_mismatch"),
                            "failures": result.get("failures", []),
                        },
                        expanded=True,
                    )

    with st.expander("Run metadata & hashes"):
        st.json(
            {
                "version": run.get("version"),
                "suite": run.get("suite"),
                "provider": run.get("provider"),
                "model": run.get("model"),
                "prompt_hash": run.get("prompt_hash"),
                "tools_hash": run.get("tools_hash"),
                "generated_at": run.get("generated_at"),
                "provider_error_cases": summary.get("provider_error_cases"),
            },
            expanded=True,
        )


def main() -> None:
    inject_styles()
    page, config = render_sidebar()

    if page == "Playground":
        render_playground(config)
    elif page == "Run evidence":
        render_run_evidence(config)
    else:
        render_transcripts(config)


if __name__ == "__main__":
    main()

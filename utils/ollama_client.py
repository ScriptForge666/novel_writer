# utils/ollama_client.py
import json
import requests
from typing import List, Dict, Tuple
from config import OLLAMA_HOST, MODEL_NAME

# --------------------------------------------------------------
# 控制是否在极端情况下把 thinking 当作后备（默认关闭）
# --------------------------------------------------------------
USE_THINKING_AS_BACKUP = False   # 设为 True 才会启用方案 B

# --------------------------------------------------------------
# 1️⃣ 低层请求 helpers
# --------------------------------------------------------------
def _post_chat_once(payload: dict) -> dict:
    """一次性非流式请求（fallback）"""
    url = f"{OLLAMA_HOST}/api/chat"
    resp = requests.post(url, json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()


def _post_chat_stream(payload: dict):
    """
    流式（SSE）请求。
    逐行读取 data: {...}，yield 已解析的 dict。
    """
    url = f"{OLLAMA_HOST}/api/chat"
    resp = requests.post(url, json=payload, stream=True, timeout=180)
    resp.raise_for_status()

    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError:
            continue

        # 结束标记
        if line.strip() in ("data: [DONE]", "[DONE]"):
            break

        if line.startswith("data:"):
            json_part = line[5:].strip()
            try:
                yield json.loads(json_part)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Failed to decode SSE JSON chunk: {json_part!r} – {e}"
                )
        else:
            # 兼容极少出现的非 data 行
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


# --------------------------------------------------------------
# 2️⃣ 公共接口：chat()
# --------------------------------------------------------------
def chat(messages: List[Dict],
         max_tokens: int = 4000,
         temperature: float = 0.7) -> Tuple[str, int, int]:
    """
    流式读取模型回复，返回 (full_text, prompt_tokens, completion_tokens)。
    - 默认只拼接 `message.content`（方案 A）。
    - 若 `USE_THINKING_AS_BACKUP=True`，在极端情况下会把 `thinking` 作为后备（方案 B）。
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "max_gen": max_tokens,
            "num_predict": max_tokens,
            "stream": True          # 强制开启 SSE
        }
    }

    # ------------------- 尝试流式 -------------------
    try:
        gen = _post_chat_stream(payload)

        full_text = ""
        # 方案 B 需要收集所有 thinking，做后备
        backup_thinking = [] if USE_THINKING_AS_BACKUP else None

        prompt_tokens: int | None = None
        completion_tokens: int | None = None

        for chunk in gen:
            # 记录首次出现的 prompt token 计数
            if prompt_tokens is None:
                prompt_tokens = chunk.get("prompt_eval_count", 0)

            # --------------------------------------------------
            # 取内容
            # --------------------------------------------------
            msg = chunk.get("message")
            if isinstance(msg, dict):
                # ① 优先使用正式 content
                piece = msg.get("content", "")

                # ② 如果 content 仍为空，检查 "thinking"
                if not piece:
                    thinking_piece = msg.get("thinking", "")
                    if USE_THINKING_AS_BACKUP:
                        # 方案 B：收集全部 thinking 作为后备
                        backup_thinking.append(thinking_piece)
                    # 方案 A：直接忽略 thinking（不加入到 final 文本）
                    piece = ""   # 保持空，以免出现碎片
                full_text += piece
            else:
                # 老版返回的直接字段
                full_text += chunk.get("response", "")

            # --------------------------------------------------
            # 检查是否结束
            # --------------------------------------------------
            if chunk.get("done"):
                completion_tokens = chunk.get("eval_count", 0)
                if prompt_tokens is None:
                    prompt_tokens = chunk.get("prompt_eval_count", 0)
                break

        # ------------------- 流式结束后处理 -------------------
        if completion_tokens is None:
            # 未收到 done 标记的情况下，把已收集的 eval 计数设为 0
            completion_tokens = 0

        # 方案 B：若启用且最终文本仍为空，使用备份的 thinking
        if USE_THINKING_AS_BACKUP and not full_text.strip() and backup_thinking:
            full_text = "".join(backup_thinking)

        return (
            full_text,
            int(prompt_tokens or 0),
            int(completion_tokens or 0)
        )

    except Exception as stream_err:
        # ------------------- 流式失败 → 一次性回退 -------------------
        print("[Ollama] Stream mode failed, fallback to single‑shot request:")
        print("        ", stream_err)

        payload["options"]["stream"] = False
        raw = _post_chat_once(payload)

        # 兼容不同结构的返回
        msg = raw.get("message", {})
        final_text = msg.get("content", "")
        if not final_text:
            final_text = raw.get("response", "")

        prompt_tokens = raw.get("prompt_eval_count", 0)
        completion_tokens = raw.get("eval_count", 0)

        return (
            final_text,
            int(prompt_tokens or 0),
            int(completion_tokens or 0)
        )

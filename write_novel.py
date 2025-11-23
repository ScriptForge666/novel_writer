# write_novel.py
import json, time, traceback
from pathlib import Path
from tqdm import tqdm
from utils.ollama_client import chat
from config import (
    BIBLE_PATH, OUTLINE_PATH, CHAPTER_DIR, SUMMARY_DIR,
    TOKEN_BUDGET
)

# ---------- 预算统计 ----------
used_prompt = used_completion = 0
def update_usage(p: int, c: int):
    """累计 token，超预算则抛异常停止写作。"""
    global used_prompt, used_completion
    used_prompt += p
    used_completion += c
    if used_prompt + used_completion > TOKEN_BUDGET:
        raise RuntimeError(
            f"已超过 token 预算（{TOKEN_BUDGET:,}），当前使用 {used_prompt+used_completion:,}"
        )

# ---------- 读取资源 ----------
def load_bible() -> str:
    return BIBLE_PATH.read_text(encoding="utf-8")

def load_outline() -> list:
    return json.loads(OUTLINE_PATH.read_text(encoding="utf-8"))

def read_recent_summaries(k: int = 3) -> list:
    files = sorted(SUMMARY_DIR.glob("summary_*.md"))[-k:]
    return [f.read_text(encoding="utf-8") for f in files]

# ---------- Prompt 构造 ----------
def build_chapter_prompt(bible: str, recent_summaries: list, chap_info: dict) -> list:
    recent = "\n".join(recent_summaries) if recent_summaries else "(暂无摘要)"
    system_msg = {
        "role": "system",
        "content": "你是一名专业的中文长篇小说作者，请严格遵守下列设定。"
    }
    user_msg = {
        "role": "user",
        "content": f"""以下是全局设定（Story Bible）：
{bible}

以下是最近几章的摘要（帮助保持情节连贯）：
{recent}

请根据下面的章节信息写 **完整章节**，字数约 **{chap_info['target_words']}**，章节标题使用《{chap_info['title']}》。
关键情节点（必须全部出现）：
{json.dumps(chap_info['key_points'], ensure_ascii=False, indent=2)}

写作要求：
- 第三人称全知视角
- 句子长度 15‑25 字，语言略带诗意
- 章节结尾留下 1‑2 句开放式悬念

只返回章节正文（Markdown），不要出现任何说明文字。"""
    }
    return [system_msg, user_msg]

def build_summary_prompt(chapter_text: str) -> list:
    system_msg = {"role": "system", "content": "请把下面的章节压缩为 200‑300 字的摘要。"}
    user_msg = {
        "role": "user",
        "content": f"""章节正文如下（已去掉标题）：

{chapter_text}

请在摘要中包含：
1. 章节标题
2. 主人公当前的状态
3. 本章的主要冲突或转折
4. 为下一章留下的悬念

仅返回摘要（Markdown），不要出现其他文字。"""
    }
    return [system_msg, user_msg]

# ---------- 主循环 ----------
def main():
    bible = load_bible()
    outline = load_outline()

    for idx, chap in enumerate(tqdm(outline, desc="写作进度", unit="章")):
        chap_no = idx + 1

        # 1️⃣ 读取最近摘要（滚动记忆）
        recent_summaries = read_recent_summaries(k=3)

        # 2️⃣ 生成章节正文
        try:
            chapter_text, p_tok, c_tok = chat(
                messages=build_chapter_prompt(bible, recent_summaries, chap),
                max_tokens=8000,                 # 留出足够空间（32k 上下文窗口内部）
                temperature=0.7
            )
            update_usage(p_tok, c_tok)
        except Exception as e:
            print(f"\n⚠️ 第 {chap_no} 章生成失败：{e}")
            raise

        # 3️⃣ 保存章节
        chap_path = CHAPTER_DIR / f"chapter_{chap_no:03d}.md"
        chap_path.write_text(chapter_text, encoding="utf-8")

        # 4️⃣ 生成该章摘要（供后续章节记忆）
        try:
            summary_text, p2, c2 = chat(
                messages=build_summary_prompt(chapter_text),
                max_tokens=800,
                temperature=0.6
            )
            update_usage(p2, c2)
        except Exception as e:
            print(f"\n⚠️ 第 {chap_no} 章摘要生成失败：{e}")
            raise

        sum_path = SUMMARY_DIR / f"summary_{chap_no:03d}.md"
        sum_path.write_text(summary_text, encoding="utf-8")

        # 5️⃣ 小休息（防止本地速率限制，通常可忽略）
        time.sleep(0.2)

    # -------- 合并所有章节为完整小说 --------
    all_chapters = sorted(CHAPTER_DIR.glob("chapter_*.md"))
    novel_text = "\n\n".join(p.read_text(encoding="utf-8") for p in all_chapters)
    (Path(__file__).parent / "novel_full.md").write_text(novel_text, encoding="utf-8")

    print("\n✅ 完成！完整小说已保存为 novel_full.md")
    print(f"累计 token 使用量：Prompt={used_prompt:,}，Completion={used_completion:,}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n❌ 程序异常，已打印堆栈：")
        traceback.print_exc()

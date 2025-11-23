# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()                         # 读取 .env（如果存在）

# ----------------- Ollama 基础配置 -----------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL_NAME  = os.getenv("MODEL", "qwen3:8b")

# ----------------- 预算（token） -----------------
# 这里设一个大上限，防止因为循环错误无限生成
TOKEN_BUDGET = 10_000_000   # 约 10M token，足够写 150k 字（约 200k token）

# ----------------- 项目路径 -----------------
BASE_DIR = Path(__file__).parent
BIBLE_PATH   = BASE_DIR / "bible" / "story_bible.md"
OUTLINE_PATH = BASE_DIR / "outline" / "outline.json"
CHAPTER_DIR  = BASE_DIR / "chapters"
SUMMARY_DIR  = BASE_DIR / "summaries"

CHAPTER_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

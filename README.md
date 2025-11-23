# 📖 README – 本地 Ollama + Qwen‑3‑8B 中文长篇小说生成器  

> **项目名称**：`novel_writer`  
> **核心技术**：Ollama 本地部署 + Qwen‑3‑8B（4‑bit 量化）  
> **目标**：在 8 GB 显卡（如 NVIDIA Quadro P4000）上离线生成 ≈150 k 字的中文长篇小说，支持流式 SSE、章节‑摘要‑滚动记忆，完全开源（MIT）。

---

## 🎯 项目亮点  

| 功能 | 说明 |
|------|------|
| **全离线** | 完全不依赖云服务，只消耗本机算力和电力 |
| **流式 SSE** | 通过 `Server‑Sent Events` 实时拼接文本，避免出现 `thinking` 碎片 |
| **章节‑摘要‑滚动记忆** | 自动为每章生成 200‑300 字摘要，最新 3 章节摘要供后续章节参考，保证故事连贯 |
| **低显存** | 采用 Qwen‑3‑8B 4‑bit 量化，显存占用约 5‑6 GB，8 GB GPU 可轻松运行 |
| **可配置** | 通过 `config.py` / `.env` 调整模型、token 预算、路径等 |
| **开源** | 代码全开源，可自行二次开发或在其他项目中复用 |

---

## 🗂 项目结构  

```
novel_writer/
│
├─ bible/                # 全局设定（一次编辑）
│   └─ story_bible.md
│
├─ outline/              # 章节大纲（JSON 列表）
│   └─ outline.json
│
├─ chapters/             # 运行时生成的章节（.md）
│   └─ (空)
│
├─ summaries/            # 每章 200‑300 字摘要（.md）
│   └─ (空)
│
├─ utils/
│   ├─ __init__.py
│   └─ ollama_client.py  # SSE 流式实现 + 失效回退
│
├─ .env (optional)      # OLLAMA_HOST、MODEL
├─ config.py
├─ requirements.txt
├─ write_novel.py        # 主脚本
└─ README.md             # 本文件
```

> **所有源码已在下文完整列出**，复制对应块即可创建文件。

---

## 📦 环境准备  

### 1️⃣ 安装 Ollama（全平台）  
- 前往 <https://ollama.com/download> 下载并安装。  
- 启动服务（保持窗口打开）：

```bash
ollama serve
```

### 2️⃣ 拉取并量化模型（约 5‑6 GB 显存）  

```bash
ollama pull qwen3:8b --quantize q4_0   # 推荐 4‑bit 量化
# 若显存 > 12 GB，可省略 --quantize
# ollama pull qwen3:8b
```

> 验证：`ollama list` → 应看到 `qwen3:8b   (local)   8.0B`

### 3️⃣ Python 环境 & 依赖  

```bash
# 进入项目根目录
cd path/to/novel_writer

# 创建并激活虚拟环境
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

`requirements.txt`

```text
requests>=2.31.0
tqdm>=4.66.0
python-dotenv>=1.0.0
```

### 4️⃣ 可选 `.env`  

如果需要自定义 Ollama 主机或模型名：

```
OLLAMA_HOST=http://127.0.0.1:11434
MODEL=qwen3:8b
```

---

## 🚀 一键运行（生成完整小说）  

```bash
# 1️⃣ 保持 Ollama 运行
ollama serve

# 2️⃣ 拉取模型（只需做一次）
ollama pull qwen3:8b --quantize q4_0

# 3️⃣ 进入项目并激活虚拟环境（参考上一步）

# 4️⃣ 运行主脚本
python write_novel.py
```

- **进度**：终端会显示章节写作进度条。  
- **输出**：根目录生成 `novel_full.md`（完整小说），同时在 `chapters/` 与 `summaries/` 中保存每章原文与摘要。  
- **Token 统计**：脚本结束后会打印累计 `prompt` 与 `completion` token，用于预算监控（默认 10 M token ≈ 150 k 中文字符）。

---

## ⚙️ 配置说明  

| 参数 | 所在文件 | 默认值 | 说明 |
|------|----------|--------|------|
| `OLLAMA_HOST` | `.env` / `config.py` | `http://127.0.0.1:11434` | Ollama 服务地址 |
| `MODEL_NAME` | `.env` / `config.py` | `qwen3:8b` | 使用的模型 |
| `TOKEN_BUDGET` | `config.py` | `10_000_000` | 本项目最大 token 预算 |
| `max_tokens`（章节） | `write_novel.py` → `chat(..., max_tokens=8000)` | `8000` | 单次生成的最大 token，显存紧张时可调至 6000 |
| `temperature` | `write_novel.py` | `0.7` | 创意度，可自行调节 |
| `USE_THINKING_AS_BACKUP` | `utils/ollama_client.py` | `False` | 若设为 `True`，在无 `content` 时会回退使用 `thinking`（不推荐） |

---

## 🛠 调优建议（针对 8 GB 显卡）  

1. **模型量化**：始终使用 `--quantize q4_0`，显存占用最低。  
2. **`max_tokens`**：  
   - 8000 → 约 4.5k 中文字符，适合显存 5‑6 GB。  
   - 如出现 OOM，改为 **6000** 再次运行。  
3. **温度**：0.6‑0.8 范围内微调，低温更稳，稍高更有创意。  
4. **显存监控**：`nvidia-smi -l 5` 实时查看，防止突发 OOM。  
5. **速率控制**：脚本已在章节间 `time.sleep(0.2)`，若本地速率限制仍报错，可适当调高（0.5‑1 s）。  

---

## ❓ 常见问题 & 解决方案  

| 错误 | 原因 | 解决办法 |
|------|------|----------|
| `unknown endpoint /api/chat` | Ollama 版本过旧 | 更新至 **0.12+**（`ollama version`），或使用 `ollama_client.py` 已内置一次性回退 |
| `model not found: qwen3:8b` | 模型未下载或名称拼写错误 | 再次执行 `ollama pull qwen3:8b --quantize q4_0`，确认 `ollama list` 中出现 |
| `invalid character 'ï'` (JSON) | JSON 文件带 UTF‑8 BOM | 直接使用脚本中内置的 `outline.json`（已无 BOM），或用 `Set-Content -Encoding utf8NoBOM` 重写 |
| 章节输出出现 `thinking` 碎片 | 使用了旧版 `ollama_client.py` | 替换为本 README 中提供的最新实现，确保 `USE_THINKING_AS_BACKUP=False` |
| 脚本卡在 0% 长时间不返回 | 显存占满或模型卡死 | 检查 `nvidia-smi`，若显存 > 7 GB，降低 `max_tokens` 或重启 Ollama |
| `CUDA out of memory` | 未量化或 `max_tokens` 过大 | 确认已使用 `--quantize q4_0`，并把 `max_tokens` 调至 6000 或更低 |

---

---

## 👏 致谢 & 下一步  

- **离线 AI 创作**：本方案展示了在普通工作站上，使用开源模型完成大规模中文创作的可行性。  
- **可扩展性**：你可以在 `utils/` 中加入情感曲线检测、人物成长表、或自定义输出格式（HTML、PDF）。  
- **社区**：欢迎 Fork、Pull Request、Issue 共同完善。  

祝你玩得开心，写出好看的长篇小说 🎉🚀

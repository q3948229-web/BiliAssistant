# BiliAssistant

这是一个基于阿里云 DashScope 的视频/音频转文字与智能摘要生成助手。它能够自动处理本地文件或 B站视频，生成精简的总结、会议纪要、思维导图甚至是全篇翻译。

## 功能特性

- **多源支持**: 支持本地音视频文件、B站 AV/BV 号、在线 URL。
- **自动转录集成**: 使用阿里云 DashScope ASR 模型 (qwen3-asr-flash-filetrans)，实现高精度语音转文字。
- **AI 智能摘要**: 集成阿里云 Qwen-Long 模型，基于预设提示词生成结构化内容。
- **流程自动化**: 自动下载 -> 上传 OSS -> 转录 -> 摘要 -> 清理 OSS。
- **Web 服务**: 内置 FastAPI 服务，支持 HTTP 调用及任务队列。

## 安装与环境配置

本项目使用 [uv](https://github.com/astral-sh/uv) 进行高效的 Python 环境与依赖管理。

1. **安装依赖**:
   如果尚未安装 `uv`，请先安装。然后运行：
   ```bash
   uv sync
   ```

2. **配置环境变量**:
   复制 `config.example.py` 为 `.env` 文件，并填入您的阿里云 API Key 和 OSS 配置信息。
   *(注: 阿里云 OSS 用于暂存音频文件以供 ASR 服务读取)*

## 使用方法 (CLI)

您可以通过命令行直接处理单个任务。

### 基本用法

```bash
# 使用 uv 运行 (推荐)
uv run main.py <source> [options]
```

### 示例

1. **处理 B站视频 (默认生成视频总结)**:
   ```bash
   uv run main.py BV1xxxxxxxx
   ```

2. **处理本地文件**:
   需提供绝对路径或相对路径。
   ```bash
   uv run main.py "C:\Downloads\meeting_recording.mp3"
   ```

3. **使用不同的提示词预设**:
   默认预设为 `bilibili_summary`。您可以通过 `--preset` 参数指定其他模式。
   
   **会议纪要模式**:
   ```bash
   uv run main.py "path/to/meeting.mp4" --preset meeting_summary
   ```

   **全文翻译模式**:
   ```bash
   uv run main.py BV1xxxxxxxx --preset translation
   ```

### 可用预设 (Presets)

项目内置了以下几种提示词预设 (详见 `prompts/presets.json`):

- `bilibili_summary`: **(默认)** 适用于 B站视频，生成一句话概括、精彩观点和幽默总结。
- `meeting_summary`: 适用于会议录音，提取核心议题、详细摘要、结论与待办事项 (Action Items)。
- `translation`: 全文翻译 (中英互译)，保留时间戳。
- `mindmap`: 生成 Markdown 格式的思维导图节点。

## Web 服务

启动内置的 API 服务器，提供 RESTful 接口。

```bash
uv run main.py --server
```

启动后可访问文档: http://localhost:8000/docs


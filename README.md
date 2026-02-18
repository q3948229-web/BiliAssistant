# BiliAssistant

B站视频/音频转文字与摘要生成助手。|开发中

## 功能特性

- **多源支持**: 支持本地文件、B站 AV/BV 号、在线 URL。
- **自动转录**: 集成阿里云 DashScope ASR 模型 (qwen3-asr-flash-filetrans)。
- **智能摘要**: 集成阿里云 Qwen-Long 模型生成结构化会议纪要或内容总结。
- **流程自动化**: 自动下载 -> 上传 OSS -> 转录 -> 摘要 -> 清理 OSS。
- **Web 服务**: 内置 FastAPI 服务，支持 HTTP 调用。

## 安装

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 配置文件:
复制 `config.example.py` 为 `.env` 并填入您的阿里云 API Key 和 OSS 配置。
*(注: 项目使用 `pydantic-settings` 读取 `.env` 文件，请确保格式正确)*

## 使用

**命令行 (CLI):**
```bash
python main.py BV1xxxxxxxx
```

**Web 服务:**
```bash
python main.py --server
```


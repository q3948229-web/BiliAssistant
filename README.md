# BiliAssistant

基于阿里云 DashScope 的音视频转录与内容整理工具，支持本地文件、Bilibili 视频和普通 URL 输入，输出转录文本与结构化总结。

## 项目能力

- 音视频转文字：调用 DashScope ASR 模型完成转录。
- 内容总结：调用大模型按预设提示词生成摘要、翻译、思维导图等结果。
- 多输入源：支持本地文件、B 站 BV 号、视频 URL。
- 自动处理链路：下载、提取音频、上传 OSS、转录、总结、清理临时资源。
- 双入口：支持命令行模式和 FastAPI Web 服务模式。

## 项目结构

```text
.
|- main.py                 # CLI 与 FastAPI 入口
|- core/
|  |- pipeline.py         # 主处理流程
|  |- downloader.py       # 下载视频/音频
|  |- asr_client.py       # DashScope ASR 调用
|  |- llm_client.py       # 摘要与提示词处理
|  `- oss_manager.py      # OSS 上传与清理
|- utils/
|  |- config.py           # 环境变量配置
|  `- logger.py           # 日志
`- prompts/presets.json   # 预设提示词
```

## 环境要求

- Python `3.10+`
- Windows 环境
- `uv` 用于环境和依赖管理
- 阿里云 DashScope API Key
- 阿里云 OSS 配置

## 安装

1. 安装 `uv`。
2. 在项目根目录执行：

```bash
uv sync
```

3. 之后统一使用 `uv run` 执行程序，不再维护 Conda、WSL 虚拟环境或仓库内其他 Python 环境目录。

## 配置

程序通过 `.env` 读取配置，字段定义见 `utils/config.py`。

可以参考 `config.example.py`，在项目根目录创建 `.env`，至少包含以下变量：

```env
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_MODEL=qwen3-asr-flash-filetrans
DASHSCOPE_SUMMARY_MODEL=qwen-long
OSS_ACCESS_KEY_ID=your_oss_id
OSS_ACCESS_KEY_SECRET=your_oss_secret
OSS_ENDPOINT=https://oss-cn-shanghai.aliyuncs.com
OSS_BUCKET_NAME=your_bucket_name
```

注意：`config.example.py` 只是字段示例，实际运行读取的是 `.env`。

## CLI 用法

### 基本命令

```bash
uv run main.py <source> [--preset <preset_name>]
```

`source` 支持：

- 本地音视频文件路径
- Bilibili `BV` 号
- 普通视频 URL
- 本地目录路径：会批量处理目录中的 `.mp4` 文件

### 示例

处理 B 站视频：

```bash
uv run main.py BV1xxxxxxxx
```

处理本地文件：

```bash
uv run main.py "C:\Downloads\meeting_recording.mp3"
```

批量处理目录中的 MP4：

```bash
uv run main.py "C:\videos"
```

指定预设：

```bash
uv run main.py BV1xxxxxxxx --preset bilibili_summary
uv run main.py "C:\videos\meeting.mp4" --preset meeting_summary
uv run main.py "C:\videos\lecture.mp4" --preset translation
```

## 可用预设

当前 `prompts/presets.json` 中包含：

- `bilibili_summary`：B 站视频总结
- `meeting_summary`：会议纪要
- `translation`：全文翻译
- `mindmap`：Markdown 思维导图
- `summary`：偏完整的长摘要
- `lab_experiment`：实验报告视频总结

## Web API

启动服务：

```bash
uv run main.py --server
```

启动后可访问：

- Swagger 文档：`http://localhost:8000/docs`
- OpenAPI 描述：`http://localhost:8000/openapi.json`

主要接口：

- `GET /presets`：获取可用预设
- `POST /process`：提交异步处理任务
- `GET /status/{task_id}`：查询任务状态

`POST /process` 请求体示例：

```json
{
  "source": "BV1xxxxxxxx",
  "skip_download": false,
  "preset_name": "bilibili_summary",
  "custom_prompt": null
}
```

## 输出结果

默认输出目录：

- `downloads/`：下载的原始文件或中间音频
- `output/`：转录文本与总结结果

每次处理通常会生成：

- `output/<name>.txt`：转录文本
- `output/<name>_summary.txt`：模型生成结果

## 当前已知注意事项

- `README` 现已按 `.env` 方式说明配置，但仓库里仍保留了 `config.example.py`，名称容易让人误以为程序直接读取 Python 配置。
- 当前仓库按 `Windows + uv` 使用方式整理，不再保留 Conda 环境文件。
- 本地虚拟环境目录如 `.venv/`、`.opencode-venv/` 已列入忽略列表，不应提交到 git。

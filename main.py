import uuid
import json
import os
import mimetypes
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict
from fastapi.middleware.cors import CORSMiddleware

from core.pipeline import Pipeline
from utils.logger import get_logger

"""
主程序入口 (Entry Point)
功能：
1. 提供 Web API 服务 (FastAPI)，供外部调用 (如油猴脚本、前端页面)。
2. 提供 命令行工具 (CLI)，直接在终端处理文件或 URL。
"""

# 初始化 APP
app = FastAPI(
    title="BiliAssistant Service",
    description="一个将视频/音频转换为文本并生成摘要的 API 服务",
    version="1.0.0"
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化核心处理流程
pipeline = Pipeline()
logger = get_logger("Main")

# 简单的内存任务存储
# 结构: { task_id: { "status": "processing" | "succeeded" | "failed", "result": {...}, "error": "..." } }
tasks_db: Dict[str, dict] = {}

# 加载 presets
PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "presets.json")

def load_presets():
    try:
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading presets: {e}")
    return {}

class ProcessRequest(BaseModel):
    """
    API 请求体模型
    """
    source: str          # 输入源: 可以是 B站 BV号, URL, 或 本地文件路径
    skip_download: bool = False # 是否跳过下载步骤 (仅当确信文件已在本地时使用)
    preset_name: str = "bilibili_summary" # 预设提示词名称
    custom_prompt: Optional[str] = None # 自定义 System Prompt

def background_process_task(task_id: str, request: ProcessRequest):
    logger.info(f"后台任务开始: {task_id}")
    try:
        tasks_db[task_id]["status"] = "processing"
        
        # 调用 Pipeline
        result = pipeline.run(
            request.source, 
            request.skip_download, 
            preset_name=request.preset_name,
            custom_prompt=request.custom_prompt
        )
        
        tasks_db[task_id]["status"] = "succeeded"
        tasks_db[task_id]["result"] = result
        logger.info(f"后台任务完成: {task_id}")
    except Exception as e:
        logger.error(f"后台任务失败 {task_id}: {e}")
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)

@app.get("/presets", summary="获取可用的提示词预设")
def get_presets():
    presets = load_presets()
    return [{"key": k, "label": v.get("label", k)} for k, v in presets.items()]

@app.post("/process", summary="提交音频处理任务 (异步)")
def process_audio(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    提交任务并立即返回 task_id
    """
    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "status": "queued",
        "result": None,
        "error": None
    }
    background_tasks.add_task(background_process_task, task_id, request)
    return {"task_id": task_id, "message": "Task queued"}

@app.get("/status/{task_id}", summary="查询任务状态")
def get_task_status(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/files/{filename}", summary="下载临时音频文件（供 ASR API 拉取）")
async def serve_file(filename: str):
    from utils.config import settings
    file_path = os.path.join(settings.PUBLIC_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    media_type, _ = mimetypes.guess_type(filename)
    return FileResponse(file_path, media_type=media_type or "audio/mpeg")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BiliAssistant - B站视频摘要</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f7; color: #1d1d1f; min-height: 100vh; }
.container { max-width: 640px; margin: 0 auto; padding: 32px 20px; }
h1 { font-size: 24px; font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 8px; }
.subtitle { font-size: 14px; color: #86868b; margin-bottom: 24px; }
.card { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }
label { font-size: 14px; font-weight: 500; display: block; margin-bottom: 6px; color: #1d1d1f; }
input, select, textarea { width: 100%; padding: 10px 14px; border: 1px solid #d2d2d7; border-radius: 10px; font-size: 15px; outline: none; transition: border-color .2s; background: #fff; font-family: inherit; }
input:focus, select:focus, textarea:focus { border-color: #007aff; }
.form-group { margin-bottom: 14px; }
.btn { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 16px; font-weight: 500; cursor: pointer; transition: opacity .2s; background: #007aff; color: #fff; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn:hover:not(:disabled) { opacity: .85; }
.status { font-size: 14px; padding: 12px 16px; border-radius: 10px; margin-bottom: 16px; display: none; align-items: center; gap: 8px; }
.status.show { display: flex; }
.status.info { background: #e8f0fe; color: #1967d2; }
.status.done { background: #e6f4ea; color: #137333; }
.status.err { background: #fce8e6; color: #c5221f; }
.spinner { width: 16px; height: 16px; border: 2px solid #1967d2; border-top-color: transparent; border-radius: 50%; animation: spin .6s linear infinite; flex-shrink: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
.result-box { display: none; }
.result-box.show { display: block; }
.result-box textarea { width: 100%; min-height: 260px; padding: 14px; border: 1px solid #d2d2d7; border-radius: 10px; font-size: 14px; line-height: 1.6; resize: vertical; background: #fafafa; }
.result-actions { display: flex; gap: 8px; margin-top: 10px; }
.result-actions button { padding: 8px 16px; border: 1px solid #d2d2d7; border-radius: 8px; font-size: 13px; cursor: pointer; background: #fff; transition: background .2s; }
.result-actions button:hover { background: #f5f5f7; }
.result-actions button.primary { background: #007aff; color: #fff; border-color: #007aff; }
.result-actions button.primary:hover { opacity: .85; }
a { color: #007aff; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="container">
  <h1>🤖 BiliAssistant</h1>
  <p class="subtitle">输入 B站视频链接或 BV 号，AI 自动生成摘要</p>

  <div class="card">
    <div class="form-group">
      <label>视频链接或 BV 号</label>
      <input id="input-source" placeholder="例如: BV1xx411c7mD 或 https://www.bilibili.com/video/BV1xx411c7mD">
    </div>

    <div class="form-group">
      <label>总结模式</label>
      <select id="input-preset"></select>
    </div>

    <div class="form-group">
      <label>自定义提示词（可选）</label>
      <textarea id="input-custom" placeholder="留空则使用上方选择的模式默认提示词" rows="2"></textarea>
    </div>

    <button class="btn" id="btn-submit" onclick="startTask()">🚀 生成摘要</button>
  </div>

  <div class="status" id="status-msg">
    <div class="spinner"></div>
    <span id="status-text"></span>
  </div>

  <div class="card result-box" id="result-box">
    <label>📝 生成结果</label>
    <textarea id="result-text" readonly></textarea>
    <div class="result-actions">
      <button class="primary" onclick="copyResult()">📋 复制</button>
      <button onclick="clearResult()">🗑️ 清空</button>
    </div>
  </div>

  <p style="text-align:center;font-size:13px;color:#86868b;margin-top:24px">
    <a href="/docs" target="_blank">API 文档</a>
  </p>
</div>

<script>
async function loadPresets() {
  try {
    const r = await fetch('/presets');
    const list = await r.json();
    const sel = document.getElementById('input-preset');
    list.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.key; opt.textContent = p.label;
      sel.appendChild(opt);
    });
  } catch { /* fallback handled below */ }
}
loadPresets();

function setStatus(msg, type) {
  const el = document.getElementById('status-msg');
  const txt = document.getElementById('status-text');
  el.className = 'status show ' + (type || 'info');
  txt.textContent = msg;
}

function showResult(text) {
  document.getElementById('result-text').value = text;
  document.getElementById('result-box').classList.add('show');
}

async function startTask() {
  const source = document.getElementById('input-source').value.trim();
  if (!source) { setStatus('请先输入视频链接或 BV 号', 'err'); return; }

  const btn = document.getElementById('btn-submit');
  btn.disabled = true;
  document.getElementById('result-box').classList.remove('show');

  setStatus('提交任务中...', 'info');

  try {
    const r = await fetch('/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source,
        preset_name: document.getElementById('input-preset').value,
        custom_prompt: document.getElementById('input-custom').value.trim() || null
      })
    });
    const data = await r.json();
    if (!data.task_id) throw new Error('提交失败');

    // Poll
    let attempts = 0;
    const poll = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch('/status/' + data.task_id);
        const task = await res.json();
        if (task.status === 'succeeded') {
          clearInterval(poll);
          btn.disabled = false;
          setStatus('✅ 处理完成！', 'done');
          if (task.result?.summary) showResult(task.result.summary);
        } else if (task.status === 'failed') {
          clearInterval(poll);
          btn.disabled = false;
          setStatus('❌ 失败: ' + (task.error || '未知错误'), 'err');
        } else {
          const dots = '.'.repeat((attempts % 3) + 1);
          setStatus('⏳ ' + (task.status === 'queued' ? '排队中' : '处理中') + dots, 'info');
        }
      } catch { /* retry */ }
    }, 1500);
  } catch (e) {
    btn.disabled = false;
    setStatus('❌ 连接失败，请检查服务是否正常运行', 'err');
  }
}

function copyResult() {
  const ta = document.getElementById('result-text');
  ta.select();
  navigator.clipboard?.writeText(ta.value);
  const btn = event.target;
  const orig = btn.textContent;
  btn.textContent = '✅ 已复制';
  setTimeout(() => btn.textContent = orig, 1500);
}

function clearResult() {
  document.getElementById('result-text').value = '';
  document.getElementById('result-box').classList.remove('show');
}
</script>
</body>
</html>"""

def run_cli(source, preset_name="bilibili_summary"):
    """
    命令行模式运行入口
    """
    if os.path.isdir(source):
        # 目录模式: 批量处理 MP4 文件
        logger.info(f"检测到目录输入: {source}")
        files = [f for f in os.listdir(source) if f.lower().endswith(".mp4")]
        
        if not files:
            logger.warning(f"在该目录下未找到 .mp4 文件: {source}")
            return
            
        logger.info(f"找到 {len(files)} 个 MP4 文件准备处理")
        
        for i, filename in enumerate(files, 1):
            file_path = os.path.join(source, filename)
            logger.info(f"[{i}/{len(files)}] 正在处理文件: {filename}")
            try:
                pipeline.run(file_path, preset_name=preset_name)
            except Exception as e:
                logger.error(f"处理文件失败 {filename}: {e}")
                # 继续处理下一个文件
    else:
        # 单任务模式
        try:
            logger.info(f"开始 CLI 模式处理: {source} | Preset: {preset_name}")
            pipeline.run(source, preset_name=preset_name)
        except Exception as e:
            logger.error(f"CLI Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bilibili/MP3 转文字摘要工具")
    parser.add_argument("source", nargs="?", help="输入源 (文件路径 / URL / B站BV号)")
    parser.add_argument("--preset", default="bilibili_summary", help="选择摘要提示词预设 (默认: bilibili_summary)")
    parser.add_argument("--server", action="store_true", help="启动 Web API 服务器模式")
    
    args = parser.parse_args()
    
    if args.server:
        print("正在启动 Web 服务... 访问 http://localhost:8000/docs 查看文档")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif args.source:
        run_cli(args.source, args.preset)
    else:
        # 如果没有参数，打印帮助信息
        parser.print_help()

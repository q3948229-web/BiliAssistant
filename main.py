import uuid
import json
import os
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
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

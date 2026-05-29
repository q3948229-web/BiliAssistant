import os
import subprocess
import shutil
import uuid
import time
import imageio_ffmpeg
from typing import ClassVar
from .downloader import BilibiliDownloader
from .asr_client import ASRClient
from .llm_client import LLMClient
from utils.config import settings
from utils.logger import get_logger
import utils.transcript_cache as transcript_cache

logger = get_logger("Pipeline")

class Pipeline:
    task_progress: ClassVar[dict[str, str]] = {}

    def __init__(self):
        self.downloader = BilibiliDownloader(settings.DOWNLOAD_DIR)
        self.asr = ASRClient()
        self.llm = LLMClient()

    def run(self, source: str, skip_download=False, preset_name="bilibili_summary", custom_prompt=None, task_id=""):
        local_file = source
        served_file = None
        transcript = None
        bv_id = transcript_cache.extract_bv(source) if not skip_download else None
        
        try:
            # -- Cache check: skip download + ASR if we already have transcript --
            if bv_id:
                cached = transcript_cache.get(bv_id)
                if cached:
                    Pipeline.task_progress[task_id] = "检测到已有转录记录，跳过下载和语音识别..."
                    logger.info(f"Cache hit for {bv_id}, skipping download and ASR")
                    transcript = cached
            
            # -- 1. Download (only if no cached transcript) --
            if transcript is None:
                if not skip_download and (source.startswith("http") or source.startswith("BV")):
                    Pipeline.task_progress[task_id] = "下载视频中..."
                    logger.info("Step 1: Downloading...")
                    local_file = self.downloader.download(source)
                elif os.path.exists(source):
                    logger.info(f"Step 1: Using local file: {source}")
                else:
                    raise Exception("Invalid source")

                # 2. Convert to mp3 for ASR compatibility, then serve via URL
                Pipeline.task_progress[task_id] = "转换音频格式中..."
                logger.info("Step 2: Converting audio for ASR...")
                file_id = str(uuid.uuid4())
                os.makedirs(settings.PUBLIC_DIR, exist_ok=True)
                serve_path = os.path.join(settings.PUBLIC_DIR, f"{file_id}.mp3")

                ext = os.path.splitext(local_file)[1].lower()
                if ext in [".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg"]:
                    shutil.copy2(local_file, serve_path)
                else:
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    subprocess.run(
                        [ffmpeg_exe, '-i', local_file, '-acodec', 'libmp3lame', '-q:a', '4', serve_path, '-y'],
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )

                served_file = serve_path
                file_url = f"{settings.PUBLIC_HOST}/files/{file_id}.mp3"

                # 3. Transcribe
                Pipeline.task_progress[task_id] = "语音识别中..."
                logger.info("Step 3: Transcribing...")
                asr_task_id = self.asr.submit_task(file_url)
                logger.info(f"ASR Task ID: {asr_task_id}")
                Pipeline.task_progress[task_id] = "等待语音识别结果..."
                transcript = self.asr.poll_result(asr_task_id)

                # -- Cache the transcript --
                if bv_id:
                    transcript_cache.set(bv_id, transcript)
                    logger.info(f"Cached transcript for {bv_id}")
            
            # -- Save Transcript --
            base_name = os.path.splitext(os.path.basename(local_file))[0]
            output_dir = settings.OUTPUT_DIR
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            transcript_path = os.path.join(output_dir, f"{base_name}.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            logger.info(f"Transcript saved to {transcript_path}")

            # 4. Summarize
            Pipeline.task_progress[task_id] = "AI 生成总结中..."
            logger.info(f"Step 4: Summarizing (Preset: {preset_name})...")
            summary = self.llm.generate_summary(transcript, preset_name=preset_name, custom_prompt=custom_prompt)
            
            summary_path = os.path.join(output_dir, f"{base_name}_summary.txt")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            logger.info(f"Summary saved to {summary_path}")

            Pipeline.task_progress.pop(task_id, None)

            return {
                "transcript": transcript,
                "summary": summary,
                "files": {
                    "transcript": transcript_path,
                    "summary": summary_path
                }
            }

        except Exception as e:
            logger.error(f"Pipeline Error: {e}")
            Pipeline.task_progress.pop(task_id, None)
            raise e
            
        finally:
            if served_file and os.path.exists(served_file):
                try:
                    os.remove(served_file)
                    logger.info(f"Cleaned up served file: {served_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup served file: {e}")

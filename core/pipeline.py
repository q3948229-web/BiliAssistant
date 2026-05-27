import os
import shutil
import uuid
from .downloader import BilibiliDownloader
from .asr_client import ASRClient
from .llm_client import LLMClient
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("Pipeline")

class Pipeline:
    def __init__(self):
        self.downloader = BilibiliDownloader(settings.DOWNLOAD_DIR)
        self.asr = ASRClient()
        self.llm = LLMClient()

    def run(self, source: str, skip_download=False, preset_name="bilibili_summary", custom_prompt=None):
        local_file = source
        served_file = None
        
        try:
            # 1. Download if needed
            if not skip_download and (source.startswith("http") or source.startswith("BV")):
                logger.info("Step 1: Downloading...")
                local_file = self.downloader.download(source)
            elif os.path.exists(source):
                logger.info(f"Step 1: Using local file: {source}")
            else:
                raise Exception("Invalid source")

            # 2. Make file accessible via public URL
            logger.info("Step 2: Preparing file for ASR...")
            file_id = str(uuid.uuid4())
            ext = os.path.splitext(local_file)[1] or ".mp3"
            serve_name = f"{file_id}{ext}"
            os.makedirs(settings.PUBLIC_DIR, exist_ok=True)
            serve_path = os.path.join(settings.PUBLIC_DIR, serve_name)
            shutil.copy2(local_file, serve_path)
            served_file = serve_path
            file_url = f"{settings.PUBLIC_HOST}/files/{serve_name}"

            # 3. Transcribe
            logger.info("Step 3: Transcribing...")
            task_id = self.asr.submit_task(file_url)
            logger.info(f"Task ID: {task_id}")
            transcript = self.asr.poll_result(task_id)
            
            # Save Transcript
            base_name = os.path.splitext(os.path.basename(local_file))[0]
            output_dir = settings.OUTPUT_DIR
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            transcript_path = os.path.join(output_dir, f"{base_name}.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)
            logger.info(f"Transcript saved to {transcript_path}")

            # 4. Summarize
            logger.info(f"Step 4: Summarizing (Preset: {preset_name})...")
            summary = self.llm.generate_summary(transcript, preset_name=preset_name, custom_prompt=custom_prompt)
            
            summary_path = os.path.join(output_dir, f"{base_name}_summary.txt")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(summary)
            logger.info(f"Summary saved to {summary_path}")

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
            raise e
            
        finally:
            # Cleanup served file
            if served_file and os.path.exists(served_file):
                try:
                    os.remove(served_file)
                    logger.info(f"Cleaned up served file: {served_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup served file: {e}")

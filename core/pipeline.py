import os
from .downloader import BilibiliDownloader
from .oss_manager import OSSManager
from .asr_client import ASRClient
from .llm_client import LLMClient
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("Pipeline")

class Pipeline:
    def __init__(self):
        self.downloader = BilibiliDownloader(settings.DOWNLOAD_DIR)
        self.oss = OSSManager()
        self.asr = ASRClient()
        self.llm = LLMClient()

    def run(self, source: str, skip_download=False):
        local_file = source
        oss_key = None
        
        try:
            # 1. Download if needed
            if not skip_download and (source.startswith("http") or source.startswith("BV")):
                logger.info("Step 1: Downloading...")
                local_file = self.downloader.download(source)
            elif os.path.exists(source):
                logger.info(f"Step 1: Using local file: {source}")
            else:
                raise Exception("Invalid source")

            # 2. Upload to OSS
            logger.info("Step 2: Uploading to OSS...")
            oss_url, oss_key = self.oss.upload_file(local_file)

            # 3. Transcribe
            logger.info("Step 3: Transcribing...")
            task_id = self.asr.submit_task(oss_url)
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
            logger.info("Step 4: Summarizing...")
            summary = self.llm.generate_summary(transcript, mode="meeting_summary") # defaulting mode for now
            
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
            # Cleanup OSS
            if oss_key:
                self.oss.delete_file(oss_key)

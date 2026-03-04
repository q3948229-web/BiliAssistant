import os
import subprocess
import imageio_ffmpeg
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

    def _convert_video_to_audio(self, video_path: str) -> str:
        """如果输入是视频文件，且存在 ffmpeg，则提取音频"""
        try:
            ext = os.path.splitext(video_path)[1].lower()
            if ext not in [".mp4", ".mkv", ".mov", ".flv", ".avi", ".webm"]:
                return video_path
            
            logger.info("Attempting to convert video to audio for faster upload...")
            
            # 生成临时输出路径
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            # 确保下载目录存在
            if not os.path.exists(settings.DOWNLOAD_DIR):
                os.makedirs(settings.DOWNLOAD_DIR)
                
            output_path = os.path.join(settings.DOWNLOAD_DIR, f"{base_name}_temp_audio.mp3")
            
            # 获取 ffmpeg 路径
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            # 构建命令: -i input -vn (无视频) -acodec mp3 -y (覆盖)
            cmd = [ffmpeg_exe, '-i', video_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '4', output_path, '-y']
            
            # 使用 subprocess 调用
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(output_path):
                logger.info(f"Conversion successful: {output_path}")
                return output_path
            
        except Exception as e:
            logger.warning(f"Video to audio conversion failed (using original file): {e}")
        
        return video_path

    def run(self, source: str, skip_download=False, preset_name="bilibili_summary", custom_prompt=None):
        local_file = source
        oss_key = None
        temp_audio_file = None
        
        try:
            # 1. Download if needed
            if not skip_download and (source.startswith("http") or source.startswith("BV")):
                logger.info("Step 1: Downloading...")
                local_file = self.downloader.download(source)
            elif os.path.exists(source):
                logger.info(f"Step 1: Using local file: {source}")
                # 尝试转换本地视频
                converted_file = self._convert_video_to_audio(source)
                if converted_file != source:
                    local_file = converted_file
                    temp_audio_file = converted_file
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
            # Cleanup OSS
            if oss_key:
                self.oss.delete_file(oss_key)
            
            # Cleanup temp file
            if temp_audio_file and os.path.exists(temp_audio_file):
                try:
                    os.remove(temp_audio_file)
                    logger.info(f"Cleaned up temp audio: {temp_audio_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp audio: {e}")

import os
import sys
import imageio_ffmpeg
try:
    import yt_dlp
except ImportError:
    pass # handled by caller or requirements

from utils.logger import get_logger

logger = get_logger("Downloader")

class BilibiliDownloader:
    def __init__(self, download_dir="downloads"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        try:
            self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except:
            self.ffmpeg_exe = None

    def download(self, url_or_bv: str) -> str:
        # Normalize input
        if not url_or_bv.startswith("http"):
            if url_or_bv.startswith("BV") or url_or_bv.startswith("bv"):
                url_or_bv = f"https://www.bilibili.com/video/{url_or_bv}"
            else:
                url_or_bv = f"https://www.bilibili.com/video/{url_or_bv}"

        logger.info(f"Target: {url_or_bv}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'ffmpeg_location': self.ffmpeg_exe,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_or_bv, download=True)
                filename = ydl.prepare_filename(info)
                final_filename = os.path.splitext(filename)[0] + ".mp3"
                logger.info(f"Download complete: {final_filename}")
                return final_filename
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise e

import os
import sys
import tempfile
import imageio_ffmpeg
try:
    import yt_dlp
except ImportError:
    pass

from utils.logger import get_logger
from utils.config import settings

logger = get_logger("Downloader")


def _write_cookies():
    """Write BILIBILI_COOKIES env var to a temp file if set, return the path or None."""
    raw = getattr(settings, "BILIBILI_COOKIES", None) or os.environ.get("BILIBILI_COOKIES", "")
    if not raw.strip():
        return None
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    tmp.write(raw.strip())
    tmp.close()
    logger.info("Using BILIBILI_COOKIES from environment")
    return tmp.name


class BilibiliDownloader:
    def __init__(self, download_dir="downloads"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        self.cookie_file = _write_cookies()

        try:
            self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except:
            self.ffmpeg_exe = None

    def download(self, url_or_bv: str) -> str:
        if not url_or_bv.startswith("http"):
            if url_or_bv.startswith("BV") or url_or_bv.startswith("bv"):
                url_or_bv = f"https://www.bilibili.com/video/{url_or_bv}"
            else:
                url_or_bv = f"https://www.bilibili.com/video/{url_or_bv}"

        logger.info(f"Target: {url_or_bv}")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.download_dir, "%(title)s.%(ext)s"),
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://www.bilibili.com",
            },
            "extractor_args": {"bilibili": {"no_webproxy": ["True"]}},
            "ffmpeg_location": self.ffmpeg_exe,
        }

        if self.cookie_file:
            ydl_opts["cookiefile"] = self.cookie_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_or_bv, download=True)
                filename = ydl.prepare_filename(info)
                logger.info(f"Download complete: {filename}")
                return filename
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise e

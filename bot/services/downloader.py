import os
import re
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp

try:
    import imageio_ffmpeg
    src_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    FFMPEG_DIR = os.path.dirname(src_ffmpeg)
    ffmpeg_bin = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_bin) and os.path.exists(src_ffmpeg):
        import shutil
        shutil.copyfile(src_ffmpeg, ffmpeg_bin)
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
except Exception as e:
    FFMPEG_DIR = None
    print(f"[FFmpeg Init Warning] {e}")

from bot.config import DOWNLOAD_DIR, MAX_VIDEO_SIZE_MB, PROXY_URL

logger = logging.getLogger(__name__)


def clean_media_url(url: str) -> str:
    """Removes tracking query parameters (igsh, igsi, si, etc.) that can break downloaders."""
    if "instagram.com" in url.lower():
        # Remove tracking parameters
        url = re.sub(r'(\?|&)(igsh|igsi|utm_[a-z]+)=[^&]*', '', url)
        url = url.rstrip('?&')
    elif "youtu" in url.lower():
        url = re.sub(r'(\?|&)si=[^&]*', '', url).rstrip('?&')
    return url


class DownloaderService:
    """Fast, robust, and resilient video downloader for YouTube, Instagram, and more."""

    @staticmethod
    def _sync_download(url: str, output_path: Path) -> Dict[str, Any]:
        """Synchronous download function using flexible format selection and retries."""
        cleaned_url = clean_media_url(url)

        ydl_opts = {
            'outtmpl': str(output_path),
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/worst[height>=360]/worst[ext=mp4]/best',
            'max_filesize': MAX_VIDEO_SIZE_MB * 1024 * 1024,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 45,
            'retries': 3,
            'fragment_retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Mode': 'navigate',
            }
        }

        if FFMPEG_DIR and os.path.exists(FFMPEG_DIR):
            ydl_opts['ffmpeg_location'] = FFMPEG_DIR

        # Use proxy if configured
        if PROXY_URL:
            ydl_opts['proxy'] = PROXY_URL

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(cleaned_url, download=True)
            except Exception:
                # If cleaned URL fails, try original URL as fallback
                info = ydl.extract_info(url, download=True)
            
            actual_filename = ydl.prepare_filename(info)
            if not os.path.exists(actual_filename):
                base = os.path.splitext(str(output_path))[0]
                for ext in ['.mp4', '.mkv', '.webm', '.mov', '.m4v']:
                    if os.path.exists(base + ext):
                        actual_filename = base + ext
                        break

            if not os.path.exists(actual_filename):
                raise FileNotFoundError(f"Yuklangan video fayli topilmadi: {actual_filename}")

            return {
                "file_path": Path(actual_filename),
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "tags": info.get("tags", []),
                "uploader": info.get("uploader", ""),
                "duration": info.get("duration", 0),
            }

    @classmethod
    async def download_video_from_url(cls, url: str) -> Optional[Dict[str, Any]]:
        """Asynchronously downloads video from URL with resilient error handling."""
        unique_id = uuid.uuid4().hex[:12]
        output_template = DOWNLOAD_DIR / f"vid_{unique_id}.%(ext)s"

        try:
            result = await asyncio.to_thread(cls._sync_download, url, output_template)
            return result
        except Exception as e:
            logger.error(f"[Downloader Error] {url} yuklashda xatolik: {e}")
            return None


downloader = DownloaderService()

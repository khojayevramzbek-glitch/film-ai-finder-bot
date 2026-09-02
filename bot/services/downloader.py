import os
import re
import uuid
import asyncio
import logging
import requests
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
        url = re.sub(r'(\?|&)(igsh|igsi|utm_[a-z]+)=[^&]*', '', url)
        url = url.rstrip('?&')
    elif "youtu" in url.lower():
        url = re.sub(r'(\?|&)si=[^&]*', '', url).rstrip('?&')
    return url


class DownloaderService:
    """Fast, robust, and resilient video downloader for YouTube, Instagram, and more."""

    @staticmethod
    def _fetch_instagram_oembed(url: str, output_image_path: Path) -> Optional[Dict[str, Any]]:
        """Fetches Instagram metadata and high-res thumbnail when video download is blocked by datacenter IP."""
        m = re.search(r'/(reel|p)/([A-Za-z0-9_-]+)', url)
        if not m:
            return None
        code = m.group(2)
        oembed_url = f"https://www.instagram.com/api/v1/oembed/?url=https://www.instagram.com/reel/{code}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }
        try:
            resp = requests.get(oembed_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                thumb_url = data.get("thumbnail_url")
                caption = data.get("title", "")
                if thumb_url:
                    img_resp = requests.get(thumb_url, headers=headers, timeout=8)
                    if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                        with open(output_image_path, "wb") as f:
                            f.write(img_resp.content)
                        return {
                            "is_image_fallback": True,
                            "file_path": output_image_path,
                            "title": caption,
                            "description": caption,
                            "uploader": data.get("author_name", "")
                        }
        except Exception as e:
            logger.warning(f"[Instagram OEmbed Warning] {e}")
        return None

    @staticmethod
    def _fetch_youtube_oembed(url: str, output_image_path: Path) -> Optional[Dict[str, Any]]:
        """Fetches YouTube metadata and thumbnail when video is geoblocked or unavailable."""
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        try:
            resp = requests.get(oembed_url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                thumb_url = data.get("thumbnail_url")
                title = data.get("title", "")
                if thumb_url:
                    img_resp = requests.get(thumb_url, timeout=8)
                    if img_resp.status_code == 200:
                        with open(output_image_path, "wb") as f:
                            f.write(img_resp.content)
                        return {
                            "is_image_fallback": True,
                            "file_path": output_image_path,
                            "title": title,
                            "description": title,
                            "uploader": data.get("author_name", "")
                        }
        except Exception as e:
            logger.warning(f"[YouTube OEmbed Warning] {e}")
        return None

    @classmethod
    def _sync_download(cls, url: str, output_path: Path) -> Dict[str, Any]:
        """Synchronous download function with smart OEmbed fallback."""
        cleaned_url = clean_media_url(url)

        ydl_opts = {
            'outtmpl': str(output_path),
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/worst[height>=360]/worst[ext=mp4]/best',
            'max_filesize': MAX_VIDEO_SIZE_MB * 1024 * 1024,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 2,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }

        if FFMPEG_DIR and os.path.exists(FFMPEG_DIR):
            ydl_opts['ffmpeg_location'] = FFMPEG_DIR

        if PROXY_URL:
            ydl_opts['proxy'] = PROXY_URL

        # 1. Try yt-dlp direct download
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(cleaned_url, download=True)
                except Exception:
                    info = ydl.extract_info(url, download=True)

                actual_filename = ydl.prepare_filename(info)
                if not os.path.exists(actual_filename):
                    base = os.path.splitext(str(output_path))[0]
                    for ext in ['.mp4', '.mkv', '.webm', '.mov', '.m4v']:
                        if os.path.exists(base + ext):
                            actual_filename = base + ext
                            break

                if os.path.exists(actual_filename):
                    return {
                        "is_image_fallback": False,
                        "file_path": Path(actual_filename),
                        "title": info.get("title", ""),
                        "description": info.get("description", ""),
                        "tags": info.get("tags", []),
                        "uploader": info.get("uploader", ""),
                        "duration": info.get("duration", 0),
                    }
        except Exception as ydl_err:
            logger.warning(f"[yt-dlp Warning] {ydl_err}")

        # 2. Fallback: Instagram OEmbed & High-Res Thumbnail
        if "instagram.com" in url.lower():
            fallback_img = DOWNLOAD_DIR / f"thumb_{uuid.uuid4().hex[:8]}.jpg"
            res = cls._fetch_instagram_oembed(url, fallback_img)
            if res:
                return res

        # 3. Fallback: YouTube OEmbed
        if "youtu" in url.lower():
            fallback_img = DOWNLOAD_DIR / f"thumb_{uuid.uuid4().hex[:8]}.jpg"
            res = cls._fetch_youtube_oembed(url, fallback_img)
            if res:
                return res

        raise FileNotFoundError(f"Video yoki ma'lumot yuklab bo'lmadi: {url}")

    @classmethod
    async def download_video_from_url(cls, url: str) -> Optional[Dict[str, Any]]:
        """Asynchronously downloads video or thumbnail fallback from URL."""
        unique_id = uuid.uuid4().hex[:12]
        output_template = DOWNLOAD_DIR / f"vid_{unique_id}.%(ext)s"

        try:
            result = await asyncio.to_thread(cls._sync_download, url, output_template)
            return result
        except Exception as e:
            logger.error(f"[Downloader Error] {url} yuklashda xatolik: {e}")
            return None

    @staticmethod
    def extract_audio_snippet(video_path: Path, max_duration_sec: int = 30) -> Optional[Path]:
        """Extracts short audio snippet (MP3) from video for Whisper dialogue transcription."""
        if not video_path.exists():
            return None

        ffmpeg_cmd = "ffmpeg"
        if FFMPEG_DIR and os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg.exe")):
            ffmpeg_cmd = os.path.join(FFMPEG_DIR, "ffmpeg.exe")

        out_audio = DOWNLOAD_DIR / f"audio_{uuid.uuid4().hex[:8]}.mp3"
        try:
            import subprocess
            cmd = [
                ffmpeg_cmd,
                "-i", str(video_path),
                "-t", str(max_duration_sec),
                "-vn",
                "-acodec", "libmp3lame",
                "-ar", "16000",
                "-ac", "1",
                "-b:a", "64k",
                str(out_audio),
                "-y"
            ]
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if out_audio.exists() and out_audio.stat().st_size > 1000:
                return out_audio
        except Exception as e:
            logger.warning(f"[Audio Snippet Extraction Warning] {e}")
        return None


downloader = DownloaderService()

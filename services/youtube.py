import asyncio
import os
import logging
from pathlib import Path
import yt_dlp
import aiohttp

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self, download_dir: Path):
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def _extract_info(self, url: str, playlist_flat: bool = True) -> dict:
        ydl_opts = {
            'extract_flat': playlist_flat,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'referer': 'https://www.youtube.com/',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def get_info(self, url: str, playlist_flat: bool = True) -> dict:
        loop = asyncio.get_running_loop()
        try:
            info = await loop.run_in_executor(None, self._extract_info, url, playlist_flat)
            return info
        except Exception as e:
            logger.error(f"Error extracting info for {url}: {e}", exc_info=True)
            raise e

    def _download(self, url: str, height: int, progress_hook=None) -> dict:
        # Construct format selector
        # We want video format with height <= requested height + best audio
        # If height is not available, yt-dlp will automatically select the best format <= height
        fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        
        outtmpl = str(self.download_dir / '%(title).150s-%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': fmt,
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'referer': 'https://www.youtube.com/',
        }
        
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            filepath = None
            if 'requested_downloads' in info and info['requested_downloads']:
                filepath = info['requested_downloads'][0].get('filepath')
            
            if not filepath or not os.path.exists(filepath):
                # Fallback: find it by looking for the video id in the filename
                video_id = info.get('id')
                for f in self.download_dir.iterdir():
                    if video_id in f.name and f.suffix in ['.mp4', '.mkv', '.webm']:
                        filepath = str(f)
                        break
            
            # Extract metadata from requested downloads or info
            duration = info.get('duration')
            width = info.get('width')
            downloaded_height = info.get('height')
            
            req_downloads = info.get('requested_downloads', [{}])
            if req_downloads:
                width = req_downloads[0].get('width') or width
                downloaded_height = req_downloads[0].get('height') or downloaded_height
                
            return {
                'filepath': filepath,
                'title': info.get('title'),
                'duration': duration,
                'width': width,
                'height': downloaded_height,
                'thumbnail_url': info.get('thumbnail'),
                'size': os.path.getsize(filepath) if filepath and os.path.exists(filepath) else 0
            }

    async def download(self, url: str, height: int, progress_hook=None) -> dict:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._download, url, height, progress_hook)
        except Exception as e:
            logger.error(f"Error downloading {url} at {height}p: {e}", exc_info=True)
            raise e

    async def download_thumbnail(self, url: str) -> str:
        if not url:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        suffix = Path(url).suffix
                        if not suffix or len(suffix) > 5 or '?' in suffix:
                            suffix = '.jpg'
                        thumb_path = self.download_dir / f"thumb_{os.urandom(4).hex()}{suffix}"
                        with open(thumb_path, 'wb') as f:
                            f.write(await response.read())
                        return str(thumb_path)
        except Exception as e:
            logger.error(f"Failed to download thumbnail from {url}: {e}")
        return None

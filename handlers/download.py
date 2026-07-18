import os
import re
import logging
from pathlib import Path
from aiogram import Router, F, html
from aiogram.types import Message, CallbackQuery, FSInputFile, URLInputFile
from keyboards.inline import (
    get_quality_keyboard, 
    get_choice_keyboard, 
    QualityCallback, 
    DownloadChoiceCallback
)
from services.youtube import YouTubeService
from config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)
router = Router(name="download")
youtube_service = YouTubeService(DOWNLOAD_DIR)

# Regex patterns for YouTube videos and playlists
YOUTUBE_VIDEO_REGEX = re.compile(
    r'(?:https?://)?(?:www\.|m\.)?(?:youtu\.be/|youtube\.com/(?:embed/|v/|watch\?v=|watch\?.+&v=|shorts/|live/))([\w-]{11})'
)
YOUTUBE_PLAYLIST_REGEX = re.compile(
    r'(?:https?://)?(?:www\.|m\.)?youtube\.com/playlist\?list=([\w-]+)'
)

def format_duration(seconds: int) -> str:
    if not seconds:
        return "Неизвестно"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

@router.message(F.text)
async def handle_message(message: Message):
    text = message.text.strip()
    
    video_match = YOUTUBE_VIDEO_REGEX.search(text)
    playlist_match = YOUTUBE_PLAYLIST_REGEX.search(text)
    
    video_id = video_match.group(1) if video_match else None
    playlist_id = playlist_match.group(1) if playlist_match else None
    
    if not video_id and not playlist_id:
        return  # Ignore messages without YouTube links
        
    # If both video and playlist IDs are found
    if video_id and playlist_id:
        await message.answer(
            "🔍 В вашей ссылке обнаружены и видео, и плейлист.\n"
            "Что бы вы хотели скачать?",
            reply_markup=get_choice_keyboard(video_id, playlist_id)
        )
        return
        
    # If only playlist ID is found
    if playlist_id:
        await show_playlist_options(message, playlist_id)
        return
        
    # If only video ID is found
    if video_id:
        await show_video_options(message, video_id)
        return

async def show_video_options(message: Message, video_id: str):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    status = await message.answer("🔍 Анализ видео...")
    
    try:
        info = await youtube_service.get_info(video_url, playlist_flat=False)
        title = info.get('title', 'Видео')
        duration = info.get('duration', 0)
        thumbnail_url = info.get('thumbnail')
        
        caption = (
            f"🎬 {html.bold(title)}\n"
            f"⏱ Длительность: {format_duration(duration)}\n\n"
            f"Выберите желаемое качество для скачивания:"
        )
        
        keyboard = get_quality_keyboard(action="vid", target_id=video_id)
        
        if thumbnail_url:
            await message.answer_photo(
                photo=thumbnail_url,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await status.delete()
        else:
            await status.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Failed to show video options: {e}")
        await status.edit_text("❌ Не удалось извлечь информацию о видео. Попробуйте еще раз.")

async def show_playlist_options(message: Message, playlist_id: str):
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    status = await message.answer("🔍 Анализ плейлиста...")
    
    try:
        info = await youtube_service.get_info(playlist_url, playlist_flat=True)
        title = info.get('title', 'Плейлист')
        entries = info.get('entries', [])
        count = len(entries)
        
        caption = (
            f"📁 Плейлист: {html.bold(title)}\n"
            f"🎬 Количество видео: {html.bold(str(count))}\n\n"
            f"Выберите качество для скачивания всех видео из плейлиста:"
        )
        
        keyboard = get_quality_keyboard(action="pl", target_id=playlist_id)
        await status.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Failed to show playlist options: {e}")
        await status.edit_text("❌ Не удалось извлечь информацию о плейлисте. Попробуйте еще раз.")

# Callback query handler for double-choice (video or playlist)
@router.callback_query(DownloadChoiceCallback.filter())
async def process_choice(callback_query: CallbackQuery, callback_data: DownloadChoiceCallback):
    await callback_query.answer()
    
    # Delete choice message
    await callback_query.message.delete()
    
    if callback_data.choice == "vid":
        await show_video_options(callback_query.message, callback_data.video_id)
    elif callback_data.choice == "pl":
        await show_playlist_options(callback_query.message, callback_data.playlist_id)

# Callback query handler for quality selection
@router.callback_query(QualityCallback.filter())
async def process_quality_selection(callback_query: CallbackQuery, callback_data: QualityCallback):
    await callback_query.answer()
    
    action = callback_data.action
    quality = callback_data.quality
    target_id = callback_data.target_id
    
    # We edit the message to show downloading state
    await callback_query.message.edit_reply_markup(reply_markup=None)
    
    if action == "vid":
        url = f"https://www.youtube.com/watch?v={target_id}"
        status_msg = await callback_query.message.answer("⏳ Скачивание видео с YouTube...")
        
        filepath = None
        thumb_path = None
        try:
            # Download video
            result = await youtube_service.download(url, quality)
            filepath = result.get('filepath')
            
            if not filepath or not os.path.exists(filepath):
                await status_msg.edit_text("❌ Ошибка при скачивании видео.")
                return
                
            file_size = result['size']
            if file_size > 50 * 1024 * 1024:
                file_size_mb = file_size / (1024 * 1024)
                await status_msg.edit_text(
                    f"⚠️ Файл слишком большой ({file_size_mb:.1f} МБ).\n"
                    f"Лимит Telegram на отправку файлов ботами — 50 МБ.\n"
                    f"Попробуйте выбрать меньшее разрешение (например, 480p или 720p)."
                )
                return
                
            await status_msg.edit_text("📤 Отправка видео в Telegram...")
            
            # Download thumbnail
            thumb_path = await youtube_service.download_thumbnail(result.get('thumbnail_url'))
            
            # Send video
            video_file = FSInputFile(filepath)
            thumb_file = FSInputFile(thumb_path) if thumb_path else None
            
            await callback_query.message.answer_video(
                video=video_file,
                caption=f"🎬 {result['title']}\n\n🔍 Разрешение: {result['height']}p",
                duration=result.get('duration'),
                width=result.get('width'),
                height=result.get('height'),
                thumbnail=thumb_file
            )
            
            await status_msg.delete()
            
        except Exception as e:
            logger.error(f"Error handling video download: {e}", exc_info=True)
            await status_msg.edit_text("❌ Произошла ошибка во время скачивания или отправки видео.")
        finally:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
            
    elif action == "pl":
        url = f"https://www.youtube.com/playlist?list={target_id}"
        status_msg = await callback_query.message.answer("⏳ Получение списка видео из плейлиста...")
        
        try:
            info = await youtube_service.get_info(url, playlist_flat=True)
            entries = info.get('entries', [])
            
            if not entries:
                await status_msg.edit_text("❌ Плейлист пуст или скрыт.")
                return
                
            total_videos = len(entries)
            MAX_PLAYLIST_SIZE = 15
            
            if total_videos > MAX_PLAYLIST_SIZE:
                await status_msg.edit_text(
                    f"⚠️ В плейлисте {total_videos} видео.\n"
                    f"Бот может скачать не более {MAX_PLAYLIST_SIZE} видео за раз, чтобы избежать блокировок.\n"
                    f"Пожалуйста, присылайте ссылки на видео отдельно."
                )
                return
                
            await status_msg.edit_text(f"📥 Начинаем загрузку плейлиста ({total_videos} видео)...")
            
            for idx, entry in enumerate(entries, start=1):
                video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                video_title = entry.get('title', f"Видео {idx}")
                
                prog_msg = await callback_query.message.answer(
                    f"⏳ [{idx}/{total_videos}] Скачивание: {html.italic(video_title)}..."
                )
                
                filepath = None
                thumb_path = None
                try:
                    result = await youtube_service.download(video_url, quality)
                    filepath = result.get('filepath')
                    
                    if not filepath or not os.path.exists(filepath):
                        await prog_msg.edit_text(f"❌ [{idx}/{total_videos}] Не удалось скачать видео.")
                        continue
                        
                    file_size = result['size']
                    if file_size > 50 * 1024 * 1024:
                        file_size_mb = file_size / (1024 * 1024)
                        await prog_msg.edit_text(
                            f"⚠️ [{idx}/{total_videos}] Файл слишком большой ({file_size_mb:.1f} МБ).\n"
                            f"Лимит: 50 МБ."
                        )
                        continue
                        
                    await prog_msg.edit_text(f"📤 [{idx}/{total_videos}] Отправка в Telegram...")
                    
                    thumb_path = await youtube_service.download_thumbnail(result.get('thumbnail_url'))
                    
                    video_file = FSInputFile(filepath)
                    thumb_file = FSInputFile(thumb_path) if thumb_path else None
                    
                    await callback_query.message.answer_video(
                        video=video_file,
                        caption=f"🎬 {result['title']}\n\n🔍 Разрешение: {result['height']}p (Плейлист)",
                        duration=result.get('duration'),
                        width=result.get('width'),
                        height=result.get('height'),
                        thumbnail=thumb_file
                    )
                    
                    await prog_msg.delete()
                    
                except Exception as ex:
                    logger.error(f"Error processing item {idx} in playlist: {ex}")
                    await prog_msg.edit_text(f"❌ [{idx}/{total_videos}] Ошибка при обработке видео.")
                finally:
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
                    if thumb_path and os.path.exists(thumb_path):
                        os.remove(thumb_path)
                    
            await status_msg.edit_text("✅ Загрузка плейлиста завершена!")
            
        except Exception as e:
            logger.error(f"Error downloading playlist: {e}", exc_info=True)
            await status_msg.edit_text("❌ Произошла ошибка при обработке плейлиста.")

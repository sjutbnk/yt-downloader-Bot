from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

class QualityCallback(CallbackData, prefix="dl_q"):
    action: str        # "vid" or "pl"
    quality: int       # 480, 720, 1080, 1440
    target_id: str     # YouTube ID (video or playlist)

class DownloadChoiceCallback(CallbackData, prefix="dl_choice"):
    choice: str        # "vid" or "pl"
    video_id: str
    playlist_id: str

def get_quality_keyboard(action: str, target_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Supported qualities
    qualities = [
        ("480p", 480),
        ("720p (HD)", 720),
        ("1080p (FHD)", 1080),
        ("1440p (2K)", 1440)
    ]
    
    for label, q_val in qualities:
        builder.button(
            text=label,
            callback_data=QualityCallback(action=action, quality=q_val, target_id=target_id)
        )
        
    builder.adjust(2)  # 2 columns
    return builder.as_markup()

def get_choice_keyboard(video_id: str, playlist_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎬 Скачать только видео",
        callback_data=DownloadChoiceCallback(choice="vid", video_id=video_id, playlist_id=playlist_id)
    )
    builder.button(
        text="📁 Скачать весь плейлист",
        callback_data=DownloadChoiceCallback(choice="pl", video_id=video_id, playlist_id=playlist_id)
    )
    builder.adjust(1)
    return builder.as_markup()


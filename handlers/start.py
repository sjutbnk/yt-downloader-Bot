from aiogram import Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="start")

@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Handle the /start command.
    """
    welcome_text = (
        f"👋 Привет, {html.bold(message.from_user.first_name)}!\n\n"
        f"Отправь мне ссылку на видео или плейлист.\n\n"
        f"ℹ️ Используй /help, чтобы узнать больше о лимитах Telegram."
    )
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handle the /help command.
    """
    help_text = (
        f"⚙️ {html.bold('Справка по использованию:')}\n\n"
        f"1️⃣ Отправь мне ссылку на YouTube-видео или плейлист.\n"
        f"2️⃣ Выбери желаемое качество (от 480p до 1440p).\n"
        f"3️⃣ Дождись завершения скачивания и отправки файла.\n\n"
        f"⚠️ {html.bold('Важные ограничения Telegram:')}\n"
        f"• Максимальный размер файла для отправки обычным ботом — {html.bold('50 МБ')}.\n"
        f"• Если видео в выбранном качестве превысит этот лимит, я постараюсь предупредить тебя или предложу более низкое качество.\n"
        f"• При скачивании плейлистов видео загружаются и отправляются по очереди."
    )
    await message.answer(help_text, parse_mode="HTML")

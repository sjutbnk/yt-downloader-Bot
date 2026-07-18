import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN, DOWNLOAD_DIR
from handlers import router as main_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def set_commands(bot: Bot):
    """
    Register bot commands in Telegram menu interface.
    """
    commands = [
        BotCommand(command="start", description="Запустить бота / Начало работы"),
        BotCommand(command="help", description="Справка по лимитам и работе"),
    ]
    await bot.set_my_commands(commands)

def cleanup_downloads_dir():
    """
    Clear downloads folder of any leftover temporary files.
    """
    if DOWNLOAD_DIR.exists():
        logger.info(f"Cleaning up download directory: {DOWNLOAD_DIR}")
        for path in DOWNLOAD_DIR.glob('*'):
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
            except Exception as e:
                logger.warning(f"Could not delete {path}: {e}")

async def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is missing in the environment or .env file! Exiting.")
        sys.exit(1)

    # Clean up any leftover downloaded files from previous runs
    cleanup_downloads_dir()

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Include main router
    dp.include_router(main_router)
    
    # Startup actions
    await set_commands(bot)
    
    logger.info("Bot started successfully. Listening for updates...")
    
    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        # Final cleanup
        cleanup_downloads_dir()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

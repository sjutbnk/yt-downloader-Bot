import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    # We will log or warn, but let's raise a clear error so they know why it fails
    # Wait, during development/run, we don't want it to crash immediately if they haven't set it yet,
    # but it's better to check it when starting.
    pass

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"
WEB_DIR = BASE_DIR / "web"

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        self.scan_interval = float(os.getenv("SCAN_INTERVAL", "2.0"))
        self.auto_solve_single = os.getenv("AUTO_SOLVE_SINGLE", "true").lower() in ("true", "1", "yes")
        self.port = int(os.getenv("PORT", "5055"))
        self.host = os.getenv("HOST", "127.0.0.1")
        self.enable_desktop_overlay = os.getenv("ENABLE_DESKTOP_OVERLAY", "true").lower() in ("true", "1", "yes")
        self.open_chatgpt = os.getenv("OPEN_CHATGPT", "true").lower() in ("true", "1", "yes")
        self.show_dev_window = os.getenv("SHOW_DEV_WINDOW", "false").lower() in ("true", "1", "yes")

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

config = Config()

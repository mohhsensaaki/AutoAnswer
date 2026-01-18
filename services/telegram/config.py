import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram API credentials - get from https://my.telegram.org
    API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
    API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    
    # Session file name (stores login state)
    SESSION_NAME = os.getenv("SESSION_NAME", "telegram_user_session")
    
    # Callback URL for forwarding messages
    CALLBACK_URL = os.getenv("CALLBACK_URL", "")
    
    # HTTP request settings
    CALLBACK_TIMEOUT = int(os.getenv("CALLBACK_TIMEOUT", "10"))
    CALLBACK_RETRIES = int(os.getenv("CALLBACK_RETRIES", "3"))
    
    # Media download settings
    ENABLE_MEDIA_DOWNLOAD = os.getenv("ENABLE_MEDIA_DOWNLOAD", "true").lower() == "true"
    MAX_MEDIA_SIZE = int(os.getenv("MAX_MEDIA_SIZE", "10"))  # MB
    MEDIA_GROUP_TIMEOUT = float(os.getenv("MEDIA_GROUP_TIMEOUT", "5.0"))  # seconds
    
    # Media types to download (comma-separated)
    # Options: photo, video, audio, voice, document, sticker, animation
    # Use "all" to download all types
    _media_types_raw = os.getenv("DOWNLOAD_MEDIA_TYPES", "all")
    DOWNLOAD_MEDIA_TYPES = (
        {"photo", "video", "audio", "voice", "document", "sticker", "animation"}
        if _media_types_raw.lower() == "all"
        else {t.strip().lower() for t in _media_types_raw.split(",") if t.strip()}
    )
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        errors = []
        
        if cls.API_ID == 0:
            errors.append("TELEGRAM_API_ID is required")
        
        if not cls.API_HASH:
            errors.append("TELEGRAM_API_HASH is required")
        
        if not cls.CALLBACK_URL:
            errors.append("CALLBACK_URL is required")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))


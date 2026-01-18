"""
Media Service - Handles downloading media from Telegram messages as base64.
"""

import base64
import logging
from io import BytesIO

from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument,
    MessageMediaContact, MessageMediaGeo,
    MessageMediaWebPage, MessageMediaPoll
)

from services.telegram.config import Config

logger = logging.getLogger(__name__)


class MediaService:
    """Service for downloading Telegram media as base64."""
    
    # Media types that can be downloaded as files
    DOWNLOADABLE_TYPES = (MessageMediaPhoto, MessageMediaDocument)
    
    # Non-downloadable media types (metadata only)
    NON_DOWNLOADABLE_TYPES = (
        MessageMediaContact, MessageMediaGeo,
        MessageMediaWebPage, MessageMediaPoll
    )
    
    @staticmethod
    def is_downloadable(message) -> bool:
        """Check if the message has downloadable media."""
        if not message.media:
            return False
        return isinstance(message.media, MediaService.DOWNLOADABLE_TYPES)
    
    @staticmethod
    def get_media_size(message) -> int | None:
        """Get the size of media in bytes, if available."""
        media = message.media
        if not media:
            return None
        
        if isinstance(media, MessageMediaPhoto):
            # Photos don't have a direct size, estimate based on largest size
            if media.photo and media.photo.sizes:
                # Get the largest photo size
                for size in reversed(media.photo.sizes):
                    if hasattr(size, 'size'):
                        return size.size
            return None
        
        elif isinstance(media, MessageMediaDocument):
            if media.document:
                return media.document.size
        
        return None
    
    @staticmethod
    def get_mime_type(message) -> str:
        """Get the MIME type of the media."""
        media = message.media
        if not media:
            return "application/octet-stream"
        
        if isinstance(media, MessageMediaPhoto):
            return "image/jpeg"
        
        elif isinstance(media, MessageMediaDocument):
            if media.document:
                return media.document.mime_type or "application/octet-stream"
        
        return "application/octet-stream"
    
    @staticmethod
    def get_filename(message) -> str | None:
        """Get the filename of the media if available."""
        media = message.media
        if not media:
            return None
        
        if isinstance(media, MessageMediaDocument) and media.document:
            for attr in media.document.attributes:
                if type(attr).__name__ == "DocumentAttributeFilename":
                    return attr.file_name
        
        return None
    
    @staticmethod
    def get_media_type(message) -> str:
        """Get a human-readable media type."""
        media = message.media
        if not media:
            return "unknown"
        
        if isinstance(media, MessageMediaPhoto):
            return "photo"
        
        elif isinstance(media, MessageMediaDocument):
            if media.document:
                # Check document attributes for specific types
                for attr in media.document.attributes:
                    attr_name = type(attr).__name__
                    if attr_name == "DocumentAttributeVideo":
                        return "video"
                    elif attr_name == "DocumentAttributeAudio":
                        return "voice" if attr.voice else "audio"
                    elif attr_name == "DocumentAttributeSticker":
                        return "sticker"
                    elif attr_name == "DocumentAttributeAnimated":
                        return "animation"
                return "document"
        
        return "unknown"
    
    @staticmethod
    def is_type_enabled(message) -> bool:
        """Check if the media type is enabled for download in config."""
        media_type = MediaService.get_media_type(message)
        return media_type in Config.DOWNLOAD_MEDIA_TYPES
    
    @staticmethod
    def _build_skipped_result(message, reason: str, violation_type: str) -> dict:
        """Build a result dict for skipped media."""
        return {
            "type": MediaService.get_media_type(message),
            "mime_type": MediaService.get_mime_type(message),
            "filename": MediaService.get_filename(message),
            "size": MediaService.get_media_size(message),
            "base64": None,
            "skipped": True,
            "violation": {
                "type": violation_type,
                "reason": reason
            }
        }
    
    @staticmethod
    async def process_media(client, message) -> dict | None:
        """
        Process media from a message - download if allowed, or return violation info.
        
        This method always returns media info if media exists, including
        violation details when media cannot be downloaded due to policy.
        
        Args:
            client: The Telegram client instance
            message: The Telegram message with media
            
        Returns:
            dict with media data/metadata, or None if no media present
        """
        # No media at all
        if not message.media:
            return None
        
        media_type = MediaService.get_media_type(message)
        size = MediaService.get_media_size(message)
        
        # Check if media download is globally disabled
        if not Config.ENABLE_MEDIA_DOWNLOAD:
            logger.debug("Media download disabled globally")
            return MediaService._build_skipped_result(
                message,
                reason="Media download is disabled in configuration",
                violation_type="download_disabled"
            )
        
        # Check if this is a non-downloadable type (contact, location, etc.)
        if not MediaService.is_downloadable(message):
            logger.debug(f"Media type not downloadable: {type(message.media).__name__}")
            return MediaService._build_skipped_result(
                message,
                reason=f"Media type '{type(message.media).__name__}' cannot be downloaded as file",
                violation_type="not_downloadable"
            )
        
        # Check if this media type is enabled in config
        if not MediaService.is_type_enabled(message):
            logger.debug(f"Media type '{media_type}' not in DOWNLOAD_MEDIA_TYPES, skipping")
            return MediaService._build_skipped_result(
                message,
                reason=f"Media type '{media_type}' is not enabled for download",
                violation_type="type_not_enabled"
            )
        
        # Check file size limit
        max_size_bytes = Config.MAX_MEDIA_SIZE * 1024 * 1024
        if size and size > max_size_bytes:
            logger.warning(
                f"Media size ({size / 1024 / 1024:.2f} MB) exceeds limit "
                f"({Config.MAX_MEDIA_SIZE} MB), skipping download"
            )
            return MediaService._build_skipped_result(
                message,
                reason=f"File size ({size / 1024 / 1024:.2f} MB) exceeds {Config.MAX_MEDIA_SIZE} MB limit",
                violation_type="size_exceeded"
            )
        
        # All checks passed, download the media
        try:
            buffer = BytesIO()
            await client.download_media(message, file=buffer)
            
            media_bytes = buffer.getvalue()
            base64_data = base64.b64encode(media_bytes).decode('utf-8')
            
            result = {
                "type": media_type,
                "mime_type": MediaService.get_mime_type(message),
                "filename": MediaService.get_filename(message),
                "size": len(media_bytes),
                "base64": base64_data,
                "skipped": False,
                "violation": None
            }
            
            logger.debug(
                f"Downloaded media: {result['type']} "
                f"({result['size'] / 1024:.2f} KB)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
            return MediaService._build_skipped_result(
                message,
                reason=f"Download failed: {str(e)}",
                violation_type="download_error"
            )
    
    @staticmethod
    async def download_as_base64(client, message) -> dict | None:
        """
        Download media from a message and return as base64.
        
        Deprecated: Use process_media() instead for full violation reporting.
        
        Args:
            client: The Telegram client instance
            message: The Telegram message with media
            
        Returns:
            dict with base64 data and metadata, or None if skipped
        """
        result = await MediaService.process_media(client, message)
        
        # For backward compatibility, return None if skipped (except for size exceeded)
        if result and result.get("skipped"):
            violation_type = result.get("violation", {}).get("type")
            # Only return result for size_exceeded and download_error (original behavior)
            if violation_type in ("size_exceeded", "download_error"):
                return result
            return None
        
        return result


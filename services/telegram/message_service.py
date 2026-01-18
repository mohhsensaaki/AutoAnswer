"""
Message Service - Handles parsing Telegram messages into structured payloads.
"""

from datetime import datetime
from telethon.tl.types import (
    User, Chat, Channel,
    MessageMediaPhoto, MessageMediaDocument,
    MessageMediaWebPage, MessageMediaGeo,
    MessageMediaContact, MessageMediaPoll
)


class MessageService:
    """Service for parsing and transforming Telegram messages."""
    
    @staticmethod
    async def build_payload(
        message,
        media_files: list | None = None,
        is_media_group: bool = False,
        media_group_id: str | None = None
    ) -> dict:
        """
        Build a JSON-serializable payload from a Telegram message.
        
        Args:
            message: The Telegram message
            media_files: Optional list of downloaded media files (base64)
            is_media_group: Whether this is part of a media group (album)
            media_group_id: The media group ID if applicable
        """
        payload = {
            "message_id": message.id,
            "date": message.date.isoformat() if message.date else None,
            "text": message.text or message.message,
            "raw_text": message.raw_text,
            "chat": await MessageService.get_chat_info(message),
            "sender": await MessageService.get_sender_info(message),
            "reply_to_message_id": message.reply_to.reply_to_msg_id if message.reply_to else None,
            "forward": MessageService.get_forward_info(message),
            "media": MessageService.get_media_info(message),
            "entities": MessageService.get_entities_info(message),
            "is_outgoing": message.out,
            "received_at": datetime.utcnow().isoformat()
        }
        
        # Add media files if provided
        if media_files:
            payload["media_files"] = media_files
        
        # Add media group info if applicable
        if is_media_group:
            payload["is_media_group"] = True
            payload["media_group_id"] = media_group_id
        
        return payload
    
    @staticmethod
    async def get_chat_info(message) -> dict:
        """Extract chat information from a message."""
        chat = await message.get_chat()
        
        info = {
            "id": message.chat_id,
            "type": "unknown"
        }
        
        if isinstance(chat, User):
            info["type"] = "private"
            info["title"] = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
            info["username"] = chat.username
        elif isinstance(chat, Chat):
            info["type"] = "group"
            info["title"] = chat.title
        elif isinstance(chat, Channel):
            info["type"] = "channel" if chat.broadcast else "supergroup"
            info["title"] = chat.title
            info["username"] = chat.username
        
        return info
    
    @staticmethod
    async def get_sender_info(message) -> dict:
        """Extract sender information from a message."""
        sender = await message.get_sender()
        
        if sender is None:
            return {"id": None, "name": "Unknown"}
        
        if isinstance(sender, User):
            return {
                "id": sender.id,
                "name": f"{sender.first_name or ''} {sender.last_name or ''}".strip(),
                "username": sender.username,
                "is_bot": sender.bot,
                "phone": sender.phone
            }
        elif isinstance(sender, (Chat, Channel)):
            return {
                "id": sender.id,
                "name": sender.title,
                "username": getattr(sender, "username", None),
                "is_bot": False
            }
        
        return {"id": None, "name": "Unknown"}
    
    @staticmethod
    def get_forward_info(message) -> dict | None:
        """Extract forward information if message is forwarded."""
        fwd = message.forward
        if not fwd:
            return None
        
        return {
            "date": fwd.date.isoformat() if fwd.date else None,
            "from_id": fwd.from_id.user_id if hasattr(fwd.from_id, 'user_id') else None,
            "from_name": fwd.from_name,
            "channel_id": fwd.chat_id if fwd.chat_id else None,
            "channel_post": fwd.channel_post
        }
    
    @staticmethod
    def get_media_info(message) -> dict | None:
        """Extract media information from a message."""
        media = message.media
        if not media:
            return None
        
        info = {"type": "unknown"}
        
        if isinstance(media, MessageMediaPhoto):
            info["type"] = "photo"
            if media.photo:
                info["id"] = media.photo.id
                info["access_hash"] = media.photo.access_hash
        
        elif isinstance(media, MessageMediaDocument):
            info["type"] = "document"
            if media.document:
                info["id"] = media.document.id
                info["access_hash"] = media.document.access_hash
                info["mime_type"] = media.document.mime_type
                info["size"] = media.document.size
                
                # Check for specific document types
                for attr in media.document.attributes:
                    attr_name = type(attr).__name__
                    if attr_name == "DocumentAttributeFilename":
                        info["filename"] = attr.file_name
                    elif attr_name == "DocumentAttributeVideo":
                        info["type"] = "video"
                        info["duration"] = attr.duration
                        info["width"] = attr.w
                        info["height"] = attr.h
                    elif attr_name == "DocumentAttributeAudio":
                        info["type"] = "voice" if attr.voice else "audio"
                        info["duration"] = attr.duration
                        info["title"] = attr.title
                        info["performer"] = attr.performer
                    elif attr_name == "DocumentAttributeSticker":
                        info["type"] = "sticker"
                        info["alt"] = attr.alt
                    elif attr_name == "DocumentAttributeAnimated":
                        info["type"] = "animation"
        
        elif isinstance(media, MessageMediaWebPage):
            info["type"] = "webpage"
            if media.webpage and hasattr(media.webpage, 'url'):
                info["url"] = media.webpage.url
                info["title"] = getattr(media.webpage, 'title', None)
                info["description"] = getattr(media.webpage, 'description', None)
        
        elif isinstance(media, MessageMediaGeo):
            info["type"] = "location"
            if media.geo:
                info["latitude"] = media.geo.lat
                info["longitude"] = media.geo.long
        
        elif isinstance(media, MessageMediaContact):
            info["type"] = "contact"
            info["phone"] = media.phone_number
            info["first_name"] = media.first_name
            info["last_name"] = media.last_name
            info["user_id"] = media.user_id
        
        elif isinstance(media, MessageMediaPoll):
            info["type"] = "poll"
            if media.poll:
                info["question"] = media.poll.question.text if hasattr(media.poll.question, 'text') else str(media.poll.question)
                info["answers"] = [
                    {"text": a.text.text if hasattr(a.text, 'text') else str(a.text), "data": a.option.hex()}
                    for a in media.poll.answers
                ]
        
        return info
    
    @staticmethod
    def get_entities_info(message) -> list | None:
        """Extract message entities (mentions, links, etc.)."""
        if not message.entities:
            return None
        
        entities = []
        for entity in message.entities:
            entity_info = {
                "type": type(entity).__name__.replace("MessageEntity", "").lower(),
                "offset": entity.offset,
                "length": entity.length
            }
            
            # Add extra info for specific entity types
            if hasattr(entity, "url"):
                entity_info["url"] = entity.url
            if hasattr(entity, "user_id"):
                entity_info["user_id"] = entity.user_id
            if hasattr(entity, "language"):
                entity_info["language"] = entity.language
            
            entities.append(entity_info)
        
        return entities


"""
Telegram User Client - Forwards received messages to a callback URL.

Usage:
    1. Copy .env.example to .env and fill in your credentials
    2. Run: python main.py
    3. On first run, you'll be prompted for your phone number and verification code
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List

from telethon import TelegramClient, events

from services.telegram.config import Config
from services.telegram import MessageService, CallbackService, MediaService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@dataclass
class MediaGroupBuffer:
    """Buffer for collecting media group (album) messages."""
    messages: List = field(default_factory=list)
    timer_task: asyncio.Task | None = None


class TelegramUserClient:
    def __init__(self):
        Config.validate()
        self.client = TelegramClient(
            Config.SESSION_NAME,
            Config.API_ID,
            Config.API_HASH
        )
        self.callback_service = CallbackService()
        
        # Buffer for media groups (albums)
        # Key: media_group_id, Value: MediaGroupBuffer
        self.media_group_buffers: Dict[str, MediaGroupBuffer] = {}
    
    async def start(self):
        """Start the Telegram client and begin listening for messages."""
        logger.info("Starting Telegram client...")
        
        # Start callback service
        await self.callback_service.start()
        
        # Register event handler for incoming messages
        self.client.on(events.NewMessage(incoming=True))(self.on_new_message)
        
        # Start the client (will prompt for phone/code on first run)
        await self.client.start()
        
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username or 'no username'}) [ID: {me.id}]")
        logger.info(f"Callback URL: {Config.CALLBACK_URL}")
        logger.info(f"Media download: {'enabled' if Config.ENABLE_MEDIA_DOWNLOAD else 'disabled'}")
        if Config.ENABLE_MEDIA_DOWNLOAD:
            logger.info(f"Max media size: {Config.MAX_MEDIA_SIZE} MB")
            logger.info(f"Media types: {', '.join(sorted(Config.DOWNLOAD_MEDIA_TYPES))}")
        logger.info("Listening for incoming messages...")
        
        # Keep running until disconnected
        await self.client.run_until_disconnected()
    
    async def stop(self):
        """Stop the client and cleanup."""
        # Cancel any pending media group timers
        for buffer in self.media_group_buffers.values():
            if buffer.timer_task and not buffer.timer_task.done():
                buffer.timer_task.cancel()
        
        await self.callback_service.stop()
        await self.client.disconnect()
        logger.info("Client stopped.")
    
    async def on_new_message(self, event):
        """Handle incoming messages and forward to callback URL."""
        try:
            message = event.message
            
            # Check if this is part of a media group (album)
            if message.grouped_id:
                await self._handle_media_group_message(message)
            else:
                await self._process_single_message(message)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def _handle_media_group_message(self, message):
        """Buffer media group messages and process after timeout."""
        group_id = str(message.grouped_id)
        
        # Create buffer if doesn't exist
        if group_id not in self.media_group_buffers:
            self.media_group_buffers[group_id] = MediaGroupBuffer()
        
        buffer = self.media_group_buffers[group_id]
        buffer.messages.append(message)
        
        logger.debug(f"Buffered message for media group {group_id} (total: {len(buffer.messages)})")
        
        # Cancel existing timer if any
        if buffer.timer_task and not buffer.timer_task.done():
            buffer.timer_task.cancel()
        
        # Start new timer to process the group
        buffer.timer_task = asyncio.create_task(
            self._process_media_group_after_timeout(group_id)
        )
    
    async def _process_media_group_after_timeout(self, group_id: str):
        """Wait for timeout then process the media group."""
        try:
            await asyncio.sleep(Config.MEDIA_GROUP_TIMEOUT)
            await self._process_media_group(group_id)
        except asyncio.CancelledError:
            # Timer was cancelled, new messages arrived
            pass
    
    async def _process_media_group(self, group_id: str):
        """Process all messages in a media group and send as single callback."""
        if group_id not in self.media_group_buffers:
            return
        
        buffer = self.media_group_buffers.pop(group_id)
        messages = buffer.messages
        
        if not messages:
            return
        
        logger.info(f"Processing media group {group_id} with {len(messages)} items")
        
        # Process all media files (includes violation info if not downloaded)
        media_files = []
        downloaded_count = 0
        skipped_count = 0
        
        for msg in messages:
            media_data = await MediaService.process_media(self.client, msg)
            if media_data:
                media_files.append(media_data)
                if media_data.get("skipped"):
                    skipped_count += 1
                else:
                    downloaded_count += 1
        
        # Use the first message as the base for the payload
        first_message = messages[0]
        
        # Build payload with all media files
        payload = await MessageService.build_payload(
            first_message,
            media_files=media_files if media_files else None,
            is_media_group=True,
            media_group_id=group_id
        )
        
        # Add info about all messages in the group
        payload["media_group_messages"] = [
            {
                "message_id": msg.id,
                "text": msg.text or msg.message,
                "media": MessageService.get_media_info(msg)
            }
            for msg in messages
        ]
        
        # Log the message
        sender_info = payload.get("sender", {})
        chat_info = payload.get("chat", {})
        skip_info = f" ({skipped_count} skipped)" if skipped_count > 0 else ""
        logger.info(
            f"Media group from {sender_info.get('name', 'Unknown')} "
            f"in {chat_info.get('title', 'Private Chat')}: "
            f"{downloaded_count} downloaded{skip_info}"
        )
        
        # Send to callback URL
        await self.callback_service.send(payload)
    
    async def _process_single_message(self, message):
        """Process a single (non-grouped) message."""
        # Process media if present (includes violation info if not downloaded)
        media_files = []
        media_data = await MediaService.process_media(self.client, message)
        if media_data:
            media_files.append(media_data)
        
        # Build the payload using MessageService
        payload = await MessageService.build_payload(
            message,
            media_files=media_files if media_files else None
        )
        
        # Log the message
        sender_info = payload.get("sender", {})
        chat_info = payload.get("chat", {})
        text_preview = (payload.get('text', '') or '')[:50]
        
        # Build media info for logging
        if media_files:
            media_item = media_files[0]
            if media_item.get("skipped"):
                violation = media_item.get("violation", {})
                media_info = f" [{media_item['type']} SKIPPED: {violation.get('type', 'unknown')}]"
            else:
                media_info = f" [{media_item['type']}]"
        else:
            media_info = ""
        
        logger.info(
            f"New message from {sender_info.get('name', 'Unknown')} "
            f"in {chat_info.get('title', 'Private Chat')}: "
            f"{text_preview}...{media_info}"
        )
        
        # Send to callback URL using CallbackService
        await self.callback_service.send(payload)


async def main():
    client = TelegramUserClient()
    try:
        await client.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())

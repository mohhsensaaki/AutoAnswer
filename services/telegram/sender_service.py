"""
Sender Service - Handles sending messages with images to Telegram chats.
"""

import logging
from io import BytesIO
from typing import Optional

import aiohttp
from telethon import TelegramClient

logger = logging.getLogger(__name__)


class SenderService:
    """Service for sending messages with images to Telegram."""
    
    def __init__(self):
        self.http_session: Optional[aiohttp.ClientSession] = None
    
    async def start(self):
        """Initialize the HTTP session."""
        self.http_session = aiohttp.ClientSession()
        logger.debug("SenderService HTTP session started")
    
    async def stop(self):
        """Close the HTTP session."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.debug("SenderService HTTP session closed")
    
    async def download_image(self, url: str) -> bytes:
        """
        Download an image from a URL.
        
        Args:
            url: The URL to download the image from
            
        Returns:
            The image data as bytes
            
        Raises:
            Exception: If download fails
        """
        if not self.http_session:
            raise RuntimeError("SenderService not started. Call start() first.")
        
        try:
            async with self.http_session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download image: HTTP {response.status}")
                
                image_data = await response.read()
                logger.debug(f"Downloaded image from {url} ({len(image_data)} bytes)")
                return image_data
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error downloading image from {url}: {e}")
            raise Exception(f"Failed to download image: {e}")
    
    async def download_images(self, urls: list[str]) -> list[BytesIO]:
        """
        Download multiple images from URLs.
        
        Args:
            urls: List of URLs to download images from
            
        Returns:
            List of BytesIO objects containing image data
        """
        image_files = []
        for i, url in enumerate(urls):
            image_data = await self.download_image(url)
            image_file = BytesIO(image_data)
            image_file.name = f"image_{i}.jpg"
            image_files.append(image_file)
        return image_files
    
    async def send_message(
        self,
        client: TelegramClient,
        chat_id: int | str,
        image_urls: Optional[list[str]] = None,
        caption: Optional[str] = None
    ) -> dict:
        """
        Send a message with images and caption to a Telegram chat.
        
        Supports sending multiple images as an album.
        
        Args:
            client: The Telegram client instance
            chat_id: Target chat ID (int) or username (str like '@username')
            image_urls: List of image URLs to send (optional)
            caption: Caption text for the image/message
            
        Returns:
            dict with success status, message_ids, and chat_id
        """
        try:
            message_ids = []
            
            # If image URLs provided, download and send
            if image_urls and len(image_urls) > 0:
                image_files = await self.download_images(image_urls)
                
                if len(image_files) == 1:
                    # Single image - send as photo with caption
                    message = await client.send_file(
                        chat_id,
                        file=image_files[0],
                        caption=caption
                    )
                    message_ids.append(message.id)
                else:
                    # Multiple images - send as album
                    messages = await client.send_file(
                        chat_id,
                        file=image_files,
                        caption=caption
                    )
                    
                    # send_file returns list for albums
                    if isinstance(messages, list):
                        message_ids.extend([m.id for m in messages])
                    else:
                        message_ids.append(messages.id)
            else:
                # Send text message only
                message = await client.send_message(
                    chat_id,
                    message=caption or ""
                )
                message_ids.append(message.id)
            
            logger.info(f"Sent message(s) to chat {chat_id}, message_ids: {message_ids}")
            
            return {
                "success": True,
                "message_ids": message_ids,
                "chat_id": chat_id,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")
            return {
                "success": False,
                "message_ids": [],
                "chat_id": chat_id,
                "error": str(e)
            }

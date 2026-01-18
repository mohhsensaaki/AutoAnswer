"""
Callback Service - Handles sending message payloads to webhook URLs.
"""

import asyncio
import logging

import aiohttp

from services.telegram.config import Config

logger = logging.getLogger(__name__)


class CallbackService:
    """Service for sending message payloads to callback URLs."""
    
    def __init__(self):
        self.http_session: aiohttp.ClientSession | None = None
    
    async def start(self):
        """Initialize the HTTP session."""
        self.http_session = aiohttp.ClientSession()
        logger.debug("CallbackService HTTP session started")
    
    async def stop(self):
        """Close the HTTP session."""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            logger.debug("CallbackService HTTP session closed")
    
    async def send(self, payload: dict) -> bool:
        """
        Send message payload to callback URL with retries.
        
        Args:
            payload: The message payload to send
            
        Returns:
            True if callback was sent successfully, False otherwise
        """
        if not self.http_session:
            logger.error("CallbackService not started. Call start() first.")
            return False
        
        message_id = payload.get('message_id', 'unknown')
        
        for attempt in range(Config.CALLBACK_RETRIES):
            try:
                async with self.http_session.post(
                    Config.CALLBACK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=Config.CALLBACK_TIMEOUT),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Callback sent successfully for message {message_id}")
                        return True
                    else:
                        body = await response.text()
                        logger.warning(
                            f"Callback failed (attempt {attempt + 1}/{Config.CALLBACK_RETRIES}): "
                            f"HTTP {response.status} - {body[:200]}"
                        )
            
            except asyncio.TimeoutError:
                logger.warning(
                    f"Callback timeout (attempt {attempt + 1}/{Config.CALLBACK_RETRIES})"
                )
            except Exception as e:
                logger.warning(
                    f"Callback error (attempt {attempt + 1}/{Config.CALLBACK_RETRIES}): {e}"
                )
            
            # Wait before retry (exponential backoff)
            if attempt < Config.CALLBACK_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"Failed to send callback for message {message_id} after {Config.CALLBACK_RETRIES} attempts")
        return False


"""
Telegram Sender Router - FastAPI endpoints for sending messages to Telegram.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from services.telegram.config import Config
from services.telegram.models import (
    SendMessagesRequest,
    SendMessagesResponse,
    SendMessageResult,
    StartTypingRequest,
    StartTypingResponse,
    CancelTypingRequest,
    CancelTypingResponse,
)
from services.telegram.sender_service import SenderService
from services.telegram.typing_service import TypingService

from telethon import TelegramClient

logger = logging.getLogger(__name__)

# Router instance
telegram_sender_router = APIRouter(tags=["Telegram Sender"])

# Shared instances (initialized in lifespan)
_telegram_client: TelegramClient | None = None
_sender_service: SenderService | None = None

# Typing background tasks (keyed by str(chat_id))
_typing_tasks: dict[str, asyncio.Task] = {}


async def init_telegram_sender():
    """Initialize the Telegram client and sender service."""
    global _telegram_client, _sender_service
    
    # Create and start sender service
    _sender_service = SenderService()
    await _sender_service.start()
    
    # Create Telegram client
    _telegram_client = TelegramClient(
        Config.SESSION_NAME,
        Config.API_ID,
        Config.API_HASH
    )
    
    # Start the client (will use existing session if available)
    await _telegram_client.start()
    
    me = await _telegram_client.get_me()
    logger.info(f"Telegram sender initialized as: {me.first_name} (@{me.username or 'no username'})")


async def shutdown_telegram_sender():
    """Shutdown the Telegram client and sender service."""
    global _telegram_client, _sender_service, _typing_tasks

    # Cancel typing tasks first (their finally blocks send best-effort 'cancel')
    if _typing_tasks:
        tasks = list(_typing_tasks.values())
        _typing_tasks.clear()
        for t in tasks:
            if not t.done():
                t.cancel()
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass
    
    if _sender_service:
        await _sender_service.stop()
        _sender_service = None
    
    if _telegram_client:
        await _telegram_client.disconnect()
        _telegram_client = None
    
    logger.info("Telegram sender shutdown complete")


def get_telegram_client() -> TelegramClient:
    """Get the initialized Telegram client."""
    if _telegram_client is None:
        raise HTTPException(
            status_code=503,
            detail="Telegram client not initialized"
        )
    return _telegram_client


def get_sender_service() -> SenderService:
    """Get the initialized sender service."""
    if _sender_service is None:
        raise HTTPException(
            status_code=503,
            detail="Sender service not initialized"
        )
    return _sender_service


@telegram_sender_router.post(
    "/send",
    response_model=SendMessagesResponse,
    summary="Send multiple messages with images",
    description="Send a list of messages to Telegram chats with optional images"
)
async def send_messages(request: SendMessagesRequest) -> SendMessagesResponse:
    """
    Send multiple messages to Telegram chats.
    
    Each message can have:
    - **chat_id**: Target chat ID to send the message to
    - **image_urls**: Optional list of image URLs (sent as album if multiple)
    - **caption**: Optional caption text
    """
    client = get_telegram_client()
    sender = get_sender_service()
    
    results = []
    successful = 0
    failed = 0
    
    for msg in request.messages:
        # Validate that at least images or caption is provided
        has_images = msg.image_urls and len(msg.image_urls) > 0
        if not has_images and not msg.caption:
            results.append(SendMessageResult(
                success=False,
                message_ids=[],
                chat_id=msg.chat_id,
                error="At least 'image_urls' or 'caption' must be provided"
            ))
            failed += 1
            continue
        
        result = await sender.send_message(
            client=client,
            chat_id=msg.chat_id,
            image_urls=msg.image_urls,
            caption=msg.caption
        )
        
        results.append(SendMessageResult(**result))
        
        if result["success"]:
            successful += 1
        else:
            failed += 1
    
    return SendMessagesResponse(
        total=len(request.messages),
        successful=successful,
        failed=failed,
        results=results
    )


@telegram_sender_router.post(
    "/typing/start",
    response_model=StartTypingResponse,
    summary="Start typing indicator for a duration",
    description="Set chat to typing mode for duration_seconds (returns immediately; runs in background)",
)
async def start_typing(request: StartTypingRequest) -> StartTypingResponse:
    client = get_telegram_client()
    try:
        await TypingService.start_typing(
            client=client,
            chat_id=request.chat_id,
            duration_seconds=request.duration_seconds,
            registry=_typing_tasks,
        )
        return StartTypingResponse(
            success=True,
            chat_id=request.chat_id,
            duration_seconds=request.duration_seconds,
            error=None,
        )
    except Exception as e:
        logger.error(f"Failed to start typing for chat {request.chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@telegram_sender_router.post(
    "/typing/cancel",
    response_model=CancelTypingResponse,
    summary="Cancel typing indicator immediately",
    description="Cancel typing mode immediately and stop any background typing task for that chat",
)
async def cancel_typing(request: CancelTypingRequest) -> CancelTypingResponse:
    client = get_telegram_client()
    try:
        cancelled_task = await TypingService.cancel_typing(
            client=client,
            chat_id=request.chat_id,
            registry=_typing_tasks,
        )
        return CancelTypingResponse(
            success=True,
            chat_id=request.chat_id,
            cancelled_task=cancelled_task,
            error=None,
        )
    except Exception as e:
        logger.error(f"Failed to cancel typing for chat {request.chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

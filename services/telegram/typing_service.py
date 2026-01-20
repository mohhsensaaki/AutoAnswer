"""
Typing Service - Handles Telegram typing indicators (start for duration / cancel).

This uses Telethon's MTProto chat actions:
    - client.action(chat_id, 'typing') to show typing
    - client.action(chat_id, 'cancel') to cancel immediately
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from telethon import TelegramClient

logger = logging.getLogger(__name__)


class TypingService:
    """Service for managing per-chat typing background tasks."""

    @staticmethod
    async def start_typing(
        *,
        client: TelegramClient,
        chat_id: int | str,
        duration_seconds: int,
        registry: dict[str, asyncio.Task],
    ) -> None:
        """
        Start typing indicator in a chat for a duration (background task).

        Overlap policy: reset — if a task exists for the same chat_id, cancel it first.
        """
        chat_key = str(chat_id)

        existing = registry.get(chat_key)
        if existing and not existing.done():
            existing.cancel()

        task = asyncio.create_task(
            TypingService._typing_task(
                client=client,
                chat_id=chat_id,
                duration_seconds=duration_seconds,
                registry=registry,
            ),
            name=f"telegram-typing:{chat_key}",
        )
        registry[chat_key] = task

    @staticmethod
    async def cancel_typing(
        *,
        client: TelegramClient,
        chat_id: int | str,
        registry: dict[str, asyncio.Task],
    ) -> bool:
        """
        Cancel typing indicator immediately.

        Returns True if there was a registry task that was cancelled.
        """
        chat_key = str(chat_id)
        cancelled_task = False

        existing = registry.get(chat_key)
        if existing and not existing.done():
            existing.cancel()
            cancelled_task = True

        # Send immediate cancel to Telegram (best-effort).
        try:
            await client.action(chat_id, "cancel")
        except Exception as e:
            logger.warning(f"Failed to send typing cancel for chat {chat_id}: {e}")

        return cancelled_task

    @staticmethod
    async def _typing_task(
        *,
        client: TelegramClient,
        chat_id: int | str,
        duration_seconds: int,
        registry: dict[str, asyncio.Task],
    ) -> None:
        chat_key = str(chat_id)
        current_task = asyncio.current_task()
        try:
            async with client.action(chat_id, "typing"):
                await asyncio.sleep(duration_seconds)
        except asyncio.CancelledError:
            # Reset policy cancels prior task; we still attempt to cancel the typing indicator.
            raise
        except Exception as e:
            logger.warning(f"Typing task error for chat {chat_id}: {e}")
        finally:
            # Best-effort cancellation to avoid lingering indicator.
            try:
                await client.action(chat_id, "cancel")
            except Exception:
                pass

            # Cleanup registry only if it still points to this task.
            try:
                if registry.get(chat_key) is current_task:
                    registry.pop(chat_key, None)
            except Exception:
                # Defensive: registry might be mutated concurrently.
                pass

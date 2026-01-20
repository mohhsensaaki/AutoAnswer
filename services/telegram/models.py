"""
Pydantic models for Telegram sender service.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SendMessageItem(BaseModel):
    """Model for a single message to send."""
    
    chat_id: int | str = Field(..., description="Target chat ID (int) or username (str like '@username')")
    image_urls: Optional[list[str]] = Field(
        None, 
        description="List of image URLs to send (will be sent as album if multiple)"
    )
    caption: Optional[str] = Field(None, description="Caption text for the image/message")


class SendMessagesRequest(BaseModel):
    """Request model for sending multiple messages."""
    
    messages: list[SendMessageItem] = Field(
        ..., 
        description="List of messages to send",
        min_length=1
    )


class SendMessageResult(BaseModel):
    """Result for a single sent message."""
    
    success: bool = Field(..., description="Whether the message was sent successfully")
    message_ids: list[int] = Field(default_factory=list, description="IDs of the sent messages")
    chat_id: int | str = Field(..., description="Chat ID or username the message was sent to")
    error: Optional[str] = Field(None, description="Error message if failed")


class SendMessagesResponse(BaseModel):
    """Response model for send messages endpoint."""
    
    total: int = Field(..., description="Total number of messages processed")
    successful: int = Field(..., description="Number of messages sent successfully")
    failed: int = Field(..., description="Number of messages that failed")
    results: list[SendMessageResult] = Field(..., description="Results for each message")


class StartTypingRequest(BaseModel):
    """Request model for starting typing indicator in a chat."""

    chat_id: int | str = Field(..., description="Target chat ID (int) or username (str like '@username')")
    duration_seconds: int = Field(
        ...,
        description="How long to keep the chat in typing mode (seconds)",
        gt=0,
        le=3600,
    )


class StartTypingResponse(BaseModel):
    """Response model for start typing endpoint."""

    success: bool = Field(..., description="Whether typing was started successfully")
    chat_id: int | str = Field(..., description="Chat ID or username")
    duration_seconds: int = Field(..., description="Typing duration that was scheduled (seconds)")
    error: Optional[str] = Field(None, description="Error message if failed")


class CancelTypingRequest(BaseModel):
    """Request model for cancelling typing indicator in a chat."""

    chat_id: int | str = Field(..., description="Target chat ID (int) or username (str like '@username')")


class CancelTypingResponse(BaseModel):
    """Response model for cancel typing endpoint."""

    success: bool = Field(..., description="Whether typing was cancelled successfully")
    chat_id: int | str = Field(..., description="Chat ID or username")
    cancelled_task: bool = Field(..., description="Whether an in-memory typing task was cancelled")
    error: Optional[str] = Field(None, description="Error message if failed")

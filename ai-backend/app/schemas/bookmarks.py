from datetime import datetime

from pydantic import BaseModel


class MessageBookmarkOut(BaseModel):
    message_index: int
    bookmarked: bool


class BookmarkedMessageOut(BaseModel):
    message_id: int
    conversation_id: int
    conversation_title: str
    message_index: int
    role: str
    content: str
    created_at: datetime

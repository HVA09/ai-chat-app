"""
مسارات إدارة محادثات المستخدم الحالي: عرض، تعديل الاسم، حذف، وتصدير
"""
from datetime import datetime, timezone
import json
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, over
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import enforce_daily_ai_limit, get_current_user
from app.models.assistant import Assistant
from app.models.conversation import Conversation, Message
from app.models.conversation_folder import ConversationFolder
from app.models.conversation_tag import ConversationTag
from app.models.user import User
from app.models.usage_log import UsageLog
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.bookmarks import BookmarkedMessageOut
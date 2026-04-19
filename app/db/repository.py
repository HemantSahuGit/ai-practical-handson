from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessage, ChatSession


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, title: str | None = None) -> ChatSession:
        row = ChatSession(title=title)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None:
        return await self._session.get(ChatSession, session_id)

    async def append_message(
        self, session_id: uuid.UUID, role: str, content: str
    ) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_messages_for_llm(
        self, session_id: uuid.UUID, limit: int
    ) -> Sequence[ChatMessage]:
        """Last `limit` messages in chronological order (oldest first within the window)."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def list_messages_chronological(
        self, session_id: uuid.UUID
    ) -> Sequence[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

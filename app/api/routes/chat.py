from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.repository import ChatRepository
from app.deps import get_db_session
from app.services.agent import AgentService
from app.services.chroma_schema import ChromaSchemaStore

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: uuid.UUID | None = None
    message: str = Field(..., min_length=1, max_length=16_000)


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    reply: str
    debug: dict | None = None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str


class SessionMessagesResponse(BaseModel):
    session_id: uuid.UUID
    messages: list[MessageOut]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    repo = ChatRepository(db)
    session_id = body.session_id
    if session_id is None:
        session_row = await repo.create_session()
        session_id = session_row.id
    else:
        existing = await repo.get_session(session_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Unknown session_id")

    await repo.append_message(session_id, "user", body.message)

    chroma = ChromaSchemaStore(settings)
    agent = AgentService(settings, db, chroma)
    result = await agent.run_turn(session_id)
    await repo.append_message(session_id, "assistant", result.reply)
    await db.commit()

    return ChatResponse(
        session_id=session_id,
        reply=result.reply,
        debug=result.debug if settings.include_debug_in_response else None,
    )


@router.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
async def list_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> SessionMessagesResponse:
    repo = ChatRepository(db)
    session = await repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    rows = await repo.list_messages_chronological(session_id)
    return SessionMessagesResponse(
        session_id=session_id,
        messages=[
            MessageOut(id=r.id, role=r.role, content=r.content) for r in rows
        ],
    )

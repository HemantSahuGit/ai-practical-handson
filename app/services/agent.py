from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.repository import ChatRepository
from app.db.session import get_engine
from app.services.chroma_schema import ChromaSchemaStore
from app.services.postgres_query import run_readonly_query
from app.services.sql_guard import validate_readonly_select


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "answer_from_context",
            "description": (
                "Answer using schema documentation and prior conversation only. "
                "Use when the user asks for definitions, grain, relationships, or "
                "how to interpret tables without needing row-level aggregates from the database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Complete markdown or plain-text answer for the user.",
                    }
                },
                "required": ["answer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_readonly_sql",
            "description": (
                "Run a single read-only SELECT against PostgreSQL to fetch facts, "
                "aggregates, or row samples. Only use tables/columns you know exist "
                "from the provided schema context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "One SELECT statement only; no semicolon-separated batches.",
                    }
                },
                "required": ["sql"],
            },
        },
    },
]


@dataclass
class AgentResult:
    reply: str
    debug: dict[str, Any] = field(default_factory=dict)


class AgentService:
    def __init__(
        self,
        settings: Settings,
        db_session: AsyncSession,
        chroma: ChromaSchemaStore,
    ) -> None:
        self._settings = settings
        self._repo = ChatRepository(db_session)
        self._chroma = chroma
        self._client = AsyncOpenAI(api_key=settings.openai_api_key or None)
        self._engine = get_engine(settings)

    async def run_turn(self, session_id: uuid.UUID) -> AgentResult:
        debug: dict[str, Any] = {
            "retrieved_schema_ids": [],
            "tool_rounds": 0,
            "routes": [],
        }

        history_rows = await self._repo.get_messages_for_llm(
            session_id, self._settings.chat_history_limit
        )
        history: list[ChatCompletionMessageParam] = []
        for row in history_rows:
            if row.role not in ("user", "assistant", "system"):
                continue
            history.append({"role": row.role, "content": row.content})

        last_user = ""
        for row in reversed(history_rows):
            if row.role == "user":
                last_user = row.content
                break
        if not last_user.strip():
            last_user = " "

        chroma_out = self._chroma.query_similar(
            last_user, self._settings.schema_retrieval_k
        )
        retrieved_ids: list[str] = []
        retrieved_docs: list[str] = []
        raw_ids = chroma_out.get("ids") or []
        raw_docs = chroma_out.get("documents") or []
        if raw_ids and raw_ids[0]:
            retrieved_ids = list(raw_ids[0])
        if raw_docs and raw_docs[0]:
            retrieved_docs = list(raw_docs[0])
        debug["retrieved_schema_ids"] = retrieved_ids

        schema_context = "\n\n".join(
            f"[{rid}]\n{doc}" for rid, doc in zip(retrieved_ids, retrieved_docs)
        )
        if not schema_context.strip():
            schema_context = "(No schema chunks retrieved. Ask clarifying questions.)"

        system_prompt = (
            "You are a data warehouse assistant. You help users understand schema "
            "documentation and query analytical data in PostgreSQL.\n\n"
            "Rules:\n"
            "- Prefer `answer_from_context` when the user only needs explanations, "
            "definitions, or how to use tables.\n"
            "- Use `run_readonly_sql` when numeric results, row samples, or aggregates "
            "from the database are required.\n"
            "- Never invent table or column names; only use names present in the schema context.\n"
            "- SQL must be a single SELECT.\n"
            "- After SQL results are returned, synthesize a concise answer for the user. "
            "You may call tools multiple times in one turn if needed.\n\n"
            f"Retrieved schema context:\n{schema_context}"
        )

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        final_text: str | None = None
        rounds = 0

        while rounds < self._settings.agent_max_tool_rounds:
            rounds += 1
            debug["tool_rounds"] = rounds

            completion = await self._client.chat.completions.create(
                model=self._settings.openai_chat_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            choice = completion.choices[0]
            msg = choice.message

            if msg.tool_calls:
                assistant_payload: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
                messages.append(assistant_payload)  # type: ignore[arg-type]

                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        tool_content = json.dumps({"error": "Invalid JSON arguments"})
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_content,
                            }
                        )
                        continue

                    if name == "answer_from_context":
                        answer = str(args.get("answer", "")).strip()
                        debug["routes"].append("answer_from_context")
                        if answer:
                            final_text = answer
                        tool_content = json.dumps({"status": "answer_recorded"})
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_content,
                            }
                        )
                        continue

                    if name == "run_readonly_sql":
                        sql = str(args.get("sql", "")).strip()
                        debug["routes"].append("run_readonly_sql")
                        try:
                            safe_sql = validate_readonly_select(sql)
                            rows = await run_readonly_query(self._engine, safe_sql)
                            payload = {"rows": rows, "row_count": len(rows)}
                            tool_content = json.dumps(payload, default=str)[:120_000]
                        except Exception as exc:  # noqa: BLE001 — surface to model
                            tool_content = json.dumps({"error": str(exc)})
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": tool_content,
                            }
                        )
                        continue

                    tool_content = json.dumps({"error": f"Unknown tool {name}"})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_content,
                        }
                    )

                if final_text and not any(
                    tc.function.name == "run_readonly_sql" for tc in msg.tool_calls
                ):
                    break

                continue

            if msg.content and msg.content.strip():
                final_text = msg.content.strip()
                break

            break

        if not final_text:
            final_text = (
                "I could not produce a final answer. "
                "Try rephrasing or check that the API key and database are configured."
            )

        if not self._settings.include_debug_in_response:
            debug = {}

        return AgentResult(reply=final_text, debug=debug)

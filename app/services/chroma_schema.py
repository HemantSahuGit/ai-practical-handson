from __future__ import annotations

import os
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import Settings


class ChromaSchemaStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        os.makedirs(settings.chroma_path, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key or None,
            model_name=settings.openai_embed_model,
        )
        self._collection: Collection = self._client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=ef,
            metadata={"description": "Warehouse / BI schema documentation chunks"},
        )

    def upsert_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def query_similar(self, query: str, k: int) -> dict[str, Any]:
        return self._collection.query(query_texts=[query], n_results=k)

    @property
    def collection(self) -> Collection:
        return self._collection

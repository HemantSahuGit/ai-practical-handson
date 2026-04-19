"""Load example schema documentation into Chroma (OpenAI embeddings)."""

from __future__ import annotations

import os
import sys

# Ensure project root is on path when running as `uv run python scripts/seed_chroma.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.chroma_schema import ChromaSchemaStore


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is required to compute embeddings for Chroma.")

    store = ChromaSchemaStore(settings)

    docs = [
        {
            "id": "sales_fact_overview",
            "text": (
                "Table `public.sales_fact` is the primary sales fact table. "
                "Grain: one row per line item sale. "
                "Columns: `id` (surrogate key), `sale_date` (calendar date of sale), "
                "`product_name` (sold product label), `region` (sales region), "
                "`amount` (sale currency amount, numeric)."
            ),
            "metadata": {"table": "sales_fact", "kind": "overview"},
        },
        {
            "id": "sales_fact_region",
            "text": (
                "The `region` column in `public.sales_fact` groups sales into broad "
                "geographies such as North, South, and West for reporting."
            ),
            "metadata": {"table": "sales_fact", "kind": "column_doc"},
        },
        {
            "id": "sales_fact_amount",
            "text": (
                "`amount` on `public.sales_fact` stores the monetary value of each sale "
                "in base currency; use SUM(amount) for revenue-style aggregates."
            ),
            "metadata": {"table": "sales_fact", "kind": "column_doc"},
        },
    ]

    store.upsert_documents(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[d["metadata"] for d in docs],
    )
    print(f"Upserted {len(docs)} documents into collection '{settings.chroma_collection}'.")


if __name__ == "__main__":
    main()

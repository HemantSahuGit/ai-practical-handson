"""Lightweight checks for agent-generated SQL. Prefer a read-only DB role in production."""

from __future__ import annotations

import re

import sqlparse


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|create|alter|truncate|grant|revoke|copy|"
    r"call|execute|do|merge|replace)\b",
    re.IGNORECASE,
)


def validate_readonly_select(sql: str) -> str:
    raw = sql.strip()
    if not raw:
        raise ValueError("Empty SQL")
    # Single statement only (allow trailing semicolon)
    without_trailing = raw.rstrip().rstrip(";").strip()
    statements = [s for s in sqlparse.split(without_trailing) if s.strip()]
    if len(statements) != 1:
        raise ValueError("Exactly one SQL statement is required")
    stmt_text = statements[0].strip()
    parsed_list = sqlparse.parse(stmt_text)
    if len(parsed_list) != 1:
        raise ValueError("Could not parse SQL as a single statement")
    head = stmt_text.lstrip().split()
    if not head:
        raise ValueError("Only SELECT queries are allowed")
    first_word = head[0].strip().strip(";").lower()
    if first_word not in ("select", "with"):
        raise ValueError("Only SELECT (or WITH ... SELECT) queries are allowed")
    if _FORBIDDEN.search(stmt_text):
        raise ValueError("Query contains forbidden keywords")
    if ";" in stmt_text.rstrip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed")
    return stmt_text

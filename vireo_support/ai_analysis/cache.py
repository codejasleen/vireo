from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ResultCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_results (
                cache_key TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                task TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                parsed_json TEXT,
                usage_json TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT raw_content, parsed_json, usage_json, error FROM ai_results WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        if not row:
            return None
        return {
            "raw_content": row[0],
            "parsed": json.loads(row[1]) if row[1] else None,
            "usage": json.loads(row[2]),
            "error": row[3],
        }

    def put(
        self, cache_key: str, provider: str, model: str, task: str, raw_content: str,
        parsed: dict[str, Any] | None, usage: dict[str, Any], error: str | None,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO ai_results
            (cache_key, provider, model, task, raw_content, parsed_json, usage_json, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (cache_key, provider, model, task, raw_content, json.dumps(parsed) if parsed is not None else None, json.dumps(usage), error),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ResultCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

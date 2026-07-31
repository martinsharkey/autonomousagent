#!/usr/bin/env python3
"""Semantic request deduplication and caching for LLM calls.

Stores responses in a local SQLite cache with TTL and similarity matching.
Reduces redundant API calls and cost.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from difflib import SequenceMatcher

CACHE_DB = Path(__file__).parent.parent / 'data' / 'request_cache.db'
DEFAULT_TTL = 3600  # 1 hour
SIMILARITY_THRESHOLD = 0.95

class RequestCache:
    def __init__(self, db_path: str = str(CACHE_DB), ttl: int = DEFAULT_TTL):
        self.db_path = db_path
        self.ttl = ttl
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    prompt TEXT,
                    model TEXT,
                    params TEXT,
                    response TEXT,
                    created_at REAL
                )
            ''')
            conn.commit()

    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize whitespace and lower-case for better matching."""
        return ' '.join(prompt.split()).lower()

    def _hash_key(self, prompt: str, model: str, params: dict) -> str:
        normalized = self._normalize_prompt(prompt)
        payload = json.dumps({'prompt': normalized, 'model': model, 'params': params}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, prompt: str, model: str, params: dict = None) -> str | None:
        """Return cached response if exact or similar match exists and not expired."""
        params = params or {}
        key = self._hash_key(prompt, model, params)
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            # Exact match
            row = conn.execute(
                'SELECT response, created_at FROM cache WHERE key = ?', (key,)
            ).fetchone()
            if row and (now - row[1]) < self.ttl:
                return row[0]

            # Semantic similarity scan (limit to recent entries for performance)
            rows = conn.execute(
                'SELECT prompt, response, created_at FROM cache WHERE model = ? AND created_at > ?',
                (model, now - self.ttl)
            ).fetchall()
            normalized_target = self._normalize_prompt(prompt)
            for cached_prompt, response, created_at in rows:
                similarity = SequenceMatcher(None, normalized_target, self._normalize_prompt(cached_prompt)).ratio()
                if similarity >= SIMILARITY_THRESHOLD:
                    return response
        return None

    def set(self, prompt: str, model: str, params: dict, response: str):
        """Store a response in the cache."""
        params = params or {}
        key = self._hash_key(prompt, model, params)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO cache (key, prompt, model, params, response, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (key, self._normalize_prompt(prompt), model, json.dumps(params), response, time.time())
            )
            conn.commit()

    def clear_expired(self):
        """Remove entries older than TTL."""
        cutoff = time.time() - self.ttl
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM cache WHERE created_at < ?', (cutoff,))
            conn.commit()

# Singleton for easy import
_cache = None
def get_cache() -> RequestCache:
    global _cache
    if _cache is None:
        _cache = RequestCache()
    return _cache

"""
SQLite-based time-series storage for Instagram reel metrics.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .instaloader_scraper import ReelMetrics

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reel_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shortcode TEXT NOT NULL,
    url TEXT NOT NULL,
    label TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    source TEXT NOT NULL,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    saves INTEGER,
    reach INTEGER,
    engagement_rate REAL,
    caption TEXT,
    hashtags TEXT,
    error TEXT
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_shortcode_collected
ON reel_metrics (shortcode, collected_at);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize the SQLite database and return a connection."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_TABLE_SQL)
    conn.execute(CREATE_INDEX_SQL)
    conn.commit()
    return conn


def save_metrics(conn: sqlite3.Connection, metrics: ReelMetrics) -> int:
    """Insert a ReelMetrics record and return the new row id."""
    cursor = conn.execute(
        """
        INSERT INTO reel_metrics
            (shortcode, url, label, collected_at, source,
             views, likes, comments, shares, saves, reach,
             engagement_rate, caption, hashtags, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            metrics.shortcode,
            metrics.url,
            metrics.label,
            metrics.collected_at,
            metrics.source,
            metrics.views,
            metrics.likes,
            metrics.comments,
            metrics.shares,
            metrics.saves,
            metrics.reach,
            metrics.engagement_rate,
            metrics.caption,
            json.dumps(metrics.hashtags) if metrics.hashtags else "[]",
            metrics.error,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_metrics_batch(conn: sqlite3.Connection, metrics_list: list[ReelMetrics]) -> list[int]:
    """Save multiple metrics records."""
    ids = []
    for m in metrics_list:
        ids.append(save_metrics(conn, m))
    return ids


def get_latest_metrics(conn: sqlite3.Connection) -> list[dict]:
    """Get the most recent metrics for each reel."""
    rows = conn.execute(
        """
        SELECT * FROM reel_metrics
        WHERE id IN (
            SELECT MAX(id) FROM reel_metrics
            WHERE error IS NULL
            GROUP BY shortcode
        )
        ORDER BY label
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_metrics_history(
    conn: sqlite3.Connection,
    shortcode: str,
    days: int = 30,
) -> list[dict]:
    """Get time-series metrics for a specific reel."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT * FROM reel_metrics
        WHERE shortcode = ?
          AND collected_at >= ?
          AND error IS NULL
        ORDER BY collected_at ASC
        """,
        (shortcode, since),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_metrics_history(conn: sqlite3.Connection, days: int = 30) -> dict[str, list[dict]]:
    """Get time-series data for all reels, grouped by shortcode."""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT * FROM reel_metrics
        WHERE collected_at >= ?
          AND error IS NULL
        ORDER BY shortcode, collected_at ASC
        """,
        (since,),
    ).fetchall()

    history: dict[str, list[dict]] = {}
    for row in rows:
        d = dict(row)
        sc = d["shortcode"]
        if sc not in history:
            history[sc] = []
        history[sc].append(d)
    return history


def get_previous_metrics(
    conn: sqlite3.Connection,
    shortcode: str,
    before_id: int,
) -> Optional[dict]:
    """Get the most recent successful metric record before a given id."""
    row = conn.execute(
        """
        SELECT * FROM reel_metrics
        WHERE shortcode = ?
          AND id < ?
          AND error IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (shortcode, before_id),
    ).fetchone()
    return dict(row) if row else None

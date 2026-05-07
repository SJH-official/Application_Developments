import sqlite3
from contextlib import contextmanager
from typing import Optional

DB_PATH = "quotes.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                text      TEXT    NOT NULL,
                author    TEXT    NOT NULL,
                tags      TEXT    NOT NULL DEFAULT '',
                source    TEXT    NOT NULL DEFAULT 'quotes.toscrape.com',
                created_at DATETIME DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_quote(text: str, author: str, tags: str = "", source: str = "manual") -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO quotes (text, author, tags, source) VALUES (?, ?, ?, ?)",
            (text.strip(), author.strip(), tags.strip(), source)
        )
        conn.commit()
        return get_quote(cur.lastrowid)


def get_quote(quote_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
        return dict(row) if row else None


def get_all_quotes(
    skip: int = 0,
    limit: int = 100,
    author: Optional[str] = None,
    tag: Optional[str] = None,
    keyword: Optional[str] = None,
) -> list[dict]:
    query = "SELECT * FROM quotes WHERE 1=1"
    params: list = []

    if author:
        query += " AND author LIKE ?"
        params.append(f"%{author}%")
    if tag:
        query += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    if keyword:
        query += " AND text LIKE ?"
        params.append(f"%{keyword}%")

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params += [limit, skip]

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_quote(quote_id: int, text: Optional[str] = None,
                 author: Optional[str] = None, tags: Optional[str] = None) -> Optional[dict]:
    fields, params = [], []
    if text is not None:
        fields.append("text = ?"); params.append(text.strip())
    if author is not None:
        fields.append("author = ?"); params.append(author.strip())
    if tags is not None:
        fields.append("tags = ?"); params.append(tags.strip())
    if not fields:
        return get_quote(quote_id)

    params.append(quote_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE quotes SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    return get_quote(quote_id)


def delete_quote(quote_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        conn.commit()
        return cur.rowcount > 0


def get_stats() -> dict:
    with get_conn() as conn:
        total       = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        authors     = conn.execute("SELECT COUNT(DISTINCT author) FROM quotes").fetchone()[0]
        top_authors = conn.execute(
            "SELECT author, COUNT(*) as cnt FROM quotes GROUP BY author ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        all_tags = conn.execute("SELECT tags FROM quotes WHERE tags != ''").fetchall()

    tag_freq: dict[str, int] = {}
    for row in all_tags:
        for t in row[0].split(","):
            t = t.strip()
            if t:
                tag_freq[t] = tag_freq.get(t, 0) + 1
    top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_quotes": total,
        "unique_authors": authors,
        "top_authors": [{"author": r[0], "count": r[1]} for r in top_authors],
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
    }
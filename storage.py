"""SQLite storage with transactional updates and exact cosine search."""
import json
import math
import sqlite3


def split_text(text, size=900, overlap=120):
    if not 0 <= overlap < size:
        raise ValueError('Overlap must be smaller than chunk size.')
    text = ' '.join(text.replace('\x00', ' ').split())
    result = []
    start = 0
    while start < len(text):
        result.append(text[start:start + size])
        if start + size >= len(text):
            break
        start += size - overlap
    return result


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS sources (
            source TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
            embedding_id TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY, source TEXT NOT NULL,
            location TEXT NOT NULL, text TEXT NOT NULL, vector TEXT NOT NULL,
            FOREIGN KEY(source) REFERENCES sources(source) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY, session TEXT NOT NULL,
            question TEXT NOT NULL, answer TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    return db


def replace_source(db, source, fingerprint, embedding_id, pieces, vectors):
    if not pieces or len(pieces) != len(vectors):
        raise ValueError('Missing or inconsistent chunks/embeddings.')
    dimensions = len(vectors[0])
    if not dimensions or any(len(v) != dimensions or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Invalid embedding dimensions or values.')
    with db:
        db.execute('DELETE FROM sources WHERE source=?', (source,))
        db.execute('INSERT INTO sources VALUES (?,?,?)', (source, fingerprint, embedding_id))
        db.executemany('INSERT INTO chunks(source,location,text,vector) VALUES (?,?,?,?)',
                       [(source, location, text, json.dumps(vector))
                        for (location, text), vector in zip(pieces, vectors)])


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError('Embedding dimensions changed. Re-index all sources.')
    scale = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / scale if scale else 0.0


def search(db, vector, embedding_id, top_k=4, source_filter=None):
    rows = db.execute('SELECT chunks.* FROM chunks JOIN sources USING(source) '
                      'WHERE embedding_id=?', (embedding_id,))
    # Small personal collections only: linear scan, keeping just the best k rows.
    import heapq
    scored = ((cosine(vector, json.loads(r['vector'])), r['id'], dict(r)) for r in rows
              if source_filter is None or source_filter.casefold() in r['source'].casefold())
    return [dict(row, score=score) for score, _, row in heapq.nlargest(top_k, scored)]


def history(db, session, limit=2):
    rows = db.execute('SELECT question,answer FROM turns WHERE session=? '
                      'ORDER BY id DESC LIMIT ?', (session, limit)).fetchall()
    return [dict(row) for row in reversed(rows)]

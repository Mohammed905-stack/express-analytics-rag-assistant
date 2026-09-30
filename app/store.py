"""SQLite is durable storage; FAISS provides exact cosine-similarity retrieval."""
import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import faiss
import numpy as np


def normalized(values, dimensions):
    matrix = np.asarray(values, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != dimensions or not np.isfinite(matrix).all():
        raise ValueError('Embeddings must be finite vectors with the configured dimensions')
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or (norms <= 0).any():
        raise ValueError('Embeddings must have finite, nonzero magnitude')
    return np.ascontiguousarray(matrix / norms, dtype=np.float32)


class Store:
    def __init__(self, path: Path, dimensions: int, embedding_model: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
                digest TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
                text TEXT NOT NULL, vector BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS queries (
                id TEXT PRIMARY KEY, question TEXT NOT NULL, response TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY, query_id TEXT NOT NULL REFERENCES queries(id),
                rating TEXT NOT NULL CHECK(rating IN ('up','down')), comment TEXT,
                created_at TEXT NOT NULL);
        ''')
        config = json.dumps({'dimensions':dimensions, 'model':embedding_model}, sort_keys=True)
        old = self.db.execute("SELECT value FROM metadata WHERE key='embedding_config'").fetchone()
        if old and old['value'] != config:
            self.db.close()
            raise ValueError('Saved embeddings use a different model/dimension. Choose a new DATA_DIR and re-index.')
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('embedding_config', ?)", (config,))
        self.db.commit()
        self._rebuild()

    def _rebuild(self):
        self.rows = [dict(row) for row in self.db.execute('''
            SELECT c.id AS chunk_id, c.document_id, c.text, c.vector, d.title, d.source
            FROM chunks c JOIN documents d ON d.id=c.document_id ORDER BY c.rowid
        ''')]
        self.index = faiss.IndexFlatIP(self.dimensions)
        if self.rows:
            vectors = [np.frombuffer(row['vector'], dtype=np.float32).tolist() for row in self.rows]
            self.index.add(normalized(vectors, self.dimensions))

    @staticmethod
    def digest(text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def existing(self, digest):
        with self.lock:
            row = self.db.execute('SELECT id FROM documents WHERE digest=?', (digest,)).fetchone()
            return row['id'] if row else None

    def documents(self):
        with self.lock:
            return [dict(row) for row in self.db.execute('''
                SELECT d.id AS document_id, d.title, d.source, d.created_at, COUNT(c.id) AS chunks
                FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                GROUP BY d.id ORDER BY d.created_at
            ''')]

    def add(self, title, source, digest, chunks, vectors):
        if not chunks or len(chunks) != len(vectors):
            raise ValueError('Each nonempty chunk needs one embedding')
        matrix = normalized(vectors, self.dimensions)
        with self.lock:
            prior = self.existing(digest)
            if prior:
                return {'document_id':prior, 'chunks_added':0, 'duplicate':True}
            document_id = uuid4().hex
            with self.db:
                self.db.execute('INSERT INTO documents VALUES (?,?,?,?,?)',
                    (document_id,title,source,digest,datetime.now(timezone.utc).isoformat()))
                self.db.executemany('INSERT INTO chunks VALUES (?,?,?,?)',
                    [(f'{document_id}-{i}',document_id,text,matrix[i].tobytes()) for i,text in enumerate(chunks)])
            self._rebuild()
            return {'document_id':document_id, 'chunks_added':len(chunks), 'duplicate':False}

    def search(self, vector, top_k):
        query = normalized([vector], self.dimensions)
        with self.lock:
            if not self.rows:
                return []
            scores, indices = self.index.search(query, min(top_k,len(self.rows)))
            return [{key:value for key,value in self.rows[int(i)].items() if key != 'vector'} |
                    {'score':float(score)} for score,i in zip(scores[0],indices[0]) if i >= 0]

    def save_query(self, question, response):
        with self.lock, self.db:
            self.db.execute('INSERT INTO queries VALUES (?,?,?)',
                (response['query_id'],question,json.dumps(response)))

    def feedback(self, query_id, rating, comment):
        with self.lock, self.db:
            if not self.db.execute('SELECT 1 FROM queries WHERE id=?', (query_id,)).fetchone():
                raise KeyError(query_id)
            feedback_id = uuid4().hex
            self.db.execute('INSERT INTO feedback VALUES (?,?,?,?,?)',
                (feedback_id,query_id,rating,comment,datetime.now(timezone.utc).isoformat()))
            return feedback_id

    def close(self):
        with self.lock:
            self.db.close()

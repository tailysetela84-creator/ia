"""
database.py
===========
Camada de acesso a dados (SQLite).

Guarda:
  - `words`   -> palavras aprendidas (id, nome, criado_em)
  - `samples` -> cada gravação de exemplo de uma palavra, incluindo
                 o caminho do ficheiro .wav e o embedding (vetor ML)
                 já calculado, guardado como JSON para reutilização
                 rápida sem reprocessar o áudio sempre que a app arranca.

Este módulo não sabe nada sobre Machine Learning ou áudio: é só
persistência. Isto facilita testar e substituir a base de dados no futuro
(por exemplo, trocar SQLite por PostgreSQL) sem tocar no resto do código.
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "words.db")
DB_PATH = os.path.abspath(DB_PATH)


def init_db():
    """Cria as tabelas se ainda não existirem. Chamar uma vez no arranque."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                audio_path TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (word_id) REFERENCES words (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


@contextmanager
def get_connection():
    """Context manager que garante que a ligação é sempre fechada."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def add_word_if_missing(word_name: str) -> int:
    """Garante que a palavra existe na tabela `words` e devolve o seu id."""
    with get_connection() as conn:
        cur = conn.execute("SELECT id FROM words WHERE name = ?", (word_name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur = conn.execute(
            "INSERT INTO words (name, created_at) VALUES (?, ?)",
            (word_name, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def add_sample(word_name: str, audio_path: str, embedding) -> int:
    """
    Regista uma nova gravação (amostra) de uma palavra.
    `embedding` deve ser uma lista/array de floats (o vetor ML calculado
    a partir do áudio) — é serializado em JSON para ficar em texto na BD.
    """
    word_id = add_word_if_missing(word_name)
    embedding_json = json.dumps([float(x) for x in embedding])
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO samples (word_id, audio_path, embedding, created_at) "
            "VALUES (?, ?, ?, ?)",
            (word_id, audio_path, embedding_json, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def get_all_words():
    """Devolve lista de dicts: [{id, name, created_at, n_samples}, ...]"""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT w.id, w.name, w.created_at, COUNT(s.id) as n_samples
            FROM words w
            LEFT JOIN samples s ON s.word_id = w.id
            GROUP BY w.id
            ORDER BY w.name COLLATE NOCASE
        """)
        return [
            {"id": r[0], "name": r[1], "created_at": r[2], "n_samples": r[3]}
            for r in cur.fetchall()
        ]


def get_all_samples_with_embeddings():
    """
    Devolve todos os exemplos guardados, já com o embedding desserializado,
    agrupados por palavra. Formato:
        { "Makonde": [ [emb1...], [emb2...], ... ], "Ola": [...] }
    Usado pelo recognizer para (re)calcular os protótipos de cada palavra.
    """
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT w.name, s.embedding
            FROM samples s
            JOIN words w ON w.id = s.word_id
        """)
        result = {}
        for name, embedding_json in cur.fetchall():
            result.setdefault(name, []).append(json.loads(embedding_json))
        return result


def remove_word(word_name: str):
    """Remove a palavra e todas as suas amostras (áudios ficam em disco,
    o chamador é responsável por apagar os ficheiros se quiser)."""
    with get_connection() as conn:
        cur = conn.execute("SELECT audio_path FROM samples s "
                            "JOIN words w ON w.id = s.word_id WHERE w.name = ?",
                            (word_name,))
        audio_paths = [r[0] for r in cur.fetchall()]
        conn.execute("DELETE FROM words WHERE name = ?", (word_name,))
        conn.commit()
        return audio_paths

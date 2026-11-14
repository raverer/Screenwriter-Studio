"""Lightweight, project-scoped retrieval-augmented generation for Screenwriter Studio.

Documents and embeddings stay in the local SQLite database. Ollama supplies
embeddings through its /api/embed endpoint; similarity search is cosine-based.
"""
import hashlib
import json
import math
import os
import re
import sqlite3
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import requests

DEFAULT_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_CHUNKS_PER_DOCUMENT = 500


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _database_path(db_path=None):
    return Path(
        db_path
        or os.getenv("SCREENWRITER_DB_PATH")
        or Path(__file__).with_name("screenwriter_studio.db")
    )


def _connect(db_path=None):
    path = _database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_research_db(db_path=None):
    """Create project-scoped research tables without changing existing tables."""
    connection = _connect(db_path)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS research_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(project_id, file_hash),
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS research_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                page_number INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES research_documents(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_research_chunks_project
            ON research_chunks(project_id);

            CREATE INDEX IF NOT EXISTS idx_research_documents_project
            ON research_documents(project_id);
            """
        )
    finally:
        connection.close()


def extract_document_units(file_name, file_bytes):
    """Extract text into units carrying optional PDF page numbers."""
    if not isinstance(file_bytes, bytes) or not file_bytes:
        raise ValueError("The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Each research file must be 10 MB or smaller.")

    extension = Path(file_name).suffix.lower()
    units = []
    if extension in {".txt", ".md"}:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc
        units.append({"text": text, "page_number": None})
    elif extension == ".docx":
        try:
            from docx import Document
            document = Document(BytesIO(file_bytes))
            text = "\n".join(
                paragraph.text for paragraph in document.paragraphs
                if paragraph.text.strip()
            )
        except Exception as exc:
            raise ValueError(f"Could not read DOCX file: {exc}") from exc
        units.append({"text": text, "page_number": None})
    elif extension == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(file_bytes))
            for page_index, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    units.append({
                        "text": text,
                        "page_number": page_index + 1,
                    })
        except ImportError as exc:
            raise RuntimeError(
                "PDF reading requires pypdf. Install the project dependencies again."
            ) from exc
        except Exception as exc:
            raise ValueError(f"Could not read PDF file: {exc}") from exc
    else:
        raise ValueError("Supported research formats are PDF, DOCX, TXT and MD.")

    units = [unit for unit in units if unit["text"].strip()]
    if not units:
        raise ValueError("No readable text was found in this file.")
    return units


def chunk_text(text, chunk_words=220, overlap_words=40):
    """Split text into overlapping word windows, retaining the original wording."""
    if not isinstance(text, str):
        raise TypeError("Text to chunk must be a string.")
    if chunk_words < 1 or overlap_words < 0 or overlap_words >= chunk_words:
        raise ValueError("Chunk size must be positive and overlap smaller than chunk size.")
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks = []
    step = chunk_words - overlap_words
    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + chunk_words]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks


def chunk_document_units(units, chunk_words=220, overlap_words=40):
    chunks = []
    for unit in units:
        for text in chunk_text(unit["text"], chunk_words, overlap_words):
            chunks.append({
                "content": text,
                "page_number": unit.get("page_number"),
            })
            if len(chunks) > MAX_CHUNKS_PER_DOCUMENT:
                raise ValueError(
                    f"Document exceeds the {MAX_CHUNKS_PER_DOCUMENT}-chunk indexing limit."
                )
    return chunks


def embed_texts(texts, model=DEFAULT_EMBEDDING_MODEL,
                ollama_url="http://localhost:11434", timeout=240):
    """Generate embeddings in small batches using Ollama's current /api/embed API."""
    if not texts:
        return []
    if not isinstance(model, str) or not model.strip():
        raise ValueError("An Ollama embedding model name is required.")
    url = ollama_url.rstrip("/") + "/api/embed"
    results = []
    batch_size = 8
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        try:
            response = requests.post(
                url,
                json={"model": model, "input": batch},
                timeout=timeout,
            )
            response.raise_for_status()
            embeddings = response.json().get("embeddings")
        except requests.ConnectionError as exc:
            raise RuntimeError(
                "Cannot connect to Ollama for embeddings. Start Ollama and retry."
            ) from exc
        except requests.Timeout as exc:
            raise RuntimeError(
                "Ollama embedding request timed out. Try fewer or smaller files."
            ) from exc
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = response.json().get("error", "")
            except Exception:
                pass
            raise RuntimeError(
                f"Ollama embedding request failed: {detail or exc}. "
                f"Check that '{model}' is installed (ollama pull {model})."
            ) from exc
        if not isinstance(embeddings, list) or len(embeddings) != len(batch):
            raise RuntimeError("Ollama returned an unexpected embeddings response.")
        for vector in embeddings:
            if (
                not isinstance(vector, list) or not vector
                or not all(isinstance(value, (int, float)) for value in vector)
            ):
                raise RuntimeError("Ollama returned an invalid embedding vector.")
            results.append([float(value) for value in vector])
    return results


def index_document(project_id, file_name, file_bytes, embedding_model,
                   embedding_fn, db_path=None):
    """Extract, chunk, embed and persist one document for a single project."""
    if project_id is None:
        raise ValueError("Create or load a project before adding research.")
    if not callable(embedding_fn):
        raise TypeError("embedding_fn must be callable.")
    if not isinstance(file_name, str) or not file_name.strip():
        raise ValueError("A research file must have a name.")

    units = extract_document_units(file_name, file_bytes)
    chunks = chunk_document_units(units)
    if not chunks:
        raise ValueError("No text chunks were produced from this file.")
    document_texts = [item["content"] for item in chunks]
    if "nomic-embed-text" in embedding_model.lower():
        document_texts = ["search_document: " + text for text in document_texts]
    vectors = embedding_fn(document_texts, embedding_model)
    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match the document chunk count.")
    dimensions = {len(vector) for vector in vectors if isinstance(vector, list)}
    if len(dimensions) != 1 or len(vectors) != len(chunks):
        raise ValueError("Embedding vectors must have one consistent dimension.")

    digest = hashlib.sha256(file_bytes).hexdigest()
    now = _now()
    init_research_db(db_path)
    connection = _connect(db_path)
    try:
        existing = connection.execute(
            "SELECT id FROM research_documents WHERE project_id = ? AND file_hash = ?",
            (project_id, digest),
        ).fetchone()
        if existing:
            connection.execute(
                "DELETE FROM research_documents WHERE id = ?", (existing["id"],)
            )
        cursor = connection.execute(
            """
            INSERT INTO research_documents(
                project_id, file_name, file_hash, embedding_model, chunk_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, Path(file_name).name, digest, embedding_model, len(chunks), now),
        )
        document_id = int(cursor.lastrowid)
        connection.executemany(
            """
            INSERT INTO research_chunks(
                document_id, project_id, chunk_index, content,
                embedding_json, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    document_id, project_id, index, chunk["content"],
                    json.dumps(vector), chunk["page_number"], now
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors), start=1)
            ],
        )
        connection.commit()
        return {
            "document_id": document_id,
            "file_name": Path(file_name).name,
            "chunk_count": len(chunks),
            "embedding_model": embedding_model,
            "replaced_existing": existing is not None,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def list_research_documents(project_id, db_path=None):
    if project_id is None:
        return []
    init_research_db(db_path)
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT id, file_name, embedding_model, chunk_count, created_at
            FROM research_documents
            WHERE project_id = ?
            ORDER BY created_at DESC, file_name COLLATE NOCASE
            """,
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def delete_research_document(document_id, project_id, db_path=None):
    init_research_db(db_path)
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            "DELETE FROM research_documents WHERE id = ? AND project_id = ?",
            (document_id, project_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _cosine_similarity(left, right):
    if len(left) != len(right):
        return None
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def search_chunks(project_id, query_embedding, embedding_model, top_k=5, db_path=None):
    """Return the most similar project chunks indexed with the same embedding model."""
    if project_id is None:
        return []
    if not isinstance(query_embedding, list) or not query_embedding:
        raise ValueError("A non-empty query embedding is required.")
    if not 1 <= int(top_k) <= 20:
        raise ValueError("top_k must be between 1 and 20.")
    init_research_db(db_path)
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT c.id, c.chunk_index, c.content, c.embedding_json,
                   c.page_number, d.file_name, d.embedding_model
            FROM research_chunks AS c
            JOIN research_documents AS d ON d.id = c.document_id
            WHERE c.project_id = ? AND d.embedding_model = ?
            """,
            (project_id, embedding_model),
        ).fetchall()
        ranked = []
        for row in rows:
            vector = json.loads(row["embedding_json"])
            score = _cosine_similarity(query_embedding, vector)
            if score is None:
                continue
            ranked.append({
                "chunk_id": row["id"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "page_number": row["page_number"],
                "file_name": row["file_name"],
                "embedding_model": row["embedding_model"],
                "score": score,
            })
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:int(top_k)]
    finally:
        connection.close()


def retrieve_relevant_chunks(project_id, query, embedding_model,
                             embedding_fn, top_k=5, db_path=None):
    """Embed a query and return its top project-scoped semantic matches."""
    if not isinstance(query, str) or not query.strip():
        return []
    if not callable(embedding_fn):
        raise TypeError("embedding_fn must be callable.")
    if not list_research_documents(project_id, db_path):
        return []
    query_text = query.strip()[:4000]
    if "nomic-embed-text" in embedding_model.lower():
        query_text = "search_query: " + query_text
    vectors = embedding_fn([query_text], embedding_model)
    if len(vectors) != 1:
        raise ValueError("Could not create a single query embedding.")
    return search_chunks(
        project_id, vectors[0], embedding_model, top_k=top_k, db_path=db_path
    )


def format_research_context(results, max_chars=5000):
    """Format retrieved excerpts with traceable source labels for model prompts."""
    if not results:
        return ""
    lines = [
        "RETRIEVED RESEARCH REFERENCES — supporting material, not story canon:",
        "Use only relevant details. Do not invent facts beyond these excerpts. "
        "If sources conflict with the writer's brief, prefer the writer's brief and "
        "flag the conflict for review. Do not reproduce passages verbatim or place "
        "citation markers inside screenplay dialogue/action.",
    ]
    for index, item in enumerate(results, start=1):
        page = (
            f", page {item['page_number']}"
            if item.get("page_number") is not None else ""
        )
        lines.append(
            f"[R{index}] Source: {item['file_name']}{page}; "
            f"chunk {item['chunk_index']}; similarity {item['score']:.3f}\n"
            f"{item['content']}"
        )
        if len("\n".join(lines)) >= max_chars:
            break
    formatted = "\n".join(lines)
    if len(formatted) > max_chars:
        formatted = formatted[:max_chars].rsplit("\n", 1)[0]
    return formatted

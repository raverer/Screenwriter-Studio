import tempfile
import unittest
from pathlib import Path

from story_bible import init_db, upsert_project
from research_rag import (
    chunk_text,
    delete_research_document,
    extract_document_units,
    format_research_context,
    index_document,
    list_research_documents,
    retrieve_relevant_chunks,
)


class ResearchRagTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_research.db"
        init_db(self.db_path)
        self.project_id = upsert_project("Research Film", db_path=self.db_path)
        self.other_project_id = upsert_project("Other Film", db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_chunking_creates_overlapping_windows(self):
        text = " ".join(f"word{i}" for i in range(12))
        chunks = chunk_text(text, chunk_words=5, overlap_words=2)
        self.assertEqual(len(chunks), 4)
        self.assertIn("word3 word4", chunks[0])
        self.assertTrue(chunks[1].startswith("word3 word4"))

    def test_chunking_validates_sizes(self):
        with self.assertRaises(ValueError):
            chunk_text("some words", chunk_words=5, overlap_words=5)

    def test_extracts_utf8_text(self):
        units = extract_document_units("notes.txt", "A monsoon story.".encode())
        self.assertEqual(units[0]["text"], "A monsoon story.")
        self.assertIsNone(units[0]["page_number"])

    def test_rejects_unsupported_file_types(self):
        with self.assertRaisesRegex(ValueError, "Supported research formats"):
            extract_document_units("notes.csv", b"some data")

    def test_indexes_and_retrieves_project_scoped_chunks(self):
        def fake_embed(texts, model):
            return [
                [1.0, 0.0] if "train" in text.lower() else [0.0, 1.0]
                for text in texts
            ]

        payload = b"The last local train leaves the city at midnight."
        indexed = index_document(
            self.project_id, "train.txt", payload, "fake-embed",
            fake_embed, self.db_path
        )
        self.assertEqual(indexed["chunk_count"], 1)
        self.assertEqual(len(list_research_documents(self.project_id, self.db_path)), 1)

        results = retrieve_relevant_chunks(
            self.project_id, "train", "fake-embed", fake_embed,
            db_path=self.db_path
        )
        self.assertEqual(results[0]["file_name"], "train.txt")
        self.assertGreater(results[0]["score"], 0.99)

        isolated = retrieve_relevant_chunks(
            self.other_project_id, "train", "fake-embed", fake_embed,
            db_path=self.db_path
        )
        self.assertEqual(isolated, [])

    def test_duplicate_file_replaces_existing_index(self):
        def fake_embed(texts, model):
            return [[0.5, 0.5] for _ in texts]

        first = index_document(
            self.project_id, "notes.txt", b"First draft.",
            "fake-embed", fake_embed, self.db_path
        )
        second = index_document(
            self.project_id, "renamed.txt", b"First draft.",
            "fake-embed", fake_embed, self.db_path
        )
        self.assertTrue(second["replaced_existing"])
        docs = list_research_documents(self.project_id, self.db_path)
        self.assertEqual(len(docs), 1)
        self.assertNotEqual(first["document_id"], second["document_id"])
        self.assertEqual(docs[0]["file_name"], "renamed.txt")

    def test_delete_removes_only_selected_project_document(self):
        def fake_embed(texts, model):
            return [[1.0, 0.0] for _ in texts]

        result = index_document(
            self.project_id, "notes.txt", b"Useful research.",
            "fake-embed", fake_embed, self.db_path
        )
        self.assertTrue(delete_research_document(
            result["document_id"], self.project_id, self.db_path
        ))
        self.assertEqual(list_research_documents(self.project_id, self.db_path), [])

    def test_research_context_includes_source_citation(self):
        context = format_research_context([{
            "file_name": "history.pdf", "page_number": 7,
            "chunk_index": 2, "score": 0.91, "content": "The city expanded."
        }])
        self.assertIn("history.pdf, page 7", context)
        self.assertIn("[R1]", context)
        self.assertIn("The city expanded.", context)

    def test_empty_query_does_not_call_embedding_model(self):
        def should_not_run(texts, model):
            raise AssertionError("Embedding function should not be called")
        self.assertEqual(
            retrieve_relevant_chunks(
                self.project_id, "  ", "fake", should_not_run, db_path=self.db_path
            ),
            []
        )


if __name__ == "__main__":
    unittest.main()

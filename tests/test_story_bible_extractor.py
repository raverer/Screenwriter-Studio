import json
import tempfile
import unittest
from pathlib import Path

from story_bible import init_db, list_entries, upsert_entry, upsert_project
from story_bible_extractor import (
    MAX_SCREENPLAY_CHARS,
    build_extraction_prompt,
    parse_extraction_response,
    save_extracted_entries,
)


class StoryBibleExtractorTests(unittest.TestCase):
    def _payload(self):
        return {
            "entries": [
                {
                    "category": "character",
                    "name": "Aarav",
                    "data": {
                        "age": "30",
                        "occupation_or_role": "Software engineer",
                        "continuity_notes": "Wears a silver wristwatch",
                    },
                },
                {
                    "category": "location",
                    "name": "Versova Beach",
                    "data": {"place_type": "Exterior", "key_details": "Rocky shoreline"},
                },
            ]
        }

    def test_parses_valid_candidate_entries(self):
        records = parse_extraction_response(json.dumps(self._payload()))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["name"], "Aarav")
        self.assertEqual(records[0]["data"]["age"], "30")

    def test_accepts_fenced_json_and_numeric_age(self):
        payload = {"entries": [{
            "category": "character", "name": "Aarav", "data": {"age": 30}
        }]}
        fence = chr(96) * 3
        records = parse_extraction_response(fence + "json\n" + json.dumps(payload) + "\n" + fence)
        self.assertEqual(records[0]["data"]["age"], "30")

    def test_rejects_invalid_json(self):
        with self.assertRaisesRegex(ValueError, "JSON"):
            parse_extraction_response("not JSON")

    def test_rejects_unknown_category(self):
        payload = {"entries": [{"category": "vehicle", "name": "Taxi", "data": {}}]}
        with self.assertRaisesRegex(ValueError, "unsupported category"):
            parse_extraction_response(json.dumps(payload))

    def test_rejects_unknown_category_field(self):
        payload = {"entries": [{
            "category": "character", "name": "Aarav", "data": {"height": "tall"}
        }]}
        with self.assertRaisesRegex(ValueError, "unsupported character field"):
            parse_extraction_response(json.dumps(payload))

    def test_rejects_duplicate_entries(self):
        payload = {"entries": [
            {"category": "character", "name": "Aarav", "data": {}},
            {"category": "character", "name": "aarav", "data": {}},
        ]}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_extraction_response(json.dumps(payload))

    def test_empty_entries_is_valid(self):
        self.assertEqual(parse_extraction_response('{"entries": []}'), [])

    def test_save_requires_explicit_approval_to_update_existing_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            init_db(db_path)
            project_id = upsert_project("Test", db_path=db_path)
            upsert_entry(project_id, "character", "Aarav", {"age": "30"}, db_path=db_path)
            candidates = [
                {"category": "character", "name": "Aarav", "data": {"age": "31"}}
            ]
            with self.assertRaisesRegex(ValueError, "Explicitly approve"):
                save_extracted_entries(project_id, candidates, db_path=db_path)
            self.assertEqual(
                list_entries(project_id, "character", db_path)[0]["data"]["age"],
                "30",
            )

    def test_save_creates_and_updates_only_after_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            init_db(db_path)
            project_id = upsert_project("Test", db_path=db_path)
            upsert_entry(project_id, "character", "Aarav", {"age": "30"}, db_path=db_path)
            candidates = [
                {"category": "character", "name": "Aarav", "data": {"age": "30"}},
                {"category": "location", "name": "Versova Beach", "data": {"place_type": "Exterior"}},
            ]
            result = save_extracted_entries(
                project_id, candidates, allow_overwrite=True, db_path=db_path
            )
            self.assertEqual(result, {"created": 1, "updated": 1})
            self.assertEqual(len(list_entries(project_id, db_path=db_path)), 2)

    def test_approved_update_preserves_existing_facts_not_in_extraction(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            init_db(db_path)
            project_id = upsert_project("Test", db_path=db_path)
            upsert_entry(
                project_id, "character", "Aarav",
                {"age": "30", "goal_motivation": "Find connection"},
                db_path=db_path,
            )
            candidates = [
                {"category": "character", "name": "Aarav", "data": {"age": "31"}}
            ]
            save_extracted_entries(
                project_id, candidates, allow_overwrite=True, db_path=db_path
            )
            saved = list_entries(project_id, "character", db_path)[0]["data"]
            self.assertEqual(saved["age"], "31")
            self.assertEqual(saved["goal_motivation"], "Find connection")

    def test_prompt_truncates_to_local_context_limit(self):
        script = "A" * (MAX_SCREENPLAY_CHARS + 500)
        prompt = build_extraction_prompt(script)
        self.assertIn("A" * MAX_SCREENPLAY_CHARS, prompt)
        self.assertNotIn("A" * (MAX_SCREENPLAY_CHARS + 1), prompt)

    def test_prompt_requires_a_screenplay_and_is_grounded(self):
        with self.assertRaisesRegex(ValueError, "screenplay"):
            build_extraction_prompt("")
        prompt = build_extraction_prompt("Aarav, 30, adjusts his silver watch.")
        self.assertIn("Only include details directly supported", prompt)
        self.assertIn("Aarav, 30", prompt)


if __name__ == "__main__":
    unittest.main()

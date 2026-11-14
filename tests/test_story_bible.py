import json
import tempfile
import unittest
from pathlib import Path

from story_bible import (
    delete_entry,
    format_story_bible_context,
    get_project_id,
    get_project_metadata,
    init_db,
    list_entries,
    upsert_entry,
    upsert_project,
)


class StoryBibleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_story_bible.db"
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_project_creation_and_metadata_update(self):
        project_id = upsert_project("The First Encounter", {"genre": "Romance"}, self.db_path)
        same_id = upsert_project("the first encounter", {"genre": "Sci-Fi"}, self.db_path)
        self.assertEqual(project_id, same_id)
        self.assertEqual(get_project_id("THE FIRST ENCOUNTER", self.db_path), project_id)
        self.assertEqual(get_project_metadata(project_id, self.db_path), {"genre": "Sci-Fi"})

    def test_entry_persists_and_is_listed_by_category(self):
        project_id = upsert_project("Test Film", db_path=self.db_path)
        entry_id = upsert_entry(
            project_id, "character", "Aarav",
            {"age": "30", "occupation": "Software engineer"}, db_path=self.db_path
        )
        records = list_entries(project_id, "character", self.db_path)
        self.assertEqual(records[0]["id"], entry_id)
        self.assertEqual(records[0]["data"]["age"], "30")
        self.assertEqual(list_entries(project_id, "location", self.db_path), [])

    def test_entry_update_and_delete(self):
        project_id = upsert_project("Test Film", db_path=self.db_path)
        entry_id = upsert_entry(project_id, "prop", "Watch", {"owner": "Aarav"}, db_path=self.db_path)
        upsert_entry(project_id, "prop", "Watch", {"owner": "Mira"}, entry_id=entry_id, db_path=self.db_path)
        self.assertEqual(list_entries(project_id, "prop", self.db_path)[0]["data"]["owner"], "Mira")
        self.assertTrue(delete_entry(entry_id, project_id, self.db_path))
        self.assertFalse(delete_entry(entry_id, project_id, self.db_path))

    def test_same_entry_name_can_exist_in_different_categories(self):
        project_id = upsert_project("Test Film", db_path=self.db_path)
        upsert_entry(project_id, "character", "Cafe", {"role": "barista"}, db_path=self.db_path)
        upsert_entry(project_id, "location", "Cafe", {"type": "interior"}, db_path=self.db_path)
        self.assertEqual(len(list_entries(project_id, db_path=self.db_path)), 2)

    def test_story_bible_context_contains_saved_facts(self):
        project_id = upsert_project("Test Film", db_path=self.db_path)
        upsert_entry(project_id, "character", "Aarav", {"goal": "Find his sister"}, db_path=self.db_path)
        context = format_story_bible_context(project_id, self.db_path)
        self.assertIn("Aarav", context)
        self.assertIn("Find his sister", context)
        self.assertIn("do not contradict", context)

    def test_empty_project_and_invalid_category_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "title"):
            upsert_project(" ", db_path=self.db_path)
        project_id = upsert_project("Test Film", db_path=self.db_path)
        with self.assertRaisesRegex(ValueError, "Category"):
            upsert_entry(project_id, "vehicle", "Taxi", {}, db_path=self.db_path)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from story_bible_extractor import build_extraction_prompt, parse_extraction_response


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

    def test_prompt_requires_a_screenplay_and_is_grounded(self):
        with self.assertRaisesRegex(ValueError, "screenplay"):
            build_extraction_prompt("")
        prompt = build_extraction_prompt("Aarav, 30, adjusts his silver watch.")
        self.assertIn("Only include details directly supported", prompt)
        self.assertIn("Aarav, 30", prompt)


if __name__ == "__main__":
    unittest.main()

import unittest

from continuity_checker import check_continuity


class ContinuityCheckerTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {
                "category": "character",
                "name": "Aarav",
                "data": {"age": "30", "occupation_or_role": "Software engineer"},
            },
            {
                "category": "character",
                "name": "Mira",
                "data": {"age": "29"},
            },
            {
                "category": "location",
                "name": "Versova Beach",
                "data": {"description": "Rocky shoreline"},
            },
        ]

    def test_matching_ages_are_not_flagged(self):
        script = "Aarav, 30, sits across from Mira, 29."
        result = check_continuity(script, self.entries)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["checked_characters"], 2)

    def test_mismatched_age_is_flagged_with_line_number(self):
        script = "INT. RESTAURANT - NIGHT\nAarav, 28, adjusts his watch."
        result = check_continuity(script, self.entries)
        self.assertEqual(len(result["findings"]), 1)
        finding = result["findings"][0]
        self.assertEqual(finding["character"], "Aarav")
        self.assertEqual(finding["expected_age"], 30)
        self.assertEqual(finding["found_age"], 28)
        self.assertEqual(finding["line"], 2)

    def test_supports_common_age_phrasings(self):
        script = (
            "Aarav (32) enters.\n"
            "A 31-year-old Aarav waits outside.\n"
            "Aarav is 33 years old."
        )
        result = check_continuity(script, self.entries)
        self.assertEqual(
            [item["found_age"] for item in result["findings"]],
            [32, 31, 33],
        )

    def test_unrelated_numbers_are_not_treated_as_age(self):
        script = "Aarav checks his watch at 8:30 and walks for 30 minutes."
        result = check_continuity(script, self.entries)
        self.assertEqual(result["findings"], [])

    def test_empty_screenplay_returns_no_findings(self):
        result = check_continuity("", self.entries)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["checked_characters"], 0)

    def test_approximate_age_is_not_treated_as_exact(self):
        entries = [
            {"category": "character", "name": "Aarav", "data": {"age": "early 30s"}}
        ]
        result = check_continuity("Aarav, 28, enters.", entries)
        self.assertEqual(result["checked_characters"], 0)
        self.assertEqual(result["findings"], [])

    def test_non_numeric_story_bible_age_is_skipped(self):
        entries = [
            {"category": "character", "name": "Aarav", "data": {"age": "early thirties"}}
        ]
        result = check_continuity("Aarav, 30, enters.", entries)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["checked_characters"], 0)


if __name__ == "__main__":
    unittest.main()

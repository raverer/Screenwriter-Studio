import unittest

from story_structure import get_structure, get_structure_ids, list_structures
from structure_recommender import (
    get_complementary_structures,
    recommend_structures,
)


class StoryStructureLibraryTests(unittest.TestCase):
    def test_library_contains_exactly_seven_unique_structures(self):
        structures = list_structures()
        self.assertEqual(len(structures), 7)
        self.assertEqual(len({item["id"] for item in structures}), 7)
        self.assertEqual([item["id"] for item in structures], get_structure_ids())

    def test_each_structure_has_consistent_core_fields(self):
        required = {
            "id", "name", "core_principle", "primary_engine",
            "best_for_genres", "audience_experiences", "strengths",
            "cautions", "components", "complements",
        }
        for structure in list_structures():
            with self.subTest(structure=structure["id"]):
                self.assertTrue(required.issubset(structure))
                self.assertTrue(structure["name"])
                self.assertTrue(structure["core_principle"])
                self.assertTrue(structure["components"])
                self.assertTrue(structure["cautions"])

    def test_get_structure_returns_a_copy(self):
        first = get_structure("three-act")
        first["name"] = "Changed"
        second = get_structure("three_act")
        self.assertEqual(second["name"], "Three-Act Structure")

    def test_unknown_structure_raises_helpful_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown story structure"):
            get_structure("four-act-xyz")

    def test_complementary_structures_are_resolvable(self):
        complements = get_complementary_structures("fichtean_curve")
        self.assertEqual(
            [item["id"] for item in complements],
            ["three_act", "story_circle"],
        )


class StructureRecommenderTests(unittest.TestCase):
    def test_escalating_thriller_recommends_fichtean_curve(self):
        result = recommend_structures(
            genre="thriller",
            audience_experience="suspense",
            storytelling_engine="escalating danger",
        )
        first = result["recommendations"][0]
        self.assertEqual(first["structure_id"], "fichtean_curve")
        self.assertEqual(first["score"], 10)
        self.assertEqual(first["score_breakdown"], {
            "storytelling_engine": 5,
            "audience_experience": 3,
            "genre": 2,
        })
        self.assertTrue(first["match_reasons"])

    def test_psychological_thriller_alias_maps_to_relevant_genres(self):
        result = recommend_structures(genre="psychological thriller", limit=7)
        ids = [item["structure_id"] for item in result["recommendations"]]
        self.assertIn("fichtean_curve", ids)
        self.assertIn("freytags_pyramid", ids)
        self.assertIn("three_act", ids)

    def test_romantic_comedy_expands_to_romance_and_comedy(self):
        result = recommend_structures(genre="romantic comedy", limit=7)
        ids = [item["structure_id"] for item in result["recommendations"]]
        self.assertIn("story_circle", ids)
        self.assertIn("save_the_cat", ids)
        self.assertIn("three_act", ids)

    def test_heros_journey_alias_recommends_monomyth(self):
        result = recommend_structures(storytelling_engine="Hero's Journey")
        self.assertEqual(result["recommendations"][0]["structure_id"], "monomyth")

    def test_unknown_storytelling_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown storytelling_engine"):
            recommend_structures(storytelling_engine="mysterious plot engine")

    def test_commercial_audience_experience_supports_save_the_cat(self):
        result = recommend_structures(
            audience_experience="commercially engaging",
            storytelling_engine="commercial pacing",
        )
        self.assertEqual(result["recommendations"][0]["structure_id"], "save_the_cat")

    def test_discovery_and_observation_support_kishotenketsu(self):
        result = recommend_structures(
            genre="slice-of-life",
            audience_experience="contemplative",
            storytelling_engine="discovery and contrast",
        )
        self.assertEqual(result["recommendations"][0]["structure_id"], "kishotenketsu")

    def test_unknown_genre_uses_explicit_three_act_fallback(self):
        result = recommend_structures(genre="invented genre")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(len(result["recommendations"]), 1)
        recommendation = result["recommendations"][0]
        self.assertEqual(recommendation["structure_id"], "three_act")
        self.assertTrue(recommendation["fallback"])
        self.assertIn("No direct affinity", recommendation["match_reasons"][0])

    def test_multiple_values_are_supported(self):
        result = recommend_structures(
            genre=["horror", "crime"],
            audience_experience=["dread", "suspense"],
            limit=7,
        )
        scores = [item["score"] for item in result["recommendations"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertLessEqual(max(scores), result["method"]["maximum_score"])

    def test_limit_controls_number_of_results(self):
        result = recommend_structures(genre="fantasy", limit=2)
        self.assertLessEqual(len(result["recommendations"]), 2)

    def test_recommendation_contains_cautions_and_complementary_structure_ids(self):
        result = recommend_structures(genre="fantasy")
        recommendation = result["recommendations"][0]
        self.assertTrue(recommendation["cautions"])
        self.assertTrue(recommendation["complements"])
        self.assertIn("score_breakdown", recommendation)

    def test_no_criteria_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            recommend_structures()

    def test_invalid_limit_is_rejected(self):
        for invalid in (0, 8, -1):
            with self.subTest(limit=invalid):
                with self.assertRaises(ValueError):
                    recommend_structures(genre="horror", limit=invalid)

    def test_non_integer_limit_is_rejected(self):
        with self.assertRaises(TypeError):
            recommend_structures(genre="horror", limit=2.5)

    def test_invalid_input_types_are_rejected(self):
        with self.assertRaises(TypeError):
            recommend_structures(genre=42)
        with self.assertRaises(TypeError):
            recommend_structures(audience_experience=["suspense", 3])
        with self.assertRaises(TypeError):
            recommend_structures(storytelling_engine=["escalating danger"])

    def test_scores_are_not_presented_as_probabilities(self):
        result = recommend_structures(genre="horror")
        self.assertIn("not probabilities", result["method"]["note"])


if __name__ == "__main__":
    unittest.main()

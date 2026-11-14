import json
import unittest

from scene_evaluator import CRITERIA, evaluate_scene


def valid_payload(script):
    return {
        "criteria": {
            name: {"score": 4, "evidence": script, "feedback": "Specific feedback."}
            for name in CRITERIA
        },
        "strengths": ["Clear scene objective."],
        "improvements": ["Make the conflict more active."],
        "overall_assessment": "A promising scene with room to improve.",
    }


class SceneEvaluatorTests(unittest.TestCase):
    def test_valid_evaluation_and_average(self):
        script = "Aarav watches the strange light."
        payload = valid_payload(script)
        result = evaluate_scene("Scene objective: discover a mystery.", script,
                                lambda system, prompt: json.dumps(payload))
        self.assertEqual(result["average_score"], 4.0)
        self.assertEqual(len(result["criteria"]), 7)

    def test_requires_blueprint(self):
        with self.assertRaisesRegex(ValueError, "blueprint"):
            evaluate_scene("", "A scene.", lambda *_: "{}")

    def test_rejects_invalid_score(self):
        script = "Aarav watches the light."
        payload = valid_payload(script)
        payload["criteria"]["ending_hook"]["score"] = 8
        with self.assertRaisesRegex(ValueError, "score"):
            evaluate_scene("Blueprint", script, lambda *_: json.dumps(payload))

    def test_unverifiable_evidence_is_omitted(self):
        script = "Aarav watches the light."
        payload = valid_payload(script)
        payload["criteria"]["ending_hook"]["evidence"] = "Aarav sees a spaceship."
        result = evaluate_scene("Blueprint", script, lambda *_: json.dumps(payload))
        self.assertEqual(result["criteria"]["ending_hook"]["evidence"], "")
        self.assertIn("could not be verified", result["criteria"]["ending_hook"]["feedback"])

    def test_evidence_whitespace_differences_are_accepted(self):
        script = "Aarav watches the light.\nMira enters."
        payload = valid_payload(script)
        payload["criteria"]["ending_hook"]["evidence"] = "Aarav watches the light. Mira enters."
        result = evaluate_scene("Blueprint", script, lambda *_: json.dumps(payload))
        self.assertEqual(result["criteria"]["ending_hook"]["evidence"], payload["criteria"]["ending_hook"]["evidence"])

    def test_string_strengths_and_improvements_are_normalised(self):
        script = "Aarav watches the light."
        payload = valid_payload(script)
        payload["strengths"] = "The opening image is clear."
        payload["improvements"] = "Increase the obstacle before the turning point."
        result = evaluate_scene("Blueprint", script, lambda *_: json.dumps(payload))
        self.assertEqual(result["strengths"], ["The opening image is clear."])
        self.assertEqual(result["improvements"], ["Increase the obstacle before the turning point."])

    def test_rejects_invalid_json(self):
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            evaluate_scene("Blueprint", "A scene.", lambda *_: "not json")


if __name__ == "__main__":
    unittest.main()

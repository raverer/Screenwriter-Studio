import json
import unittest

from story_architecture import (
    ARC_FIELDS,
    BEAT_FIELDS,
    build_architecture_prompt,
    build_architecture_system_prompt,
    format_architecture_context,
    generate_architecture,
    parse_architecture_response,
    validate_architecture,
)
from story_structure import get_structure, get_structure_ids


def valid_architecture(structure_id="kishotenketsu"):
    structure = get_structure(structure_id)
    return {
        "structure_id": structure_id,
        "title": "The Last Monsoon",
        "dramatic_question": "Will Nila return the lost letters before the village is evacuated?",
        "theme": "Memory connects people across generations.",
        "protagonist_arc": {
            "starting_state": "Nila avoids her family's history.",
            "external_goal": "Find and return a box of letters.",
            "internal_need": "Accept the value of inherited memory.",
            "ending_state": "Nila chooses to preserve the stories.",
        },
        "central_conflict": "Nila's deadline conflicts with the village's imminent evacuation.",
        "stakes": "The letters and the memories they contain may be permanently lost.",
        "ending_type": "Hopeful resolution",
        "beats": [
            {
                "component": component,
                "story_event": f"Specific story event for {component}.",
                "dramatic_function": f"Dramatic function of {component}.",
                "cause_and_effect": f"Causal connection for {component}.",
                "protagonist_shift": f"Protagonist shift during {component}.",
                "open_questions": ["Will the family reveal the truth?"],
            }
            for component in structure["components"]
        ],
    }


class StoryArchitecturePromptTests(unittest.TestCase):
    def test_prompt_includes_selected_structure_and_exact_components(self):
        prompt = build_architecture_prompt(
            "save_the_cat",
            {
                "title": "The Last Monsoon",
                "genre": "Family drama",
                "logline": "A daughter returns home to find a missing archive.",
            },
        )
        self.assertIn("Save the Cat", prompt)
        self.assertIn("Opening Image", prompt)
        self.assertIn("Final Image", prompt)
        self.assertIn('"beats" must contain exactly 15 items.', prompt)
        self.assertIn("The Last Monsoon", prompt)
        self.assertIn("Family drama", prompt)

    def test_prompt_contains_ki_sho_ten_ketsu_components(self):
        prompt = build_architecture_prompt("kishotenketsu", {"genre": "Slice of life"})
        self.assertIn("Ki — Introduction", prompt)
        self.assertIn("Shō — Development", prompt)
        self.assertIn("Ten — Twist or contrast", prompt)
        self.assertIn("Ketsu — Conclusion or connection", prompt)
        self.assertIn('"beats" must contain exactly 4 items.', prompt)

    def test_prompt_includes_structure_specific_cautions(self):
        prompt = build_architecture_prompt("kishotenketsu")
        self.assertIn("do not force a conventional antagonist conflict", prompt)

    def test_system_prompt_requires_json_and_project_specific_events(self):
        prompt = build_architecture_system_prompt()
        self.assertIn("valid JSON", prompt)
        self.assertIn("specific, filmable story architecture", prompt)

    def test_invalid_project_detail_container_is_rejected(self):
        with self.assertRaises(TypeError):
            build_architecture_prompt("three_act", "not a dictionary")

    def test_invalid_project_detail_value_is_rejected(self):
        with self.assertRaises(TypeError):
            build_architecture_prompt("three_act", {"genre": object()})

    def test_unknown_structure_is_rejected(self):
        with self.assertRaises(ValueError):
            build_architecture_prompt("unknown_structure")


class StoryArchitectureValidationTests(unittest.TestCase):
    def test_valid_architecture_is_normalized(self):
        architecture = valid_architecture()
        result = validate_architecture(architecture, "kishotenketsu")
        self.assertEqual(result["structure_id"], "kishotenketsu")
        self.assertEqual(len(result["beats"]), 4)
        self.assertEqual(result["beats"][0]["component"], "Ki — Introduction")

    def test_all_seven_structures_accept_their_component_counts(self):
        for structure_id in get_structure_ids():
            with self.subTest(structure=structure_id):
                result = validate_architecture(
                    valid_architecture(structure_id), structure_id
                )
                self.assertEqual(
                    len(result["beats"]),
                    len(get_structure(structure_id)["components"]),
                )

    def test_missing_top_level_field_is_rejected(self):
        architecture = valid_architecture()
        del architecture["theme"]
        with self.assertRaisesRegex(ValueError, "theme"):
            validate_architecture(architecture, "kishotenketsu")

    def test_wrong_structure_id_is_rejected(self):
        architecture = valid_architecture()
        architecture["structure_id"] = "three_act"
        with self.assertRaisesRegex(ValueError, "structure_id"):
            validate_architecture(architecture, "kishotenketsu")

    def test_missing_protagonist_arc_field_is_rejected(self):
        architecture = valid_architecture()
        del architecture["protagonist_arc"]["internal_need"]
        with self.assertRaisesRegex(ValueError, "internal_need"):
            validate_architecture(architecture, "kishotenketsu")

    def test_empty_required_story_field_is_rejected(self):
        architecture = valid_architecture()
        architecture["central_conflict"] = "  "
        with self.assertRaisesRegex(ValueError, "central_conflict"):
            validate_architecture(architecture, "kishotenketsu")

    def test_missing_beat_is_rejected(self):
        architecture = valid_architecture()
        architecture["beats"].pop()
        with self.assertRaisesRegex(ValueError, "exactly 4 beats"):
            validate_architecture(architecture, "kishotenketsu")

    def test_reordered_beats_are_rejected(self):
        architecture = valid_architecture()
        architecture["beats"][0], architecture["beats"][1] = (
            architecture["beats"][1], architecture["beats"][0]
        )
        with self.assertRaisesRegex(ValueError, "selected order"):
            validate_architecture(architecture, "kishotenketsu")

    def test_duplicate_beats_are_rejected(self):
        architecture = valid_architecture()
        architecture["beats"][1]["component"] = architecture["beats"][0]["component"]
        with self.assertRaisesRegex(ValueError, "selected order"):
            validate_architecture(architecture, "kishotenketsu")

    def test_missing_beat_detail_is_rejected(self):
        architecture = valid_architecture()
        del architecture["beats"][0]["cause_and_effect"]
        with self.assertRaisesRegex(ValueError, "cause_and_effect"):
            validate_architecture(architecture, "kishotenketsu")

    def test_too_many_open_questions_are_rejected(self):
        architecture = valid_architecture()
        architecture["beats"][0]["open_questions"] = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        with self.assertRaisesRegex(ValueError, "at most 4"):
            validate_architecture(architecture, "kishotenketsu")

    def test_non_string_question_is_rejected(self):
        architecture = valid_architecture()
        architecture["beats"][0]["open_questions"] = [42]
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            validate_architecture(architecture, "kishotenketsu")

    def test_non_mapping_architecture_is_rejected(self):
        with self.assertRaises(TypeError):
            validate_architecture("not an object", "kishotenketsu")


class StoryArchitectureParsingAndGenerationTests(unittest.TestCase):
    def test_parses_valid_json_response(self):
        raw = json.dumps(valid_architecture())
        result = parse_architecture_response(raw, "kishotenketsu")
        self.assertEqual(result["title"], "The Last Monsoon")

    def test_parses_json_fenced_response(self):
        fence = chr(96) * 3
        raw = fence + "json\n" + json.dumps(valid_architecture()) + "\n" + fence
        result = parse_architecture_response(raw, "kishotenketsu")
        self.assertEqual(len(result["beats"]), 4)

    def test_invalid_json_response_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid story architecture JSON"):
            parse_architecture_response("{not valid json}", "kishotenketsu")

    def test_empty_response_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty story architecture"):
            parse_architecture_response("", "kishotenketsu")

    def test_generation_calls_injected_model_and_validates(self):
        calls = []

        def fake_llm(system_prompt, user_prompt):
            calls.append((system_prompt, user_prompt))
            return json.dumps(valid_architecture("three_act"))

        result = generate_architecture(
            "three_act", {"title": "Test Film"}, fake_llm
        )
        self.assertEqual(result["structure_id"], "three_act")
        self.assertEqual(len(calls), 1)
        self.assertIn("Test Film", calls[0][1])

    def test_generation_rejects_invalid_model_output(self):
        with self.assertRaises(ValueError):
            generate_architecture(
                "three_act", {}, lambda system, prompt: '{"beats": []}'
            )


    def test_generation_with_monomyth_structure_uses_twelve_components(self):
        captured = {}

        def fake_llm(system_prompt, user_prompt):
            captured["prompt"] = user_prompt
            return json.dumps(valid_architecture("monomyth"))

        result = generate_architecture("monomyth", {"genre": "Fantasy"}, fake_llm)
        self.assertEqual(len(result["beats"]), 12)
        self.assertIn("Return ONLY one valid JSON object", captured["prompt"])

    def test_architecture_context_includes_each_beat_in_order(self):
        architecture = valid_architecture("kishotenketsu")
        context = format_architecture_context(architecture)
        self.assertLess(context.index("1. Ki — Introduction"), context.index("2. Shō — Development"))
        self.assertLess(context.index("2. Shō — Development"), context.index("3. Ten — Twist or contrast"))
        self.assertLess(context.index("3. Ten — Twist or contrast"), context.index("4. Ketsu — Conclusion or connection"))

    def test_generation_requires_callable(self):
        with self.assertRaises(TypeError):
            generate_architecture("three_act", {}, "not callable")


class StoryArchitectureContextTests(unittest.TestCase):
    def test_format_context_contains_approved_structure_and_beats(self):
        architecture = valid_architecture("kishotenketsu")
        context = format_architecture_context(architecture)
        self.assertIn("APPROVED STORY ARCHITECTURE", context)
        self.assertIn("Kishōtenketsu", context)
        self.assertIn("Ki — Introduction", context)
        self.assertIn("The Last Monsoon", context)

    def test_context_refuses_invalid_architecture(self):
        architecture = valid_architecture()
        architecture["beats"] = []
        with self.assertRaises(ValueError):
            format_architecture_context(architecture)


if __name__ == "__main__":
    unittest.main()

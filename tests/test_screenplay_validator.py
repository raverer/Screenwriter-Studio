import unittest

from screenplay_validator import validate_screenplay


class ScreenplayValidatorTests(unittest.TestCase):
    def test_empty_script_is_error(self):
        self.assertEqual(validate_screenplay("")[0][0], "error")

    def test_valid_exterior_heading_detected(self):
        report = validate_screenplay("EXT. VERSOVA BEACH - NIGHT\nA wave rolls in.")
        self.assertTrue(any("1 scene heading" in message for _, message in report))

    def test_indoor_beach_heading_warned(self):
        report = validate_screenplay("INT. VERSOVA BEACH - NIGHT\nWaves roll in.")
        self.assertTrue(any(level == "warning" and "EXT." in message for level, message in report))

    def test_markdown_wrapped_heading_detected(self):
        report = validate_screenplay("**EXT. VERSOVA BEACH - NIGHT**\nWaves roll in.")
        self.assertTrue(any("1 scene heading" in message for _, message in report))

    def test_numbered_beats_warned(self):
        report = validate_screenplay("EXT. BEACH - NIGHT\n**1**\nA wave rolls in.")
        self.assertTrue(any("numbered beat markers" in message for _, message in report))

    def test_repeated_transition_warned(self):
        report = validate_screenplay("EXT. BEACH - NIGHT\nCUT TO:\nA wave.\nCUT TO:")
        self.assertTrue(any("repeated transition" in message for _, message in report))


if __name__ == "__main__":
    unittest.main()

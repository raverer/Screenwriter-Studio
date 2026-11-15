import unittest

from screenplay_formats import (
    DEFAULT_DURATIONS,
    FORMAT_OPTIONS,
    build_compact_blueprint_sections,
    build_compact_blueprint_task,
    build_compact_generation_instruction,
    build_format_guidance,
    get_duration_range,
    is_compact_script_format,
    validate_target_duration,
)


class ScreenplayFormatTests(unittest.TestCase):
    def test_new_formats_are_available(self):
        self.assertIn("Advertisement", FORMAT_OPTIONS)
        self.assertIn("TVC", FORMAT_OPTIONS)
        self.assertIn("Micro Drama", FORMAT_OPTIONS)

    def test_advertisement_duration_range_is_inclusive(self):
        self.assertEqual(get_duration_range("Advertisement"), (15, 120))
        self.assertEqual(validate_target_duration("Advertisement", 15), 15)
        self.assertEqual(validate_target_duration("Advertisement", 120), 120)

    def test_tvc_duration_range_is_inclusive(self):
        self.assertEqual(get_duration_range("TVC"), (15, 120))
        self.assertEqual(validate_target_duration("TVC", 15), 15)
        self.assertEqual(validate_target_duration("TVC", 120), 120)

    def test_micro_drama_duration_range_is_inclusive(self):
        self.assertEqual(get_duration_range("Micro Drama"), (150, 200))
        self.assertEqual(validate_target_duration("Micro Drama", 150), 150)
        self.assertEqual(validate_target_duration("Micro Drama", 200), 200)

    def test_defaults_fall_inside_each_range(self):
        for project_type, duration in DEFAULT_DURATIONS.items():
            with self.subTest(project_type=project_type):
                self.assertEqual(validate_target_duration(project_type, duration), duration)

    def test_advertisement_and_tvc_reject_out_of_range_durations(self):
        for project_type in ("Advertisement", "TVC"):
            for duration in (14, 121):
                with self.subTest(project_type=project_type, duration=duration):
                    with self.assertRaises(ValueError):
                        validate_target_duration(project_type, duration)

    def test_micro_drama_rejects_out_of_range_durations(self):
        for duration in (149, 201):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    validate_target_duration("Micro Drama", duration)

    def test_boolean_and_non_integer_durations_are_rejected(self):
        for duration in (True, 30.5, "30", None):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    validate_target_duration("Advertisement", duration)

    def test_long_form_formats_do_not_require_target_duration(self):
        for project_type in ("Feature Film", "OTT / Web Series", "Short Film"):
            with self.subTest(project_type=project_type):
                self.assertIsNone(validate_target_duration(project_type, None))
                self.assertFalse(is_compact_script_format(project_type))

    def test_ad_guidance_requires_a_complete_timed_commercial(self):
        guidance = build_format_guidance("Advertisement", 45)
        self.assertIn("TARGET RUNTIME: 45 seconds", guidance)
        self.assertIn("complete, shootable commercial", guidance)
        self.assertIn("call to action", guidance)
        self.assertIn("Do not invent product features", guidance)

    def test_tvc_guidance_uses_tvc_conventions(self):
        guidance = build_format_guidance("TVC", 30)
        self.assertIn("television commercial (TVC)", guidance)
        self.assertIn("voice-over", guidance)
        self.assertIn("end card", guidance)

    def test_micro_drama_guidance_is_not_advertising_copy(self):
        guidance = build_format_guidance("Micro Drama", 180)
        self.assertIn("TARGET RUNTIME: 180 seconds", guidance)
        self.assertIn("immediate dramatic hook", guidance)
        self.assertIn("final reversal/cliffhanger", guidance)
        self.assertIn("Avoid advertising-style product pitches", guidance)

    def test_compact_blueprint_tasks_plan_the_full_script(self):
        ad_task = build_compact_blueprint_task("TVC", 60)
        drama_task = build_compact_blueprint_task("Micro Drama", 175)
        self.assertIn("COMPLETE TVC script", ad_task)
        self.assertIn("60 seconds", ad_task)
        self.assertIn("COMPLETE Micro Drama", drama_task)
        self.assertIn("175 seconds", drama_task)

    def test_blueprint_sections_differ_by_compact_format(self):
        ad_sections = build_compact_blueprint_sections("Advertisement")
        drama_sections = build_compact_blueprint_sections("Micro Drama")
        self.assertIn("SINGLE-MINDED MESSAGE", ad_sections)
        self.assertIn("CALL TO ACTION", ad_sections)
        self.assertIn("PROTAGONIST AND OBJECTIVE", drama_sections)
        self.assertIn("PAYOFF / FINAL REVERSAL / CLIFFHANGER", drama_sections)

    def test_generation_instructions_include_full_script_and_runtime(self):
        ad_instruction = build_compact_generation_instruction("Advertisement", 30)
        drama_instruction = build_compact_generation_instruction("Micro Drama", 160)
        self.assertIn("TARGET RUNTIME: 30 seconds", ad_instruction)
        self.assertIn("Write the COMPLETE commercial", ad_instruction)
        self.assertIn("TARGET RUNTIME: 160 seconds", drama_instruction)
        self.assertIn("Write the COMPLETE micro-drama", drama_instruction)

    def test_unknown_format_is_rejected(self):
        with self.assertRaises(ValueError):
            build_format_guidance("Podcast", 30)


if __name__ == "__main__":
    unittest.main()

import inspect
import unittest

from workers.ab_av1_result import (
    AbAv1ResultParser,
    CrfCandidate,
    SearchResult,
    SearchResultMode,
)
from workers.encoder import EncoderWorker


class AbAv1ResultParserTests(unittest.TestCase):
    def test_success_uses_final_crf_and_summary_candidate(self):
        parser = AbAv1ResultParser()
        parser.feed("sample 1/13 crf 23 VMAF 95.28 (84%)")
        parser.feed("sample 2/13 crf 23 VMAF 94.67 (84%)")

        candidate = parser.feed(
            "crf 23 VMAF 93.69 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )
        parser.feed("crf 23 successful")

        result = parser.finish(return_code=0, target_vmaf=93.0)

        self.assertEqual(
            candidate,
            CrfCandidate(crf=23, vmaf=93.69, encoded_percent=84.0),
        )
        self.assertEqual(
            result,
            SearchResult(
                mode=SearchResultMode.SUCCESS,
                crf=23,
                vmaf=93.69,
                encoded_percent=84.0,
            ),
        )
        self.assertEqual(parser.candidates, (candidate,))

    def test_sample_lines_do_not_create_candidates(self):
        parser = AbAv1ResultParser()

        first = parser.feed("sample 1/13 crf 23 VMAF 95.28 (84%)")
        second = parser.feed("sample 2/13 crf 23 VMAF 94.67 (84%)")

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(parser.candidates, ())

    def test_duplicate_summary_is_reported_only_once(self):
        parser = AbAv1ResultParser()
        summary = (
            "crf 23 VMAF 93.69 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )

        first = parser.feed(summary)
        second = parser.feed(f"[INFO] {summary}")

        self.assertEqual(
            first,
            CrfCandidate(crf=23, vmaf=93.69, encoded_percent=84.0),
        )
        self.assertIsNone(second)
        self.assertEqual(parser.candidates, (first,))

    def test_quality_fallback_selects_largest_crf_meeting_target(self):
        parser = AbAv1ResultParser()
        parser.feed(
            "crf 23 VMAF 93.69 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )
        parser.feed(
            "crf 24 VMAF 92.76 predicted video stream size "
            "4.70 GiB (79%) taking 9 minutes"
        )
        parser.feed("Error: Failed to find a suitable crf")

        result = parser.finish(return_code=1, target_vmaf=93.0)

        self.assertEqual(
            result,
            SearchResult(
                mode=SearchResultMode.QUALITY_FALLBACK,
                crf=23,
                vmaf=93.69,
                encoded_percent=84.0,
            ),
        )

    def test_quality_fallback_chooses_highest_qualifying_crf(self):
        parser = AbAv1ResultParser()
        parser.feed(
            "crf 22 VMAF 94.50 predicted video stream size "
            "5.30 GiB (91%) taking 10 minutes"
        )
        parser.feed(
            "crf 23 VMAF 93.20 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )
        parser.feed("Error: Failed to find a suitable crf")

        result = parser.finish(return_code=1, target_vmaf=93.0)

        self.assertEqual(result.crf, 23)

    def test_no_candidate_meeting_target_returns_none(self):
        parser = AbAv1ResultParser()
        parser.feed(
            "crf 24 VMAF 92.76 predicted video stream size "
            "4.70 GiB (79%) taking 9 minutes"
        )
        parser.feed("Error: Failed to find a suitable crf")

        self.assertIsNone(parser.finish(return_code=1, target_vmaf=93.0))

    def test_unknown_error_never_uses_temporary_candidate(self):
        parser = AbAv1ResultParser()
        parser.feed(
            "crf 23 VMAF 93.69 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )
        parser.feed("Device creation failed")

        self.assertIsNone(parser.finish(return_code=1, target_vmaf=93.0))

    def test_other_terminal_error_blocks_quality_fallback(self):
        parser = AbAv1ResultParser()
        parser.feed(
            "crf 23 VMAF 93.69 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )
        parser.feed("Error: encoder device creation failed")
        parser.feed("Error: Failed to find a suitable crf")

        self.assertIsNone(parser.finish(return_code=1, target_vmaf=93.0))

    def test_zero_exit_without_success_marker_returns_none(self):
        parser = AbAv1ResultParser()
        parser.feed(
            "crf 23 VMAF 93.69 predicted video stream size "
            "5.00 GiB (84%) taking 10 minutes"
        )

        self.assertIsNone(parser.finish(return_code=0, target_vmaf=93.0))


class EncoderIntegrationTests(unittest.TestCase):
    def test_encoder_uses_structured_ab_av1_parser(self):
        source = inspect.getsource(EncoderWorker.run)

        self.assertIn("parser = AbAv1ResultParser()", source)
        self.assertIn("candidate = parser.feed(decoded)", source)
        self.assertIn(
            "parser.finish(proc.returncode, float(target_vmaf))",
            source,
        )
        self.assertNotIn("attempt_success", source)
        self.assertNotIn("将强行采用", source)

    def test_encoder_never_uses_default_crf_after_all_searches_fail(self):
        source = inspect.getsource(EncoderWorker.run)

        self.assertIn("best_icq = None", source)
        self.assertNotIn("best_icq = 24", source)
        self.assertIn("if not search_success:", source)
        self.assertIn("self.file_status_signal.emit(filepath, \"error\")", source)


if __name__ == "__main__":
    unittest.main()

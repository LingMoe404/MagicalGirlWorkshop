import inspect
import unittest

from workers.encoder import EncoderWorker
from workers.ffmpeg_retry import (
    FailureKind,
    RetryDecision,
    RetryState,
    build_hw_decode_args,
    is_hardware_resource_error,
    next_retry_state,
)


class HardwareDecodeArgsTests(unittest.TestCase):
    def test_nvenc_uses_explicit_cuda_decode(self):
        self.assertEqual(
            build_hw_decode_args("av1_nvenc", enabled=True),
            ["-hwaccel", "cuda", "-v", "verbose"],
        )

    def test_disabled_hardware_decode_uses_software_decode(self):
        args = build_hw_decode_args("av1_nvenc", enabled=False)

        self.assertEqual(args, ["-v", "verbose"])
        self.assertNotIn("-hwaccel", args)

    def test_qsv_and_amf_keep_their_existing_decode_modes(self):
        self.assertEqual(
            build_hw_decode_args("av1_qsv", enabled=True),
            [
                "-init_hw_device",
                "qsv=hw",
                "-filter_hw_device",
                "hw",
                "-hwaccel",
                "qsv",
                "-v",
                "verbose",
            ],
        )
        self.assertEqual(
            build_hw_decode_args("av1_amf", enabled=True),
            ["-hwaccel", "auto", "-v", "verbose"],
        )


class RetryStateTests(unittest.TestCase):
    def test_hardware_error_falls_back_to_software_decode(self):
        state = RetryState(use_hw_decode=True, include_subtitles=True)

        result = next_retry_state(
            state,
            [
                "[DXVA2] Failed to create Direct3D device",
                "Device creation failed: -1313558101.",
            ],
        )

        self.assertEqual(
            result,
            RetryDecision(
                state=RetryState(
                    use_hw_decode=False,
                    include_subtitles=True,
                ),
                reason=FailureKind.HARDWARE_DEVICE,
            ),
        )

    def test_cuda_initialization_error_falls_back_to_software_decode(self):
        state = RetryState(use_hw_decode=True, include_subtitles=True)

        result = next_retry_state(
            state,
            ["Device setup failed for decoder on input stream #0:0"],
        )

        self.assertEqual(result.reason, FailureKind.HARDWARE_DEVICE)
        self.assertFalse(result.state.use_hw_decode)

    def test_subtitle_error_drops_only_subtitles(self):
        state = RetryState(use_hw_decode=True, include_subtitles=True)

        result = next_retry_state(
            state,
            ["Error while decoding subtitle stream #0:2"],
        )

        self.assertEqual(
            result,
            RetryDecision(
                state=RetryState(
                    use_hw_decode=True,
                    include_subtitles=False,
                ),
                reason=FailureKind.SUBTITLE,
            ),
        )

    def test_subtitle_encoder_mismatch_drops_subtitles(self):
        state = RetryState(use_hw_decode=False, include_subtitles=True)

        result = next_retry_state(
            state,
            [
                "Subtitle encoding currently only possible from text "
                "to text or bitmap to bitmap"
            ],
        )

        self.assertEqual(result.reason, FailureKind.SUBTITLE)
        self.assertFalse(result.state.include_subtitles)
        self.assertFalse(result.state.use_hw_decode)

    def test_subtitle_stream_number_is_linked_to_decode_error(self):
        state = RetryState(use_hw_decode=True, include_subtitles=True)

        result = next_retry_state(
            state,
            [
                "Stream #0:2(eng): Subtitle: mov_text",
                "Error while decoding stream #0:2: Invalid data found",
            ],
        )

        self.assertEqual(result.reason, FailureKind.SUBTITLE)
        self.assertFalse(result.state.include_subtitles)

    def test_subtitle_output_stream_error_drops_subtitles(self):
        state = RetryState(use_hw_decode=True, include_subtitles=True)

        result = next_retry_state(
            state,
            ["[sost#0:2/subrip] Error initializing output stream"],
        )

        self.assertEqual(result.reason, FailureKind.SUBTITLE)

    def test_unknown_error_does_not_retry(self):
        result = next_retry_state(
            RetryState(use_hw_decode=True, include_subtitles=True),
            ["Permission denied while opening output file"],
        )

        self.assertIsNone(result)

    def test_hardware_then_subtitle_uses_three_unique_states(self):
        first = RetryState(use_hw_decode=True, include_subtitles=True)
        second = next_retry_state(
            first,
            ["Device creation failed"],
        ).state
        third = next_retry_state(
            second,
            ["Error while decoding subtitle stream #0:2"],
        ).state

        self.assertEqual(
            [first, second, third],
            [
                RetryState(True, True),
                RetryState(False, True),
                RetryState(False, False),
            ],
        )
        self.assertEqual(len({first, second, third}), 3)

    def test_subtitle_then_hardware_uses_three_unique_states(self):
        first = RetryState(use_hw_decode=True, include_subtitles=True)
        second = next_retry_state(
            first,
            ["Error while decoding subtitle stream #0:2"],
        ).state
        third = next_retry_state(
            second,
            ["Failed to create CUDA context"],
        ).state

        self.assertEqual(
            [first, second, third],
            [
                RetryState(True, True),
                RetryState(True, False),
                RetryState(False, False),
            ],
        )
        self.assertEqual(len({first, second, third}), 3)

    def test_no_fallback_repeats_an_already_disabled_state(self):
        state = RetryState(use_hw_decode=False, include_subtitles=False)

        self.assertIsNone(
            next_retry_state(state, ["Device creation failed"])
        )
        self.assertIsNone(
            next_retry_state(
                state,
                ["Error while decoding subtitle stream #0:2"],
            )
        )


class HardwareResourceErrorTests(unittest.TestCase):
    def test_concurrent_session_exhaustion_is_resource_error(self):
        self.assertTrue(
            is_hardware_resource_error(
                ["OpenEncodeSessionEx failed: out of memory (10)"]
            )
        )

    def test_qsv_device_busy_is_resource_error(self):
        self.assertTrue(
            is_hardware_resource_error(["MFX_ERR_DEVICE_BUSY"])
        )

    def test_decode_device_reinitialization_is_not_resource_error(self):
        self.assertFalse(
            is_hardware_resource_error(
                ["Device setup failed for decoder on input stream #0:0"]
            )
        )


class EncoderIntegrationTests(unittest.TestCase):
    def test_encoder_run_uses_retry_policy_for_three_attempts(self):
        source = inspect.getsource(EncoderWorker.run)

        self.assertIn(
            "build_hw_decode_args(enc_name, retry_state.use_hw_decode)",
            source,
        )
        self.assertIn("for attempt in range(3):", source)
        self.assertIn(
            "next_retry_state(retry_state, err_log)",
            source,
        )


if __name__ == "__main__":
    unittest.main()
